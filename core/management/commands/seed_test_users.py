from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from schools.models import District, School

User = get_user_model()

CREDENTIALS = []


def create_user(username, password, role, **kwargs):
    if User.objects.filter(username=username).exists():
        return
    user = User(username=username, role=role, **kwargs)
    user.set_password(password)
    user.save()
    CREDENTIALS.append((username, password, role, kwargs.get('school')))


class Command(BaseCommand):
    help = 'Creates test users for all roles'

    def handle(self, *args, **options):
        district, _ = District.objects.get_or_create(name='Test tuman')
        school, _ = School.objects.get_or_create(
            name='Test maktab',
            defaults={
                'address': 'Test address 1',
                'contact': '+998901234567',
                'district': district,
            },
        )

        create_user('admin', 'superadmin', 'superuser', is_superuser=True, is_staff=True)

        create_user('school_admin', 'admin123', 'school_admin', school=school)

        create_user('teacher', 'teacher123', 'teacher', school=school, subject='Matematika')

        create_user('student', 'student123', 'student', school=school, grade='5A')

        extra_students = [
            ('ali', 'student123', 'Ali', 'Karimov'),
            ('vali', 'student123', 'Vali', 'Aliyev'),
            ('dilorom', 'student123', 'Dilorom', 'Rahimova'),
        ]
        for username, pw, fn, ln in extra_students:
            create_user(username, pw, 'student', school=school, grade='5A', first_name=fn, last_name=ln)

        self.stdout.write(self.style.SUCCESS('Test users created successfully!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 50))
        self.stdout.write(self.style.WARNING('     TEST CREDENTIALS'))
        self.stdout.write(self.style.WARNING('=' * 50))
        for username, password, role, sch in CREDENTIALS:
            school_name = sch.name if sch else '-'
            self.stdout.write(f'  {role:15s} | {username:20s} | {password:15s} | {school_name}')
        self.stdout.write(self.style.WARNING('=' * 50))
