from django.test import TestCase

from capstone_project.models import Council, User


class ArchiveUserTests(TestCase):
    """archive_user / archived_users — admin-only account lifecycle."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='ua_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='ua_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='ua_member', password='pass12345!', role='member', council=self.council)

    def test_admin_archives_member(self):
        self.client.force_login(self.admin)
        resp = self.client.get(f'/archive-user/{self.member.id}/')
        self.assertEqual(resp.status_code, 302)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_archived)
        self.assertFalse(self.member.is_active)

    def test_admin_cannot_archive_themselves(self):
        self.client.force_login(self.admin)
        self.client.get(f'/archive-user/{self.admin.id}/')
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_archived)

    def test_non_admin_cannot_archive(self):
        self.client.force_login(self.officer)
        self.client.get(f'/archive-user/{self.member.id}/')
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_archived)

    def test_archiving_already_archived_user_is_404(self):
        self.member.is_archived = True
        self.member.save()
        self.client.force_login(self.admin)
        resp = self.client.get(f'/archive-user/{self.member.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_archived_users_list_is_admin_only(self):
        self.member.is_archived = True
        self.member.save()
        self.client.force_login(self.admin)
        resp = self.client.get('/archived-users/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.member, resp.context['archived_users'])

        self.client.force_login(self.officer)
        self.assertEqual(self.client.get('/archived-users/').status_code, 302)


class ChangeCouncilTests(TestCase):
    """change_council — admin any member; officer restricted to own-council members."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council1 = Council.objects.create(id=1, name='Council One', district='D')
        self.council2 = Council.objects.create(id=2, name='Council Two', district='D')
        self.admin = User.objects.create_user(username='cc_admin', password='pass12345!', role='admin', council=self.council1)
        self.officer = User.objects.create_user(username='cc_officer', password='pass12345!', role='officer', council=self.council1)
        self.member = User.objects.create_user(username='cc_member', password='pass12345!', role='member', council=self.council1)
        self.outsider = User.objects.create_user(username='cc_outsider', password='pass12345!', role='member', council=self.council2)

    def test_admin_moves_any_member(self):
        self.client.force_login(self.admin)
        resp = self.client.post(f'/change-council/{self.outsider.id}/', {'council': self.council1.id})
        self.assertEqual(resp.status_code, 302)
        self.outsider.refresh_from_db()
        self.assertEqual(self.outsider.council, self.council1)

    def test_officer_moves_member_in_own_council(self):
        self.client.force_login(self.officer)
        self.client.post(f'/change-council/{self.member.id}/', {'council': self.council2.id})
        self.member.refresh_from_db()
        self.assertEqual(self.member.council, self.council2)

    def test_officer_cannot_move_member_from_another_council(self):
        self.client.force_login(self.officer)
        self.client.post(f'/change-council/{self.outsider.id}/', {'council': self.council1.id})
        self.outsider.refresh_from_db()
        self.assertEqual(self.outsider.council, self.council2)  # unchanged

    def test_officer_cannot_move_an_officer(self):
        target = User.objects.create_user(username='cc_officer2', password='pass12345!',
                                          role='officer', council=self.council1)
        self.client.force_login(self.officer)
        self.client.post(f'/change-council/{target.id}/', {'council': self.council2.id})
        target.refresh_from_db()
        self.assertEqual(target.council, self.council1)  # unchanged

    def test_member_cannot_change_council(self):
        self.client.force_login(self.member)
        self.client.post(f'/change-council/{self.outsider.id}/', {'council': self.council1.id})
        self.outsider.refresh_from_db()
        self.assertEqual(self.outsider.council, self.council2)  # unchanged
