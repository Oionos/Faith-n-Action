from django.test import TestCase

from capstone_project.models import Council, Notification, Recruitment, User


class RecruitmentTests(TestCase):
    """add_recruitment / my_recruits / undo_recruitment + recalculate_degree side-effects."""

    def setUp(self):
        self.client.raise_request_exception = False
        self.council = Council.objects.create(id=1, name='Test Council', district='Test District')
        self.admin = User.objects.create_user(username='r_admin', password='pass12345!', role='admin', council=self.council)
        self.admin2 = User.objects.create_user(username='r_admin2', password='pass12345!', role='admin', council=self.council)
        self.officer = User.objects.create_user(username='r_officer', password='pass12345!', role='officer', council=self.council)
        self.recruiter = User.objects.create_user(username='r_recruiter', password='pass12345!', role='member', council=self.council)
        self.recruit = User.objects.create_user(username='r_recruit', password='pass12345!', role='member', council=self.council)

    def test_admin_adds_manual_recruitment_and_degree_recalculates(self):
        self.client.force_login(self.admin)
        resp = self.client.post('/add-recruitment/',
                                {'recruiter_id': self.recruiter.id, 'recruit_id': self.recruit.id})
        record = Recruitment.objects.get(recruiter=self.recruiter, recruited=self.recruit)
        self.assertTrue(record.is_manual)
        self.assertEqual(record.added_by, self.admin)
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.current_degree, '2nd')  # 1 recent recruit -> 2nd
        self.assertTrue(Notification.objects.filter(user=self.recruiter, title__icontains='promoted').exists())

    def test_non_admin_cannot_add_recruitment(self):
        self.client.force_login(self.officer)
        self.client.post('/add-recruitment/',
                         {'recruiter_id': self.recruiter.id, 'recruit_id': self.recruit.id})
        self.assertFalse(Recruitment.objects.exists())

    def test_duplicate_recruitment_is_not_created_twice(self):
        Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                   is_manual=True, added_by=self.admin)
        self.client.force_login(self.admin)
        self.client.post('/add-recruitment/',
                         {'recruiter_id': self.recruiter.id, 'recruit_id': self.recruit.id})
        self.assertEqual(Recruitment.objects.count(), 1)

    def test_unknown_recruit_creates_no_record(self):
        self.client.force_login(self.admin)
        self.client.post('/add-recruitment/',
                         {'recruiter_id': self.recruiter.id, 'recruit_id': 99999})
        self.assertFalse(Recruitment.objects.exists())

    def test_my_recruits_lists_own_recruits(self):
        Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                   is_manual=True, added_by=self.admin)
        self.client.force_login(self.recruiter)
        resp = self.client.get('/my-recruits/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_recruits'], 1)
        self.assertEqual(resp.context['recent_recruits'], 1)
        self.assertEqual(resp.context['next_degree'], '2nd Degree')

    def test_my_recruits_progress_for_first_degree(self):
        self.client.force_login(self.recruiter)
        resp = self.client.get('/my-recruits/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_recruits'], 0)
        self.assertEqual(resp.context['recruits_needed'], 1)  # 1st -> 2nd needs 1 recent recruit

    def test_admin_undoes_own_manual_recruitment(self):
        record = Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                            is_manual=True, added_by=self.admin)
        self.client.force_login(self.admin)
        self.client.post(f'/undo-recruitment/{record.id}/')
        self.assertFalse(Recruitment.objects.filter(id=record.id).exists())

    def test_admin_cannot_undo_another_admins_recruitment(self):
        record = Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                            is_manual=True, added_by=self.admin)
        self.client.force_login(self.admin2)
        self.client.post(f'/undo-recruitment/{record.id}/')
        self.assertTrue(Recruitment.objects.filter(id=record.id).exists())

    def test_cannot_undo_non_manual_recruitment(self):
        record = Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                            is_manual=False)
        self.client.force_login(self.admin)
        self.client.post(f'/undo-recruitment/{record.id}/')
        self.assertTrue(Recruitment.objects.filter(id=record.id).exists())

    def test_non_admin_cannot_undo_recruitment(self):
        record = Recruitment.objects.create(recruiter=self.recruiter, recruited=self.recruit,
                                            is_manual=True, added_by=self.admin)
        self.client.force_login(self.officer)
        self.client.post(f'/undo-recruitment/{record.id}/')
        self.assertTrue(Recruitment.objects.filter(id=record.id).exists())
