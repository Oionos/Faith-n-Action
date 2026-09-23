from django.test import TestCase

from capstone_project.models import Analytics, Council, Event, User


class AnalyticsFormTests(TestCase):
    """analytics_form is officer-only (admins are redirected by design)."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='a_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='a_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='a_member', password='pass12345!', role='member', council=self.council)

    def test_officer_submits_analytics(self):
        self.client.force_login(self.officer)
        resp = self.client.post('/analytics-form/', {'events_count': '3', 'donations_amount': '1500.50'})
        self.assertEqual(resp.status_code, 302)
        record = Analytics.objects.get(council=self.council)
        self.assertEqual(record.events_count, 3)
        self.assertEqual(float(record.donations_amount), 1500.50)
        self.assertEqual(record.updated_by, self.officer)

    def test_officer_update_replaces_existing_record(self):
        Analytics.objects.create(council=self.council, events_count=1, donations_amount=10)
        self.client.force_login(self.officer)
        self.client.post('/analytics-form/', {'events_count': '7', 'donations_amount': '99.99'})
        self.assertEqual(Analytics.objects.filter(council=self.council).count(), 1)
        record = Analytics.objects.get(council=self.council)
        self.assertEqual(record.events_count, 7)

    def test_admin_is_redirected_from_analytics_form(self):
        self.client.force_login(self.admin)
        resp = self.client.post('/analytics-form/', {'events_count': '5', 'donations_amount': '5'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Analytics.objects.exists())

    def test_member_is_redirected_from_analytics_form(self):
        self.client.force_login(self.member)
        resp = self.client.get('/analytics-form/')
        self.assertEqual(resp.status_code, 302)


class AnalyticsViewTests(TestCase):
    """analytics_view renders the pandas/Chart.js dashboard; officers are
    scoped to their own council, admins may filter by council."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='av_admin', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='av_officer', password='pass12345!', role='officer', council=self.council)
        self.member = User.objects.create_user(username='av_member', password='pass12345!', role='member', council=self.council)
        Event.objects.create(name='Done Event', description='d', category='Service',
                             street='s', barangay='b', city='c', province='p',
                             date_from='2026-01-01', status='approved', council=self.council)

    def test_officer_sees_own_council_dashboard(self):
        self.client.force_login(self.officer)
        resp = self.client.get('/analytics-view/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['is_officer'], True)

    def test_admin_can_filter_by_council(self):
        self.client.force_login(self.admin)
        resp = self.client.get('/analytics-view/', {'council_id': self.council.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['is_officer'], False)

    def test_admin_overview_without_filter(self):
        self.client.force_login(self.admin)
        resp = self.client.get('/analytics-view/')
        self.assertEqual(resp.status_code, 200)

    def test_member_is_redirected(self):
        self.client.force_login(self.member)
        resp = self.client.get('/analytics-view/')
        self.assertEqual(resp.status_code, 302)
