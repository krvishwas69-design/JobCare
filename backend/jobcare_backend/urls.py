from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok', 'database': 'ok', 'service': 'jobcare'})
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'unavailable', 'service': 'jobcare'}, status=503)


def api_version(request):
    return JsonResponse({'version': 'v1', 'status': 'ok'})


admin_prefix = settings.ADMIN_URL.strip('/') if hasattr(settings, 'ADMIN_URL') else 'admin'

urlpatterns = [
    path(f'{admin_prefix}/', admin.site.urls),
    path('healthz', health),
    path('api/version', api_version),
    path('api/', include('accounts.urls')),
    path('api/', include('jobs.urls')),
]