from django.test import Client, TestCase

from capstone_project.models import Council, User


class PermissionMatrixTests(TestCase):
    """Role-based access control exercised across the URL surface.

    SEC-5 (IDOR in user_details) and SEC-8 (duplicate undecorated
    update_degree) are fixed as of 2026-09-22; the tests that documented them
    are no longer marked expectedFailure and now serve as permanent guards.
    """

    ADMIN_MUTATION_PATHS = [
        '/approve-user/{u}/',
        '/reject-user/{u}/',
        '/promote-user/{u}/',
        '/demote-user/{u}/',
    ]

    PROTECTED_GET_PATHS = [
        '/dashboard/', '/pending-users/', '/archived-users/', '/councils/',
        '/council/1/', '/donations/', '/donation-reports/', '/manual_donation/',
        '/review_manual_donations/', '/blockchain/', '/forum/', '/manage-roles/',
        '/add-event/', '/event-proposals/', '/event-list/',
        '/council-events/', '/member-activities/',
        '/my-recruits/', '/add-recruitment/', '/leaderboard/', '/analytics-form/',
        '/analytics-view/', '/edit-profile/', '/user/1/details/',
    ]

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='t_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='t_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='t_member', password='pass12345!', role='member', council=self.council)
        self.other_member = User.objects.create_user(username='t_other', password='pass12345!', role='member', council=self.council)

    def test_anonymous_cannot_call_admin_mutations(self):
        for path in self.ADMIN_MUTATION_PATHS:
            url = path.format(u=self.member.id)
            for method in ('get', 'post'):
                resp = getattr(self.client, method)(url)
                self.assertIn(
                    resp.status_code, (301, 302, 403, 404),
                    f'anonymous {method.upper()} {url} returned {resp.status_code}',
                )

    def test_member_cannot_call_admin_mutations(self):
        self.client.force_login(self.member)
        for path in self.ADMIN_MUTATION_PATHS:
            url = path.format(u=self.other_member.id)
            for method in ('get', 'post'):
                resp = getattr(self.client, method)(url)
                self.assertIn(
                    resp.status_code, (301, 302, 403, 404),
                    f'member {method.upper()} {url} returned {resp.status_code}',
                )

    def test_officer_cannot_promote_or_demote(self):
        self.client.force_login(self.officer)
        for path in ('/promote-user/{u}/', '/demote-user/{u}/'):
            resp = self.client.get(path.format(u=self.member.id))
            self.assertNotEqual(resp.status_code, 200, f'officer reached {path}')

    def test_no_5xx_on_any_get_anonymous(self):
        for url in self.PROTECTED_GET_PATHS:
            resp = self.client.get(url)
            self.assertLess(resp.status_code, 500, f'anonymous GET {url} -> {resp.status_code}')

    def test_no_5xx_on_any_get_as_member(self):
        self.client.force_login(self.member)
        for url in self.PROTECTED_GET_PATHS + ['/member-list/', '/council-members/']:
            resp = self.client.get(url)
            self.assertLess(resp.status_code, 500, f'member GET {url} -> {resp.status_code}')

    def test_anonymous_member_list_rejected_not_500(self):  # guard: member_list now has @login_required
        resp = self.client.get('/member-list/')
        self.assertIn(resp.status_code, (301, 302, 403, 404))

    def test_anonymous_council_members_rejected_not_500(self):  # guard: council_members now has @login_required
        resp = self.client.get('/council-members/')
        self.assertIn(resp.status_code, (301, 302, 403, 404))

    def test_member_cannot_read_other_members_full_details(self):  # SEC-5 guard (fixed 2026-09-22)
        self.client.force_login(self.member)
        resp = self.client.get(f'/user/{self.other_member.id}/details/')
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_update_degree_is_rejected_not_500(self):  # SEC-8 guard (duplicate def removed)
        resp = self.client.get(f'/update-degree/{self.member.id}/')
        self.assertIn(resp.status_code, (301, 302, 403, 404))
