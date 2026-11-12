from django.db import transaction
from django.db.models import Count, Q, TextField
from django.db.models.functions import Cast
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.billing import PaymentRequired
from accounts.models import Employer
from accounts.serializers import EmployerSerializer

from .models import Application, Candidate, CandidateUnlock, Job
from .serializers import (ApplicationSerializer, ApplySerializer, CandidateSerializer,
                          JobSerializer, PublicJobSerializer)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    pagination_class = None

    def get_queryset(self):
        qs = (Job.objects.filter(posted_by=self.request.user)
              .select_related('posted_by').annotate(applicants_count=Count('applications')))
        job_status = self.request.query_params.get('status')
        if job_status in (Job.DRAFT, Job.ACTIVE, Job.CLOSED):
            qs = qs.filter(status=job_status)
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(category__icontains=q))
        return qs

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Publish a draft/closed job using a credit or an already-active unlimited plan."""
        plan = request.data.get('plan', 'credit')
        if plan not in ('credit', 'unlimited'):
            return Response({'detail': 'Unknown plan.'}, status=status.HTTP_400_BAD_REQUEST)
        self.get_object()  # 404 if the job is not the caller's
        with transaction.atomic():
            employer = Employer.objects.select_for_update().get(pk=request.user.pk)
            job = Job.objects.select_for_update().select_related('posted_by').get(pk=pk, posted_by=employer)
            if job.status == Job.ACTIVE:
                return Response({'detail': 'This job is already active.'}, status=status.HTTP_400_BAD_REQUEST)
            if employer.has_unlimited:
                used = 'unlimited'
            elif plan == 'credit':
                if employer.job_credits < 1:
                    raise PaymentRequired({'detail': 'You have no job credits left. Buy a credit pack or pick a plan.',
                                           'code': 'no_credits'})
                employer.job_credits -= 1
                employer.save(update_fields=['job_credits'])
                used = 'credit'
            elif plan == 'unlimited':
                raise PaymentRequired({'detail': 'Buy the unlimited plan before activating this job.',
                                       'code': 'plan_required'})
            else:
                raise PaymentRequired({'detail': 'This hiring plan is not available yet.',
                                       'code': 'plan_unavailable'})
            job.status = Job.ACTIVE
            job.plan = used
            job.activated_at = timezone.now()
            job.save()
        return Response({'job': JobSerializer(job).data, 'user': EmployerSerializer(employer).data})

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        job = self.get_object()
        job = Job.objects.get(pk=job.pk)
        job.status = Job.CLOSED
        job.save(update_fields=['status', 'updated_at'])
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        src = Job.objects.get(pk=self.get_object().pk)
        copy = Job.objects.create(
            posted_by=request.user, title=f'{src.title} (Copy)'[:300], category=src.category,
            job_type=src.job_type, location=src.location, min_salary=src.min_salary,
            max_salary=src.max_salary, openings=src.openings, description=src.description)
        return Response(JobSerializer(copy).data, status=status.HTTP_201_CREATED)


class CandidateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CandidateSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Candidate.objects.filter(available_in_database=True).annotate(skills_text=Cast('skills', TextField()))
        for word in self.request.query_params.get('q', '').split()[:6]:
            qs = qs.filter(Q(name__icontains=word) | Q(role__icontains=word) | Q(city__icontains=word)
                           | Q(area__icontains=word) | Q(skills_text__icontains=word))
        return qs.order_by('name')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        user = self.request.user
        ctx['unlocked_ids'] = set(CandidateUnlock.objects.filter(employer=user).values_list('candidate_id', flat=True))
        return ctx

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Spend 1 database credit to reveal the phone number (free if already unlocked)."""
        candidate = self.get_object()
        with transaction.atomic():
            employer = Employer.objects.select_for_update().get(pk=request.user.pk)
            if not CandidateUnlock.objects.filter(employer=employer, candidate=candidate).exists():
                if employer.db_credits < 1:
                    raise PaymentRequired({'detail': 'You have no database credits left.', 'code': 'no_credits'})
                employer.db_credits -= 1
                employer.save(update_fields=['db_credits'])
                CandidateUnlock.objects.create(employer=employer, candidate=candidate)
        data = CandidateSerializer(candidate, context={'unlocked_ids': {candidate.pk}}).data
        return Response({'candidate': data, 'user': EmployerSerializer(employer).data})


class ApplicationViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Applications received on the caller's jobs; the status can be changed (PATCH)."""
    serializer_class = ApplicationSerializer
    pagination_class = None
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = (Application.objects.filter(job__posted_by=self.request.user)
              .select_related('job', 'candidate'))
        job_id = self.request.query_params.get('job')
        return qs.filter(job_id=job_id) if job_id and job_id.isdigit() else qs


class ReportView(APIView):
    def get(self, request):
        jobs = Job.objects.filter(posted_by=request.user).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status=Job.ACTIVE)),
            draft=Count('id', filter=Q(status=Job.DRAFT)),
            closed=Count('id', filter=Q(status=Job.CLOSED)),
        )
        apps = Application.objects.filter(job__posted_by=request.user)
        return Response({
            'jobs': jobs,
            'applications': apps.count(),
            'shortlisted': apps.filter(status__in=[Application.SHORTLISTED, Application.INTERVIEWED, Application.HIRED]).count(),
            'hired': apps.filter(status=Application.HIRED).count(),
            'contacted': CandidateUnlock.objects.filter(employer=request.user).count(),
        })


# ---- Public endpoints (for the job-seeker app; no login) -----------------------------------
class PublicJobListView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicJobSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Job.objects.filter(status=Job.ACTIVE).select_related('posted_by')
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(category__icontains=q))
        return qs[:100]


class PublicApplyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'apply'

    def post(self, request, pk):
        try:
            job = Job.objects.get(pk=pk, status=Job.ACTIVE)
        except Job.DoesNotExist:
            return Response({'detail': 'This job is not accepting applications.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        phone = data.pop('phone')
        data.pop('consent')
        candidate, _ = Candidate.objects.get_or_create(phone=phone, defaults=data)
        _, created = Application.objects.get_or_create(
            job=job, candidate=candidate,
            defaults={'consent_at': timezone.now(), 'consent_version': 'job-application-v1'})
        return Response({'detail': 'Application submitted.' if created else 'You already applied to this job.'},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
