import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Employer, Invoice


def _normalise_phone(value):
    digits = re.sub(r'[^\d]', '', (value or '').strip())
    if len(digits) == 10:
        return digits
    if len(digits) == 12 and digits.startswith('91'):
        return digits[2:]
    if len(digits) == 11 and digits.startswith('0'):
        return digits[1:]
    raise serializers.ValidationError('Enter a valid 10-digit mobile number.')


def normalise_identifier(value):
    """Phone number or work email, used (lower-cased) as the username."""
    value = (value or '').strip()
    if '@' in value:
        normalized = value.lower()
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', normalized):
            raise serializers.ValidationError('Enter a valid email address.')
        return normalized
    return _normalise_phone(value)


class EmployerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name', read_only=True)
    initial = serializers.SerializerMethodField()
    has_unlimited = serializers.BooleanField(read_only=True)

    class Meta:
        model = Employer
        fields = ['id', 'username', 'name', 'initial', 'company', 'phone', 'email',
                  'job_credits', 'db_credits', 'active_slots', 'unlimited_until', 'has_unlimited']
        read_only_fields = fields

    def get_initial(self, obj):
        return (obj.display_name[:1] or 'U').upper()


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_identifier(self, value):
        value = normalise_identifier(value)
        if Employer.objects.filter(username=value).exists():
            raise serializers.ValidationError('An account with this number/email already exists. Please sign in.')
        return value

    def validate(self, attrs):
        validate_password(attrs['password'])
        return attrs

    def create(self, validated):
        identifier = validated['identifier']
        parts = validated['name'].strip().split(None, 1)
        user = Employer(
            username=identifier,
            first_name=parts[0] if parts else '',
            last_name=parts[1] if len(parts) > 1 else '',
            company=validated.get('company', '').strip(),
        )
        if '@' in identifier:
            user.email = identifier
            user.username = identifier
        else:
            user.phone = identifier
            user.username = identifier
        user.set_password(validated['password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        try:
            username = normalise_identifier(attrs['identifier'])
        except serializers.ValidationError:
            raise serializers.ValidationError('Incorrect mobile/email or password.')
        user = authenticate(username=username, password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Incorrect mobile/email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account is disabled.')
        attrs['user'] = user
        return attrs


class RazorpayVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=128)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=300, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    class Meta:
        model = Employer
        fields = ['name', 'company', 'phone']

    def validate_phone(self, value):
        return _normalise_phone(value)

    def update(self, instance, validated):
        name = validated.pop('name', None)
        if name:
            parts = name.strip().split(None, 1)
            instance.first_name = parts[0]
            instance.last_name = parts[1] if len(parts) > 1 else ''
        for key, value in validated.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class InvoiceSerializer(serializers.ModelSerializer):
    is_demo = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'plan', 'amount', 'status', 'created_at', 'is_demo']

    def get_is_demo(self, obj):
        return obj.payment_order_id is None
