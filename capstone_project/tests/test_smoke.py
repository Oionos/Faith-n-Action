from django.test import TestCase

from capstone_project.models import Council, User


class RenderSmokeTests(TestCase):
    """Every primary page must render (or redirect) without a 5xx for each role.
    These catch template/view crashes that permission tests do not."""

    PUBLIC_PATHS = ['/', '/sign-in/', '/sign-up/', '/about_us/', '/mission_vision/', '/faith-action/']
    MEMBER_PATHS = [
        '/dashboard/', '/councils/', '/council/1/', '/donations/', '/event-list/',
        '/council-events/', '/forum/', '/leaderboard/', '/blockchain/',
        '/edit-profile/', '/my-recruits/', '/member-activities/',
    ]

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.member = User.objects.create_user(username='smoke_member', password='pass12345!', role='member', council=self.council)
        self.officer = User.objects.create_user(username='smoke_officer', password='pass12345!', role='officer', council=self.council)
        self.admin = User.objects.create_user(username='smoke_admin', password='pass12345!', role='admin', council=self.council)
        self.pending = User.objects.create_user(username='smoke_pending', password='pass12345!', role='pending', council=self.council)

    def _assert_no_5xx(self, urls):
        for url in urls:
            resp = self.client.get(url)
            self.assertLess(resp.status_code, 500, f'GET {url} -> {resp.status_code}')

    def test_public_pages_anonymous(self):
        self._assert_no_5xx(self.PUBLIC_PATHS)

    def test_member_pages(self):
        self.client.force_login(self.member)
        self._assert_no_5xx(self.MEMBER_PATHS)

    def test_officer_pages(self):
        self.client.force_login(self.officer)
        self._assert_no_5xx(self.MEMBER_PATHS + [
            '/pending-users/', '/manage-roles/', '/add-event/', '/event-proposals/',
            '/council-members/', '/add-recruitment/', '/review_manual_donations/',
        ])

    def test_admin_pages(self):
        self.client.force_login(self.admin)
        self._assert_no_5xx(self.MEMBER_PATHS + [
            '/pending-users/', '/archived-users/', '/manage-roles/', '/analytics-form/',
            '/analytics-view/', '/donation-reports/', '/review_manual_donations/',
        ])

    def test_pending_user_is_contained(self):
        self.client.force_login(self.pending)
        self._assert_no_5xx(['/dashboard/', '/forum/', '/edit-profile/'])
