from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from schools.models import District, School
import random
import re

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates a test school with 1-11 grades, ~20-25 students per grade'

    def add_arguments(self, parser):
        parser.add_argument('--school-name', type=str, default='Test maktab')
        parser.add_argument('--district', type=str, default='Nukus')
        parser.add_argument('--students-per-grade', type=int, default=22)

    def handle(self, *args, **options):
        school_name = options['school_name']
        district_name = options['district']
        per_grade = options['students_per_grade']
        slug = re.sub(r'[^a-z0-9]+', '_', school_name.lower()).strip('_')

        district, _ = District.objects.get_or_create(name=district_name)
        school, created = School.objects.get_or_create(
            name=school_name,
            defaults={'address': 'Test manzil', 'contact': '+998901234567', 'district': district},
        )

        if not created:
            existing = User.objects.filter(school=school, role='student').count()
            if existing > 0:
                self.stdout.write(self.style.WARNING(
                    f'School "{school_name}" already has {existing} students. Skipping.'
                ))
                return

        self.stdout.write(f'Creating students for "{school_name}" ({per_grade} per grade)...')

        letters = ['A', 'B', 'V', 'G', 'D', 'E', 'F']
        names = [
            'Ali', 'Vali', 'Sardor', 'Jasur', 'Botir', 'Shohruh', 'Dilmurod',
            'Aziz', 'Bekzod', 'Farrux', 'Gulnora', 'Zilola', 'Nigora', 'Malika',
            'Sevara', 'Aziza', 'Dildora', 'Feruza', 'Kamola', 'Lola',
            'Rustam', 'Xurshid', 'Temur', 'Nodir', 'Olim', 'Husan', 'Anvar',
        ]
        surnames = [
            'Karimov', 'Aliyev', 'Rahimov', 'Yusupov', 'Hasanov', 'Shukurov',
            'Nazarov', 'Ruziyev', 'Toshmatov', 'Xolmatov', 'Murodov', 'Sultonov',
            'Ergashev', 'Komilov', 'Norov', 'Jumayev', 'Ochilov', 'Qodirov',
            'Raxmanov', 'Sobirov', 'Tursunov', 'Umarov', 'Xasanov', 'Ismailov',
        ]
        total_created = 0
        password = 'student123'

        for grade_num in range(1, 12):
            grade_letter = letters[(grade_num - 1) % len(letters)]
            grade = f'{grade_num}{grade_letter}'
            count = per_grade + random.randint(-2, 3)

            for i in range(count):
                first_name = random.choice(names)
                last_name = random.choice(surnames)
                birth_year = 2007 + (11 - grade_num)
                user = User(
                    username=f'{slug}_{grade_num}_{i+1}',
                    first_name=first_name,
                    last_name=last_name,
                    role='student',
                    school=school,
                    grade=grade,
                    birth_date=f'{birth_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
                )
                user.set_password(password)
                user.save()
                total_created += 1

            self.stdout.write(f'  Grade {grade}: {count} students')

        admin = User(
            username=f'{slug}_adm',
            first_name='Test',
            last_name='Admin',
            role='school_admin',
            school=school,
        )
        admin.set_password('admin123')
        admin.save()

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {total_created} students + 1 admin for "{school_name}".\n'
            f'  Admin login:  username={slug}_adm, password=admin123\n'
            f'  Student login: username={slug}_N_N, password=student123'
        ))
