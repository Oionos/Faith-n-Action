import json
from datetime import date, timedelta

from django.test import TestCase

from capstone_project.models import Council, Event, EventAttendance, User


class EventLifecycleTests(TestCase):
    """add_event, approve_event, reject_event, update_attendance across roles."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.council2 = Council.objects.create(id=2, name='Other Council', district='Test District')
        self.admin = User.objects.create_user(username='ev_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='ev_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='ev_member', password='pass12345!', role='member', council=self.council)
        self.officer2 = User.objects.create_user(username='ev_officer2', password='pass12345!', role='officer', council=self.council2)

    def _event_data(self, **overrides):
        data = {
            'name': 'Feeding Program', 'description': 'Community outreach',
            'category': 'Community Service', 'subcategory': 'Feeding',
            'street': '1 Rizal St', 'barangay': 'Brgy', 'city': 'Lucena',
            'province': 'Quezon',
            'date_from': (date.today() + timedelta(days=7)).isoformat(),
        }
        data.update(overrides)
        return data

    def _add_event(self, as_user, **overrides):
        self.client.force_login(as_user)
        return self.client.post('/add-event/', self._event_data(**overrides))

    def _make_event(self, **overrides):
        data = {
            'name': 'Attendance Event', 'description': 'desc', 'category': 'Service',
            'street': '1 Rizal St', 'barangay': 'Brgy', 'city': 'Lucena',
            'province': 'Quezon', 'date_from': date.today(),
            'status': 'approved', 'council': self.council, 'is_global': False,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def test_officer_creates_pending_council_event(self):
        self._add_event(self.officer)
        event = Event.objects.get(name='Feeding Program')
        self.assertEqual(event.status, 'pending')
        self.assertEqual(event.council, self.council)
        self.assertFalse(event.is_global)

    def test_admin_creates_approved_global_event(self):
        self._add_event(self.admin, is_global='on')
        event = Event.objects.get(name='Feeding Program')
        self.assertEqual(event.status, 'approved')
        self.assertTrue(event.is_global)
        self.assertIsNone(event.council)
        self.assertEqual(event.approved_by, self.admin)

    def test_officer_cannot_force_global(self):
        self._add_event(self.officer, is_global='on')
        event = Event.objects.get(name='Feeding Program')
        self.assertFalse(event.is_global)
        self.assertEqual(event.status, 'pending')

    def test_member_cannot_add_event(self):
        self._add_event(self.member)
        self.assertFalse(Event.objects.filter(name='Feeding Program').exists())

    def test_admin_approves_pending_event(self):
        event = self._make_event(name='Awaiting', status='pending')
        self.client.force_login(self.admin)
        resp = self.client.get(f'/approve-event/{event.id}/')
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')
        self.assertEqual(event.approved_by, self.admin)

    def test_officer_cannot_approve_event(self):
        event = self._make_event(name='Awaiting', status='pending')
        self.client.force_login(self.officer)
        resp = self.client.get(f'/approve-event/{event.id}/')
        self.assertEqual(resp.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.status, 'pending')
        self.assertIsNone(event.approved_by)

    def test_admin_rejects_event_with_reason(self):
        event = self._make_event(name='Reject me', status='pending')
        self.client.force_login(self.admin)
        resp = self.client.post(f'/reject-event/{event.id}/', {
            'rejection_category': 'Budget', 'additional_notes': 'insufficient funds',
        })
        event.refresh_from_db()
        self.assertEqual(event.status, 'rejected')
        self.assertIn('Budget', event.rejection_reason)
        self.assertIn('insufficient funds', event.rejection_reason)

    def test_cannot_reject_non_pending_event(self):
        event = self._make_event(name='Already live', status='approved')
        self.client.force_login(self.admin)
        self.client.post(f'/reject-event/{event.id}/', {'rejection_category': 'Other'})
        event.refresh_from_db()
        self.assertEqual(event.status, 'approved')

    def test_officer_batch_marks_attendance(self):
        event = self._make_event()
        self.client.force_login(self.officer)
        resp = self.client.post('/event/update-attendance/',
                                data=json.dumps({'event_id': event.id, 'present_members': [self.member.id]}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'success')
        att = EventAttendance.objects.get(event=event, member=self.member)
        self.assertTrue(att.is_present)

    def test_member_cannot_update_attendance(self):
        event = self._make_event()
        self.client.force_login(self.member)
        resp = self.client.post('/event/update-attendance/',
                                data=json.dumps({'event_id': event.id, 'present_members': []}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    def test_officer_blocked_from_other_council_event(self):
        event = self._make_event(name='Their Event', council=self.council2)
        self.client.force_login(self.officer)
        resp = self.client.post('/event/update-attendance/',
                                data=json.dumps({'event_id': event.id, 'present_members': []}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 403)
