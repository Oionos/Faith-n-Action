import json

from django.http import Http404
from django.test import RequestFactory, TestCase

from capstone_project.models import (
    Council, ForumCategory, ForumMessage, Notification, User,
)
from capstone_project.views import get_notifications, mark_notification_read


class NotificationViewTests(TestCase):
    """Logic-level tests for the notification views.

    IMPORTANT: get_notifications and mark_notification_read have NO URL routes
    (verified 2026-09-22 — neither URLconf contains 'notification'), so they
    cannot be tested through the test client. They are driven directly with
    RequestFactory. See DEPLOYMENT.md 'Notification wiring gap'.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.user = User.objects.create_user(username='n_user', password='pass12345!', role='member', council=self.council)
        self.other = User.objects.create_user(username='n_other', password='pass12345!', role='member', council=self.council)
        self.category = ForumCategory.objects.create(name='general', description='General')
        self.message = ForumMessage.objects.create(
            sender=self.other, category=self.category, content='hello there', council=self.council)

    def _call(self, view, user, *args):
        request = self.factory.get('/')
        request.user = user
        return view(request, *args)

    def test_returns_only_own_unread_notifications(self):
        Notification.objects.create(user=self.user, message=self.message)
        Notification.objects.create(user=self.other, message=self.message)          # someone else's
        Notification.objects.create(user=self.user, message=self.message, is_read=True)  # already read
        data = json.loads(self._call(get_notifications, self.user).content)['notifications']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['sender'], 'n_other')

    def test_long_content_is_truncated(self):
        long_msg = ForumMessage.objects.create(
            sender=self.other, category=self.category, content='x' * 250, council=self.council)
        Notification.objects.create(user=self.user, message=long_msg)
        data = json.loads(self._call(get_notifications, self.user).content)['notifications']
        self.assertTrue(data[0]['content'].endswith('...'))

    def test_title_only_notification_does_not_crash(self):
        """recalculate_degree writes message=None notifications (title/content only);
        the endpoint must render them rather than raising AttributeError."""
        Notification.objects.create(user=self.user, title='Promoted to 2nd Degree',
                                    content='Congratulations!')
        resp = self._call(get_notifications, self.user)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(json.loads(resp.content)['notifications']), 1)

    def test_mark_read_sets_flag(self):
        notif = Notification.objects.create(user=self.user, message=self.message)
        self._call(mark_notification_read, self.user, notif.id)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_cannot_mark_another_users_notification(self):
        notif = Notification.objects.create(user=self.other, message=self.message)
        with self.assertRaises(Http404):
            self._call(mark_notification_read, self.user, notif.id)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)
