from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('jobs', views.JobViewSet, basename='job')
router.register('candidates', views.CandidateViewSet, basename='candidate')
router.register('applications', views.ApplicationViewSet, basename='application')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/', views.ReportView.as_view()),
    path('public/jobs/', views.PublicJobListView.as_view()),
    path('public/jobs/<int:pk>/apply/', views.PublicApplyView.as_view()),
]
