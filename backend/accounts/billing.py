"""Razorpay order creation, payment verification, and entitlement fulfillment."""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .models import Employer, Invoice, PaymentOrder
from .plans import PLANS

logger = logging.getLogger(__name__)
RAZORPAY_API = 'https://api.razorpay.com/v1'


class PaymentRequired(APIException):
    status_code = 402
    default_detail = 'Payment is required.'
    default_code = 'payment_required'


class PaymentGatewayError(APIException):
    status_code = 503
    default_detail = 'Payments are temporarily unavailable. Please try again later.'
    default_code = 'payment_gateway_unavailable'


def _credentials():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error('Razorpay keys are not configured.')
        raise PaymentGatewayError('Payments are not configured. Please contact support.')
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


def _gateway_request(method, path, payload=None):
    key_id, key_secret = _credentials()
    auth = base64.b64encode(f'{key_id}:{key_secret}'.encode()).decode()
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        RAZORPAY_API + path,
        data=data,
        headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'},
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        logger.error('Razorpay API returned HTTP %s for %s %s.', exc.code, method, path)
        raise PaymentGatewayError() from exc
    except (TimeoutError, URLError) as exc:
        logger.exception('Could not reach Razorpay for %s %s.', method, path)
        raise PaymentGatewayError() from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.exception('Razorpay returned an invalid response for %s %s.', method, path)
        raise PaymentGatewayError() from exc


def _grant_purchase(employer, pack, payment_order=None):
    plan = PLANS[pack]
    Employer.objects.filter(pk=employer.pk).update(
        job_credits=F('job_credits') + plan['job_credits'],
        db_credits=F('db_credits') + plan['db_credits'],
    )
    if plan['unlimited_days']:
        employer.refresh_from_db(fields=['unlimited_until'])
        start = max(employer.unlimited_until or timezone.localdate(), timezone.localdate())
        Employer.objects.filter(pk=employer.pk).update(unlimited_until=start + timedelta(days=plan['unlimited_days']))
    invoice = Invoice.objects.create(
        employer=employer,
        payment_order=payment_order,
        plan=plan['name'],
        amount=plan['amount'],
    )
    invoice.number = f'INV-{invoice.created_at.year}-{10000 + invoice.pk}'
    invoice.save(update_fields=['number'])
    employer.refresh_from_db()
    return invoice, employer


def start_purchase(employer, pack):
    """Create a checkout order; demo purchases are only available when explicitly enabled."""
    if pack not in ('credits', 'unlimited'):
        raise ValidationError({'detail': 'Unknown or unavailable plan.'})
    plan = PLANS[pack]
    if settings.DEMO_PAYMENTS:
        with transaction.atomic():
            invoice, employer = _grant_purchase(employer, pack)
        return {
            'demo': True,
            'message': f'{plan["name"]} activated (demo).',
            'invoice': invoice,
            'user': employer,
        }

    order_data = _gateway_request('POST', '/orders', {
        'amount': plan['amount'] * 100,
        'currency': 'INR',
        'receipt': f'jobcare-{uuid.uuid4().hex}',
        'notes': {'employer_id': str(employer.pk), 'plan': pack},
    })
    order_id = order_data.get('id')
    if (not order_id or order_data.get('status') != 'created'
            or order_data.get('amount') != plan['amount'] * 100
            or order_data.get('currency') != 'INR'):
        logger.error('Razorpay returned an invalid order response.')
        raise PaymentGatewayError()
    payment_order = PaymentOrder.objects.create(
        employer=employer,
        order_id=order_id,
        plan=pack,
        amount_paise=plan['amount'] * 100,
    )
    return {
        'demo': False,
        'key_id': settings.RAZORPAY_KEY_ID,
        'order_id': payment_order.order_id,
        'amount': payment_order.amount_paise,
        'currency': 'INR',
        'name': 'Job Care',
        'description': plan['name'],
        'prefill': {
            'name': employer.display_name,
            'email': employer.email,
            'contact': employer.phone,
        },
    }


def verify_checkout_signature(order_id, payment_id, signature):
    _, key_secret = _credentials()
    expected = hmac.new(
        key_secret.encode(),
        f'{order_id}|{payment_id}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValidationError({'detail': 'Payment signature could not be verified.'})


def _record_captured_payment(order_id, payment_id, amount_paise, currency):
    with transaction.atomic():
        try:
            payment_order = PaymentOrder.objects.select_for_update().get(order_id=order_id)
        except PaymentOrder.DoesNotExist as exc:
            raise ValidationError({'detail': 'Payment order was not found.'}) from exc
        if payment_order.status == PaymentOrder.CAPTURED:
            if payment_order.payment_id != payment_id:
                raise ValidationError({'detail': 'This order is already associated with another payment.'})
            return payment_order.invoice, payment_order.employer
        if payment_order.status != PaymentOrder.PENDING:
            raise ValidationError({'detail': 'This payment order is no longer pending.'})
        if amount_paise != payment_order.amount_paise or currency != 'INR':
            logger.error('Razorpay payment amount/currency did not match order %s.', order_id)
            raise ValidationError({'detail': 'The captured payment does not match the order.'})

        payment_order.status = PaymentOrder.CAPTURED
        payment_order.payment_id = payment_id
        payment_order.paid_at = timezone.now()
        payment_order.save(update_fields=['status', 'payment_id', 'paid_at'])
        invoice, employer = _grant_purchase(payment_order.employer, payment_order.plan, payment_order)
        return invoice, employer


def verify_and_fulfill(employer, order_id, payment_id, signature):
    verify_checkout_signature(order_id, payment_id, signature)
    payment = _gateway_request('GET', '/payments/' + quote(payment_id, safe=''))
    if payment.get('order_id') != order_id or payment.get('id') != payment_id:
        raise ValidationError({'detail': 'Payment does not match the checkout order.'})
    if payment.get('status') != 'captured':
        raise PaymentRequired({'detail': 'Payment has not been captured yet.', 'code': 'payment_pending'})
    order = PaymentOrder.objects.filter(order_id=order_id, employer=employer).first()
    if not order:
        raise ValidationError({'detail': 'Payment order was not found.'})
    invoice, updated_employer = _record_captured_payment(
        order_id, payment_id, payment.get('amount'), payment.get('currency'))
    return invoice, updated_employer


def verify_webhook_signature(body, signature):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error('Razorpay webhook secret is not configured.')
        raise PaymentGatewayError('Payment notifications are not configured.')
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValidationError({'detail': 'Webhook signature could not be verified.'})


def process_webhook_payment(payment):
    if payment.get('status') != 'captured':
        return
    order_id = payment.get('order_id')
    payment_id = payment.get('id')
    if not order_id or not payment_id:
        raise ValidationError({'detail': 'Webhook payment details are incomplete.'})
    _record_captured_payment(order_id, payment_id, payment.get('amount'), payment.get('currency'))
