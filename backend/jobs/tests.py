from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Employer

from .models import Application, Candidate, Job


class CandidateMarketplaceTests(APITestCase):
    def setUp(self):
        self.employer = Employer.objects.create_user(username='employer@example.test', password='Strong-pass-123')
        self.other_employer = Employer.objects.create_user(username='other@example.test', password='Strong-pass-456')
        self.job = Job.objects.create(
            posted_by=self.employer,
            title='Warehouse Associate',
            location='Bengaluru',
            status=Job.ACTIVE,
        )

    def test_application_requires_consent_and_stays_out_of_searchable_database(self):
        url = f'/api/public/jobs/{self.job.pk}/apply/'
        payload = {'name': 'Applicant One', 'phone': '9876543210'}

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Candidate.objects.exists())
        response = self.client.post(url, {**payload, 'consent': False}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Candidate.objects.exists())

        response = self.client.post(url, {**payload, 'consent': True}, format='json')
        self.assertEqual(response.status_code, 201)
        candidate = Candidate.objects.get(phone='9876543210')
        application = Application.objects.get(job=self.job, candidate=candidate)
        self.assertFalse(candidate.available_in_database)
        self.assertIsNotNone(application.consent_at)
        self.assertEqual(application.consent_version, 'job-application-v1')

        self.client.force_authenticate(self.employer)
        response = self.client.get('/api/candidates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_employer_can_review_applicants_for_owned_jobs_only(self):
        candidate = Candidate.objects.create(name='Applicant Two', phone='9876543211')
        application = Application.objects.create(
            job=self.job,
            candidate=candidate,
            consent_at=timezone.now(),
        )
        self.client.force_authenticate(self.employer)
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['candidate_phone'], candidate.phone)

        response = self.client.patch(
            f'/api/applications/{application.pk}/',
            {'status': Application.SHORTLISTED},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], Application.SHORTLISTED)

        self.client.force_authenticate(self.other_employer)
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_public_apply_rejects_honeypot_and_normalizes_phone(self):
        url = f'/api/public/jobs/{self.job.pk}/apply/'
        response = self.client.post(url, {
            'name': 'Applicant One',
            'phone': '+91 9876543210',
            'consent': True,
            'website': 'https://example.com',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(url, {
            'name': 'Applicant One',
            'phone': '+91 9876543210',
            'consent': True,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        candidate = Candidate.objects.get(phone='9876543210')
        self.assertEqual(candidate.name, 'Applicant One')
