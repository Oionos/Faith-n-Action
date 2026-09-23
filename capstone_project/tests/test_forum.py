import json

from django.test import TestCase

from capstone_project.models import Council, ForumCategory, ForumMessage, Notification, User


class ForumFlowTests(TestCase):
    """send_message / get_messages / delete_message / pin_message across roles."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='f_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='f_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='f_member', password='pass12345!', role='member', council=self.council)
        self.other = User.objects.create_user(username='f_other', password='pass12345!', role='member', council=self.council)
        self.category = ForumCategory.objects.create(name='general', description='General discussion')

    def _send(self, content, forum_type='council', as_user=None):
        self.client.force_login(as_user or self.member)
        return self.client.post('/forum/send/', {
            'category_id': self.category.id,
            'content': content,
            'forum_type': forum_type,
        })

    def test_member_can_send_council_message(self):
        resp = self._send('Hello council')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        msg = ForumMessage.objects.get(content='Hello council')
        self.assertEqual(msg.sender, self.member)
        self.assertFalse(msg.is_district_forum)
        # bulk notifications created for other users
        self.assertTrue(Notification.objects.filter(message=msg, user=self.other).exists())
        self.assertFalse(Notification.objects.filter(message=msg, user=self.member).exists())

    def test_district_message_scoped_to_council(self):
        self._send('private note', forum_type='district')
        msg = ForumMessage.objects.get(content='private note')
        self.assertTrue(msg.is_district_forum)

        # same-council officer sees it in the district feed
        self.client.force_login(self.officer)
        resp = self.client.get(f'/forum/messages/{self.category.id}/', {'forum_type': 'district'})
        self.assertTrue(any(m['content'] == 'private note' for m in resp.json()['messages']))

    def test_send_message_requires_authentication(self):
        resp = self.client.post('/forum/send/', {'category_id': self.category.id, 'content': 'anon'})
        self.assertIn(resp.status_code, (301, 302, 403))

    def test_send_message_missing_category_returns_400(self):
        resp = self._send('no category', as_user=self.member)
        self.client.force_login(self.member)
        resp = self.client.post('/forum/send/', {'category_id': 9999, 'content': 'x'})
        self.assertEqual(resp.status_code, 400)

    def test_sender_can_delete_own_message(self):
        self._send('mine')
        msg = ForumMessage.objects.get(content='mine')
        self.client.force_login(self.member)
        resp = self.client.post(f'/forum/delete/{msg.id}/')
        self.assertEqual(resp.json()['status'], 'success')
        self.assertFalse(ForumMessage.objects.filter(id=msg.id).exists())

    def test_member_cannot_delete_others_message(self):
        self._send('theirs', as_user=self.officer)
        msg = ForumMessage.objects.get(content='theirs')
        self.client.force_login(self.member)
        resp = self.client.post(f'/forum/delete/{msg.id}/')
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ForumMessage.objects.filter(id=msg.id).exists())

    def test_admin_can_delete_any_message(self):
        self._send('admin target', as_user=self.member)
        msg = ForumMessage.objects.get(content='admin target')
        self.client.force_login(self.admin)
        resp = self.client.post(f'/forum/delete/{msg.id}/')
        self.assertEqual(resp.json()['status'], 'success')
        self.assertFalse(ForumMessage.objects.filter(id=msg.id).exists())

    def test_pin_officer_allowed_member_denied(self):
        self._send('pin me', as_user=self.member)
        msg = ForumMessage.objects.get(content='pin me')
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(f'/forum/pin/{msg.id}/').status_code, 403)

        self.client.force_login(self.officer)
        resp = self.client.post(f'/forum/pin/{msg.id}/')
        self.assertEqual(resp.json()['status'], 'success')
        self.assertTrue(resp.json()['is_pinned'])
        msg.refresh_from_db()
        self.assertTrue(msg.is_pinned)
