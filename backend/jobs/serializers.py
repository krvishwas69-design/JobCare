import re

from rest_framework import serializers

from .models import Application, Candidate, Job


class JobSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.CharField(source='posted_by.display_name', read_only=True)
    applicants = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ['id', 'title', 'category', 'job_type', 'location', 'min_salary', 'max_salary', 'openings',
                  'description', 'status', 'plan', 'activated_at', 'posted_by_name', 'applicants',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'plan', 'activated_at', 'posted_by_name', 'applicants',
                            'created_at', 'updated_at']

    def get_applicants(self, obj):
        count = getattr(obj, 'applicants_count', None)
        return count if count is not None else obj.applications.count()

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Job title is required.')
        return value

    def validate_openings(self, value):
        if value < 1:
            raise serializers.ValidationError('Openings must be at least 1.')
        return value

    def validate(self, attrs):
        low = attrs.get('min_salary', getattr(self.instance, 'min_salary', 0))
        high = attrs.get('max_salary', getattr(self.instance, 'max_salary', 0))
        if high and low > high:
            raise serializers.ValidationError('Minimum pay cannot be higher than maximum pay.')
        return attrs


class PublicJobSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source='posted_by.company', read_only=True)

    class Meta:
        model = Job
        fields = ['id', 'title', 'category', 'job_type', 'location', 'min_salary', 'max_salary', 'openings',
                  'description', 'company', 'created_at']


class CandidateSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = ['id', 'name', 'role', 'city', 'area', 'experience', 'expected_salary', 'skills',
                  'phone', 'unlocked']

    def _unlocked(self, obj):
        return obj.pk in self.context.get('unlocked_ids', ())

    def get_unlocked(self, obj):
        return self._unlocked(obj)

    def get_phone(self, obj):
        if self._unlocked(obj):
            return obj.phone
        p = obj.phone
        return p[:2] + 'X' * max(len(p) - 4, 0) + p[-2:] if len(p) > 4 else 'XXXX'


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_role = serializers.CharField(source='candidate.role', read_only=True)
    candidate_phone = serializers.CharField(source='candidate.phone', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'job', 'job_title', 'candidate', 'candidate_name', 'candidate_role',
                  'candidate_phone', 'status', 'applied_at']
        read_only_fields = ['id', 'job', 'job_title', 'candidate', 'candidate_name', 'candidate_role', 'applied_at']


class ApplySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)
    consent = serializers.BooleanField(write_only=True)
    website = serializers.CharField(max_length=200, required=False, allow_blank=True, write_only=True)
    role = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)
    experience = serializers.CharField(max_length=50, required=False, allow_blank=True)
    expected_salary = serializers.CharField(max_length=50, required=False, allow_blank=True)
    skills = serializers.ListField(child=serializers.CharField(max_length=50), required=False, max_length=20)

    def validate_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('Please provide a valid name.')
        return cleaned

    def validate_phone(self, value):
        digits = re.sub(r'[^\d]', '', value or '')
        if len(digits) == 10:
            return digits
        if len(digits) == 12 and digits.startswith('91'):
            return digits[2:]
        if len(digits) == 11 and digits.startswith('0'):
            return digits[1:]
        raise serializers.ValidationError('Enter a valid mobile number.')

    def validate_website(self, value):
        if value and value.strip():
            raise serializers.ValidationError('Invalid submission.')
        return value

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError('Consent is required to submit an application.')
        return value

    def validate(self, attrs):
        phone = attrs.get('phone', '')
        if phone and phone == '0000000000':
            raise serializers.ValidationError({'phone': 'Enter a valid mobile number.'})

        for field_name in ('role', 'city', 'area', 'experience', 'expected_salary'):
            value = attrs.get(field_name)
            if value is not None:
                attrs[field_name] = value.strip()

        skills = attrs.get('skills')
        if skills is not None:
            cleaned = [str(skill).strip() for skill in skills if str(skill).strip()]
            if len(cleaned) != len(skills):
                attrs['skills'] = cleaned
            if len(cleaned) > 20:
                raise serializers.ValidationError('Too many skills provided.')
            attrs['skills'] = cleaned

        name = attrs.get('name', '')
        if len(name) > 200:
            raise serializers.ValidationError({'name': 'Name is too long.'})

        return attrs
