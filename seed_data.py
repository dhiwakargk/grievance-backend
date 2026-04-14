import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User, Department

def seed():
    # Departments
    dept_names = ['Roads', 'Electricity', 'Water', 'Police', 'Health']
    depts = []
    for name in dept_names:
        d, created = Department.objects.get_or_create(name=name)
        depts.append(d)
        print(f"Department {name}: {created}")

    # Users
    users = [
        ('admin', 'admin@example.com', 'adminpass', 'admin', None),
        ('citizen1', 'citizen1@example.com', 'pass123', 'citizen', None),
        ('official1', 'official1@example.com', 'pass123', 'official', depts[0]), # Roads Official
    ]

    for username, email, password, role, dept in users:
        if not User.objects.filter(username=username).exists():
            u = User.objects.create_user(username=username, email=email, password=password)
            u.role = role
            if dept:
                u.department = dept
            u.is_staff = (role == 'admin')
            u.is_superuser = (role == 'admin')
            u.save()
            print(f"Created {role}: {username}")
        else:
            print(f"User {username} exists")

if __name__ == '__main__':
    seed()
