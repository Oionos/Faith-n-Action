import unittest
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase

from capstone_project.models import Council, Donation, User


class GcashConfirmationTests(TestCase):
    """Payment-confirmation integrity (SEC-6).

    confirm_gcash_payment fetches the PayMongo source server-side but never
    compares the source amount to the donation amount, and accepts both ids
    from the query string. The mismatch test is expectedFailure until
    views.py gains amount validation; an unexpected success means the fix
    landed and the decorator should be removed.
    """

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.user = User.objects.create_user(username='donor', password='pass12345!', role='member', council=self.council)

    def _donation(self, amount, status='pending'):
        return Donation.objects.create(
            transaction_id=f"GCASH-{uuid.uuid4().hex[:8]}",
            first_name='Test', middle_initial='T', last_name='Donor',
            email='donor@example.com', amount=Decimal(amount),
            donation_date=date.today(), payment_method='gcash',
            status=status, source_id='src_test_1', submitted_by=self.user,
        )

    def _source_payload(self, status='chargeable', amount_centavos=100):
        return {'data': {'attributes': {'status': status, 'amount': amount_centavos}}}

    @patch('capstone_project.views.requests.get')
    def test_pending_donation_stays_pending_when_source_not_chargeable(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: self._source_payload(status='failed'))
        donation = self._donation('1000.00')
        self.client.get('/gcash/confirm/', {'donation_id': donation.id, 'source_id': 'src_test_1'})
        donation.refresh_from_db()
        self.assertNotEqual(donation.status, 'completed')

    @unittest.expectedFailure  # views.py bug: get_object_or_404 raises Http404, which
    # 'except Donation.DoesNotExist' never catches; the broad 'except Exception'
    # then references 'donation' before assignment -> UnboundLocalError -> 500.
    @patch('capstone_project.views.requests.get')
    def test_completed_donation_cannot_be_reconfirmed(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: self._source_payload())
        donation = self._donation('1000.00', status='completed')
        resp = self.client.get('/gcash/confirm/', {'donation_id': donation.id, 'source_id': 'src_test_1'})
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'completed')  # unchanged, not re-processed
        self.assertIn(resp.status_code, (301, 302, 404))

    @unittest.expectedFailure  # SEC-6: amount is never verified against the source
    @patch('capstone_project.views.requests.get')
    def test_amount_mismatch_does_not_complete_donation(self, mock_get):
        # Source paid PHP 1.00; donation claims PHP 10,000.00
        mock_get.return_value = Mock(status_code=200, json=lambda: self._source_payload(amount_centavos=100))
        donation = self._donation('10000.00')
        self.client.get('/gcash/confirm/', {'donation_id': donation.id, 'source_id': 'src_test_1'})
        donation.refresh_from_db()
        self.assertEqual(donation.status, 'pending')

    @patch('capstone_project.views.requests.get')
    def test_missing_donation_id_redirects_without_crash(self, mock_get):
        resp = self.client.get('/gcash/confirm/')
        self.assertLess(resp.status_code, 500)
