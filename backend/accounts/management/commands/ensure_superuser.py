import os

from django.core.management.base import BaseCommand

from accounts.models import Employer


class Command(BaseCommand):
    help = 'Create an admin user from DJANGO_SUPERUSER_* env vars if it does not exist (idempotent).'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_USERNAME/PASSWORD not set - skipping admin creation.')
            return
        if Employer.objects.filter(username=username).exists():
            self.stdout.write(f'Admin "{username}" already exists.')
            return
        Employer.objects.create_superuser(
            username=username, password=password, email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''))
        self.stdout.write(self.style.SUCCESS(f'Created admin "{username}".'))
