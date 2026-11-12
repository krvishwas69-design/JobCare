from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Employer, Invoice, PaymentOrder


@admin.register(Employer)
class EmployerAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'company', 'job_credits', 'db_credits', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Hiring account', {'fields': ('company', 'phone', 'job_credits', 'db_credits', 'active_slots', 'unlimited_until')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hiring account', {'fields': ('company', 'phone')}),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'employer', 'plan', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'employer', 'plan', 'amount_paise', 'status', 'created_at', 'paid_at')
    list_filter = ('status',)
    readonly_fields = ('order_id', 'employer', 'plan', 'amount_paise', 'status', 'payment_id', 'created_at', 'paid_at')
