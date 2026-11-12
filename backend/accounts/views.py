import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import billing
from .models import Employer
from .serializers import (EmployerSerializer, InvoiceSerializer, LoginSerializer,
                          ProfileUpdateSerializer, RazorpayVerifySerializer, RegisterSerializer)


def token_response(user, http_status=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': EmployerSerializer(user).data}, status=http_status)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return token_response(serializer.save(), status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return token_response(serializer.validated_data['user'])


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(EmployerSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EmployerSerializer(request.user).data)


class InvoiceListView(ListAPIView):
    serializer_class = InvoiceSerializer
    pagination_class = None

    def get_queryset(self):
        return self.request.user.invoices.all()


class PurchaseView(APIView):
    """Create a checkout order, or grant demo entitlements when explicitly enabled."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payment'

    def post(self, request):
        pack = request.data.get('pack')
        result = billing.start_purchase(request.user, pack)
        if result['demo']:
            return Response({
                'demo': True,
                'message': result['message'],
                'invoice': InvoiceSerializer(result['invoice']).data,
                'user': EmployerSerializer(result['user']).data,
            }, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payment'

    def post(self, request):
        serializer = RazorpayVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invoice, employer = billing.verify_and_fulfill(
            request.user,
            data['razorpay_order_id'],
            data['razorpay_payment_id'],
            data['razorpay_signature'],
        )
        return Response({
            'message': 'Payment verified and plan activated.',
            'invoice': InvoiceSerializer(invoice).data,
            'user': EmployerSerializer(employer).data,
        })


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get('X-Razorpay-Signature', '')
        billing.verify_webhook_signature(request.body, signature)
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({'detail': 'Invalid webhook payload.'}, status=status.HTTP_400_BAD_REQUEST)
        if payload.get('event') == 'payment.captured':
            payment = payload.get('payload', {}).get('payment', {}).get('entity')
            if not isinstance(payment, dict):
                return Response({'detail': 'Webhook payment details are missing.'}, status=status.HTTP_400_BAD_REQUEST)
            billing.process_webhook_payment(payment)
        return Response({'status': 'ok'})
