import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from . import billing
from .models import Employer, Invoice, PaymentOrder


@override_settings(
    DEMO_PAYMENTS=False,
    RAZORPAY_KEY_ID='rzp_test_public',
    RAZORPAY_KEY_SECRET='test-secret',
    RAZORPAY_WEBHOOK_SECRET='webhook-secret',
)
class RazorpayBillingTests(TestCase):
    def setUp(self):
        self.employer = Employer.objects.create_user(username='buyer@example.test', password='Strong-pass-123')
        self.gateway_order = {
            'id': 'order_test123',
            'amount': 999900,
            'currency': 'INR',
            'status': 'created',
        }

    def checkout_signature(self, order_id='order_test123', payment_id='pay_test123'):
        return hmac.new(
            b'test-secret',
            f'{order_id}|{payment_id}'.encode(),
            hashlib.sha256,
        ).hexdigest()

    @patch('accounts.billing._gateway_request')
    def test_order_does_not_grant_entitlements_before_payment_capture(self, gateway_request):
        gateway_request.return_value = self.gateway_order

        result = billing.start_purchase(self.employer, 'credits')

        self.assertEqual(result['order_id'], self.gateway_order['id'])
        self.assertEqual(result['amount'], self.gateway_order['amount'])
        self.assertEqual(PaymentOrder.objects.get().status, PaymentOrder.PENDING)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 0)
        self.assertFalse(Invoice.objects.exists())

    @patch('accounts.billing._gateway_request')
    def test_verified_captured_payment_grants_once_and_is_idempotent(self, gateway_request):
        gateway_request.return_value = self.gateway_order
        billing.start_purchase(self.employer, 'credits')
        gateway_request.return_value = {
            'id': 'pay_test123',
            'order_id': self.gateway_order['id'],
            'amount': self.gateway_order['amount'],
            'currency': 'INR',
            'status': 'captured',
        }

        first_invoice, first_user = billing.verify_and_fulfill(
            self.employer, 'order_test123', 'pay_test123', self.checkout_signature())
        second_invoice, second_user = billing.verify_and_fulfill(
            self.employer, 'order_test123', 'pay_test123', self.checkout_signature())

        self.assertEqual(first_invoice.pk, second_invoice.pk)
        self.assertEqual(first_user.job_credits, 22)
        self.assertEqual(second_user.job_credits, 22)
        self.assertEqual(Invoice.objects.count(), 1)
        gateway_request.assert_called_with('GET', '/payments/pay_test123')

    @patch('accounts.billing._gateway_request')
    def test_invalid_signature_never_grants_entitlements(self, gateway_request):
        gateway_request.return_value = self.gateway_order
        billing.start_purchase(self.employer, 'credits')
        with self.assertRaises(ValidationError):
            billing.verify_and_fulfill(self.employer, 'order_test123', 'pay_test123', 'invalid')
        gateway_request.assert_called_once()
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 0)
        self.assertFalse(Invoice.objects.exists())

    @patch('accounts.billing._gateway_request')
    def test_non_captured_payment_does_not_grant_entitlements(self, gateway_request):
        gateway_request.return_value = self.gateway_order
        billing.start_purchase(self.employer, 'credits')
        gateway_request.return_value = {
            'id': 'pay_test123',
            'order_id': self.gateway_order['id'],
            'amount': self.gateway_order['amount'],
            'currency': 'INR',
            'status': 'authorized',
        }

        with self.assertRaises(billing.PaymentRequired):
            billing.verify_and_fulfill(
                self.employer, 'order_test123', 'pay_test123', self.checkout_signature())
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 0)
        self.assertFalse(Invoice.objects.exists())

    @patch('accounts.billing._gateway_request')
    def test_webhook_capture_is_idempotent(self, gateway_request):
        gateway_request.return_value = self.gateway_order
        billing.start_purchase(self.employer, 'credits')
        webhook = {
            'id': 'pay_webhook123',
            'order_id': 'order_test123',
            'amount': 999900,
            'currency': 'INR',
            'status': 'captured',
        }

        billing.process_webhook_payment(webhook)
        billing.process_webhook_payment(webhook)

        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 22)
        self.assertEqual(Invoice.objects.count(), 1)
        gateway_request.assert_called_once()


@override_settings(
    DEMO_PAYMENTS=False,
    RAZORPAY_KEY_ID='rzp_test_public',
    RAZORPAY_KEY_SECRET='test-secret',
    RAZORPAY_WEBHOOK_SECRET='webhook-secret',
)
class RazorpayPaymentViewTests(APITestCase):
    def setUp(self):
        self.employer = Employer.objects.create_user(username='checkout@example.test', password='Strong-pass-123')
        self.client.force_authenticate(self.employer)

    @patch('accounts.billing._gateway_request')
    def test_purchase_endpoint_requires_verified_capture_before_crediting(self, gateway_request):
        gateway_request.side_effect = [
            {'id': 'order_api123', 'amount': 999900, 'currency': 'INR', 'status': 'created'},
            {'id': 'pay_api123', 'order_id': 'order_api123', 'amount': 999900,
             'currency': 'INR', 'status': 'captured'},
        ]
        response = self.client.post('/api/billing/purchase/', {'pack': 'credits'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['order_id'], 'order_api123')
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 0)

        signature = hmac.new(
            b'test-secret', b'order_api123|pay_api123', hashlib.sha256).hexdigest()
        response = self.client.post('/api/billing/verify/', {
            'razorpay_order_id': 'order_api123',
            'razorpay_payment_id': 'pay_api123',
            'razorpay_signature': signature,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['job_credits'], 22)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_healthz_reports_database_status(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['database'], 'ok')

    def test_api_version_endpoint_is_available(self):
        response = self.client.get('/api/version')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['version'], 'v1')

    def test_webhook_rejects_invalid_signatures(self):
        body = json.dumps({'event': 'payment.captured'}).encode()
        response = self.client.post(
            '/api/billing/razorpay/webhook/',
            body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid',
        )
        self.assertEqual(response.status_code, 400)

    @patch('accounts.billing._gateway_request')
    def test_signed_captured_webhook_fulfills_order(self, gateway_request):
        gateway_request.return_value = {
            'id': 'order_hook123', 'amount': 999900, 'currency': 'INR', 'status': 'created'}
        self.client.post('/api/billing/purchase/', {'pack': 'credits'}, format='json')
        body = json.dumps({
            'event': 'payment.captured',
            'payload': {'payment': {'entity': {
                'id': 'pay_hook123',
                'order_id': 'order_hook123',
                'amount': 999900,
                'currency': 'INR',
                'status': 'captured',
            }}},
        }).encode()
        signature = hmac.new(b'webhook-secret', body, hashlib.sha256).hexdigest()

        response = self.client.post(
            '/api/billing/razorpay/webhook/',
            body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        self.employer.refresh_from_db()
        self.assertEqual(self.employer.job_credits, 22)
        self.assertEqual(Invoice.objects.count(), 1)
