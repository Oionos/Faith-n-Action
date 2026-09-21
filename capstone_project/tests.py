from django.test import TestCase

from capstone_project.models import User


class RegistrationSecurityTests(TestCase):
    """Regression tests for the SEC-1 backdoor: User.save() used to promote any
    account named 'Mr_Admin' to role='admin'. Removed 2026-09-22."""

    def test_reserved_username_does_not_become_admin(self):
        user = User.objects.create_user(
            username='Mr_Admin', password='testpass123!', role='pending'
        )
        self.assertEqual(user.role, 'pending')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_normal_registration_stays_pending(self):
        user = User.objects.create_user(
            username='ordinarymember', password='testpass123!', role='pending'
        )
        self.assertEqual(user.role, 'pending')

    def test_save_never_escalates_role(self):
        user = User.objects.create_user(
            username='member2', password='testpass123!', role='member'
        )
        user.first_name = 'Changed'
        user.save()
        self.assertEqual(User.objects.get(pk=user.pk).role, 'member')

