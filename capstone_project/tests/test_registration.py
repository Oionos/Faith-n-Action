import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PILImage

from capstone_project.models import Council, User


def _png_bytes():
    """A genuinely decodable 2x2 PNG. Required since e-signature uploads are now
    validated by decoding (SEC-14 fix) rather than trusting the content-type."""
    buf = io.BytesIO()
    PILImage.new('RGB', (2, 2), 'white').save(buf, format='PNG')
    return buf.getvalue()


class SignUpViewTests(TestCase):
    """The public registration flow (views.py sign_up POST) — all validation
    branches plus upload handling. Regression guards for the sign-up path."""

    @classmethod
    def setUpTestData(cls):
        cls.council = Council.objects.create(id=1, name='Test Council', district='Test District')

    def _payload(self, **overrides):
        data = {
            'username': 'newmember', 'email': 'new@example.com',
            'password': 'C0mplex-Passphrase!', 're_password': 'C0mplex-Passphrase!',
            'first_name': 'New', 'middle_name': 'T', 'last_name': 'Member',
            'birthday': '1990-01-01', 'street': '1 Rizal St', 'barangay': 'Brgy',
            'city': 'Lucena', 'province': 'Quezon', 'zip_code': '4301',
            'contact_number': '09171234567', 'council': self.council.id,
            'practical_catholic': 'Yes', 'privacy_agreement': 'agree',
            'voluntary_join': 'on',
            'e_signature': SimpleUploadedFile('sig.png', _png_bytes(), content_type='image/png'),
        }
        data.update(overrides)
        return data

    def _post(self, **overrides):
        payload = self._payload()
        sig = payload.pop('e_signature')
        payload.update({k: v for k, v in overrides.items() if k != 'e_signature'})
        if 'e_signature' in overrides:
            sig = overrides['e_signature']
        if sig is not None:
            # Django's test client multipart-encodes files that appear in data
            payload['e_signature'] = sig
        return self.client.post('/sign-up/', payload)

    def test_successful_registration_creates_pending_user(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(username='newmember')
        self.assertEqual(user.role, 'pending')
        self.assertEqual(user.council, self.council)
        self.assertFalse(user.is_staff)

    def test_password_mismatch_creates_no_user(self):
        self._post(re_password='different-value')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='taken', password='pass12345!', role='member')
        self._post(username='taken', email='other@example.com')
        self.assertEqual(User.objects.filter(username='taken').count(), 1)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username='existing', email='dup@example.com',
                                 password='pass12345!', role='member', council=self.council)
        self._post(email='dup@example.com', username='brandnew')
        self.assertFalse(User.objects.filter(username='brandnew').exists())

    def test_underage_applicant_rejected(self):
        self._post(birthday='2010-01-01')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_non_practical_catholic_rejected(self):
        self._post(practical_catholic='No')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_privacy_agreement_required(self):
        self._post(privacy_agreement='')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_e_signature_required(self):
        self._post(e_signature=None)
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_e_signature_bad_content_type_rejected(self):
        self._post(e_signature=SimpleUploadedFile('sig.txt', b'plain', content_type='text/plain'))
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_e_signature_content_type_spoof_rejected(self):  # SEC-14 guard
        self._post(e_signature=SimpleUploadedFile('sig.png', b'this is not an image', content_type='image/png'))
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_weak_password_rejected(self):  # AUTH_PASSWORD_VALIDATORS guard
        self._post(password='123', re_password='123')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_password_similar_to_username_rejected(self):
        self._post(username='juandelacruz', email='jdc@example.com',
                   password='juandelacruz', re_password='juandelacruz')
        self.assertFalse(User.objects.filter(username='juandelacruz').exists())

    def test_authenticated_user_redirected_to_dashboard(self):
        User.objects.create_user(username='logged', password='pass12345!', role='member', council=self.council)
        self.client.force_login(User.objects.get(username='logged'))
        resp = self.client.get('/sign-up/')
        self.assertEqual(resp.status_code, 302)


class EditProfilePasswordTests(TestCase):
    """edit_profile must apply the same AUTH_PASSWORD_VALIDATORS as sign-up."""

    def setUp(self):
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.user = User.objects.create_user(username='pwuser', password='Str0ng-Pass-123!',
                                             role='member', council=self.council)
        self.client.force_login(self.user)

    def test_weak_password_change_rejected(self):
        self.client.post('/edit-profile/', {'password': '123'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Str0ng-Pass-123!'))

    def test_strong_password_change_accepted(self):
        self.client.post('/edit-profile/', {'password': 'An0ther-Str0ng-Pass!'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('An0ther-Str0ng-Pass!'))

    def test_invalid_cropped_image_rejected(self):
        import base64 as _b64
        bogus = 'data:image/png;base64,' + _b64.b64encode(b'not really an image').decode()
        self.client.post('/edit-profile/', {'cropped_image': bogus})
        self.user.refresh_from_db()
        self.assertFalse(bool(self.user.profile_picture))

