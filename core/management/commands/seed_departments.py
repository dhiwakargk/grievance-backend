from django.core.management.base import BaseCommand
from core.models import Department

class Command(BaseCommand):
    help = 'Seeds initial departments'

    def handle(self, *args, **kwargs):
        departments = [
            'Roads',
            'Water',
            'Electricity',
            'Police',
            'Health',
            'Sanitation',
            'General'
        ]

        for dept_name in departments:
            dept, created = Department.objects.get_or_create(name=dept_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created department: {dept_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Department already exists: {dept_name}'))
