from django.core.management.base import BaseCommand

from jobs.models import Candidate

CANDIDATES = [
    ('Ramesh Gowda', 'Delivery Executive', 'Bengaluru', 'Koramangala', '2 years', '₹18,000/mo', ['Driving', 'Navigation', 'Customer Service'], '9876543210'),
    ('Priya Sharma', 'Telecaller', 'Bengaluru', 'Whitefield', '1 year', '₹15,000/mo', ['Communication', 'Hindi', 'English', 'CRM'], '9876543211'),
    ('Mohammed Irfan', 'Security Guard', 'Bengaluru', 'Electronic City', '5 years', '₹20,000/mo', ['Security', 'First Aid', 'CCTV Monitoring'], '9876543212'),
    ('Anjali Verma', 'Retail Sales', 'Bengaluru', 'Indiranagar', 'Fresher', '₹12,000/mo', ['Sales', 'Kannada', 'Hindi', 'English'], '9876543213'),
    ('Suresh Kumar', 'Driver', 'Bengaluru', 'Hebbal', '7 years', '₹24,000/mo', ['Driving', 'Light Motor Vehicle', 'Kannada', 'Hindi'], '9876543214'),
    ('Lakshmi Devi', 'Warehouse Associate', 'Bengaluru', 'Peenya', '3 years', '₹16,000/mo', ['Packing', 'Inventory', 'Kannada'], '9876543215'),
    ('Arjun Reddy', 'Field Sales Executive', 'Hyderabad', 'Madhapur', '4 years', '₹22,000/mo', ['Field Sales', 'Telugu', 'English', 'Lead Generation'], '9876543216'),
    ('Fathima Banu', 'Telecaller', 'Chennai', 'T Nagar', '2 years', '₹14,000/mo', ['Tamil', 'English', 'Customer Support'], '9876543217'),
]


class Command(BaseCommand):
    help = 'Load sample candidates for the Database tab (idempotent, matched by phone).'

    def handle(self, *args, **options):
        created = 0
        for name, role, city, area, exp, salary, skills, phone in CANDIDATES:
            _, was_created = Candidate.objects.update_or_create(
                phone=phone,
                defaults={
                    'name': name, 'role': role, 'city': city, 'area': area,
                    'experience': exp, 'expected_salary': salary, 'skills': skills,
                    'available_in_database': True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f'Candidates: {created} added, {len(CANDIDATES) - created} already present.')
