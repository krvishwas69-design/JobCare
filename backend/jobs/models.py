from django.conf import settings
from django.db import models


class Job(models.Model):
    DRAFT, ACTIVE, CLOSED = 'draft', 'active', 'closed'
    STATUS_CHOICES = [(DRAFT, 'Draft'), (ACTIVE, 'Active'), (CLOSED, 'Closed')]

    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=50, default='General')
    job_type = models.CharField(max_length=20, default='Full Time')
    location = models.CharField(max_length=200)
    min_salary = models.PositiveIntegerField(default=0)
    max_salary = models.PositiveIntegerField(default=0)
    openings = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    plan = models.CharField(max_length=20, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class Candidate(models.Model):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    area = models.CharField(max_length=100, blank=True)
    experience = models.CharField(max_length=50, blank=True)
    expected_salary = models.CharField(max_length=50, blank=True)
    skills = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=20)
    available_in_database = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.role}'


class Application(models.Model):
    APPLIED, SHORTLISTED, INTERVIEWED, HIRED, REJECTED = 'applied', 'shortlisted', 'interviewed', 'hired', 'rejected'
    STATUS_CHOICES = [(APPLIED, 'Applied'), (SHORTLISTED, 'Shortlisted'), (INTERVIEWED, 'Interviewed'),
                      (HIRED, 'Hired'), (REJECTED, 'Rejected')]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ['-applied_at', '-id']
        constraints = [models.UniqueConstraint(fields=['job', 'candidate'], name='unique_application_per_job')]


class CandidateUnlock(models.Model):
    """An employer spent one database credit to reveal a candidate's phone number."""
    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='unlocks')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='unlocks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['employer', 'candidate'], name='unique_unlock_per_employer')]
