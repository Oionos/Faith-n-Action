from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from unittest import expectedFailure

from capstone_project.models import Council, User


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
            'e_signature': SimpleUploadedFile('sig.png', b'\x89PNG-fake', content_type='image/png'),
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

    @expectedFailure  # SEC-14: content_type is client-controlled — text bytes with an
    # image content-type pass. Fix: validate by decoding the image, not the header.
    def test_e_signature_content_type_spoof_rejected(self):
        self._post(e_signature=SimpleUploadedFile('sig.png', b'this is not an image', content_type='image/png'))
        self.assertFalse(User.objects.filter(username='newmember').exists())

    @expectedFailure  # views.py uses create_user directly — AUTH_PASSWORD_VALIDATORS
    # never run on this path, so trivial passwords are accepted today.
    def test_weak_password_rejected(self):
        self._post(password='123', re_password='123')
        self.assertFalse(User.objects.filter(username='newmember').exists())

    def test_authenticated_user_redirected_to_dashboard(self):
        User.objects.create_user(username='logged', password='pass12345!', role='member', council=self.council)
        self.client.force_login(User.objects.get(username='logged'))
        resp = self.client.get('/sign-up/')
        self.assertEqual(resp.status_code, 302)
