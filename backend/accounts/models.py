from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Employer(AbstractUser):
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    job_credits = models.PositiveIntegerField(default=0)
    db_credits = models.PositiveIntegerField(default=15)
    active_slots = models.PositiveIntegerField(default=1)
    unlimited_until = models.DateField(null=True, blank=True)

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.username

    @property
    def has_unlimited(self):
        return bool(self.unlimited_until and self.unlimited_until >= timezone.localdate())

    def __str__(self):
        return f'{self.display_name} ({self.company or "no company"})'


class PaymentOrder(models.Model):
    PENDING, CAPTURED, FAILED = 'pending', 'captured', 'failed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (CAPTURED, 'Captured'), (FAILED, 'Failed')]

    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_orders')
    order_id = models.CharField(max_length=100, unique=True)
    plan = models.CharField(max_length=40)
    amount_paise = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    payment_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.order_id} ({self.status})'


class Invoice(models.Model):
    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    payment_order = models.OneToOneField(
        PaymentOrder, null=True, blank=True, on_delete=models.PROTECT, related_name='invoice')
    number = models.CharField(max_length=30, blank=True)
    plan = models.CharField(max_length=100)
    amount = models.PositiveIntegerField(help_text='Amount in rupees')
    status = models.CharField(max_length=10, default='Paid')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.number} - {self.plan}'
