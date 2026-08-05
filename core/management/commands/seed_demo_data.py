import random
from datetime import timedelta

from books.models import Book, BookIssue, Category
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from schools.models import News, School

User = get_user_model()

CATEGORIES = [
    ('Badiiy adabiyot', 'fa-book'),
    ('Ilmiy adabiyot', 'fa-flask'),
    ('Darsliklar', 'fa-book-open'),
    ("Bolalar adabiyoti", 'fa-child'),
    ('Tarix', 'fa-landmark'),
    ("Chet tili", 'fa-language'),
    ('Lug\'atlar', 'fa-spell-check'),
]

BOOKS = [
    ('O\'tkan kunlar', 'Abdulla Qodiriy', 'Badiiy adabiyot', 5),
    ('Mehrobdan chayon', 'Abdulla Qodiriy', 'Badiiy adabiyot', 3),
    ('Sarob', 'Abdulla Qahhor', 'Badiiy adabiyot', 4),
    ('Anor', 'Said Ahmad', 'Badiiy adabiyot', 3),
    ('Ufq', 'Said Ahmad', 'Badiiy adabiyot', 2),
    ('Ikki eshik orasi', 'O\'tkir Hoshimov', 'Badiiy adabiyot', 4),
    ('Dunyoning ishlari', 'O\'tkir Hoshimov', 'Badiiy adabiyot', 3),
    ('Bahor qaytmaydi', 'O\'tkir Hoshimov', 'Badiiy adabiyot', 3),
    ('Shum bola', 'G\'afur G\'ulom', 'Badiiy adabiyot', 6),
    ('Yodgor', 'G\'afur G\'ulom', 'Badiiy adabiyot', 3),
    ('G\'urur', 'Hakim Nazir', 'Badiiy adabiyot', 2),
    ('Ufq sari', 'Pirimqul Qodirov', 'Badiiy adabiyot', 2),
    ('Alpomish', 'Xalq dostoni', 'Badiiy adabiyot', 3),
    ('Bobur', 'Pirimqul Qodirov', 'Tarix', 2),
    ('Temur tuzuklari', 'Amir Temur', 'Tarix', 3),
    ('Ulug\'bek xazinasi', 'Odil Yoqubov', 'Tarix', 2),
    ('O\'zbekiston tarixi', 'R. Nabiyev', 'Tarix', 4),
    ('Fizika 7-sinf', 'P. Habibullayev', 'Darsliklar', 8),
    ('Algebra 8-sinf', 'Sh. Alimov', 'Darsliklar', 8),
    ('Ona tili 5-sinf', 'Q. Qozogov', 'Darsliklar', 8),
    ('Matematika 6-sinf', 'N. Abduraxmonova', 'Darsliklar', 8),
    ('Ingliz tili 7-sinf', 'O. Hoshimov', 'Darsliklar', 6),
    ('Biologiya 9-sinf', 'A. Gafurov', 'Darsliklar', 6),
    ('Kimyo 8-sinf', 'G. Raximov', 'Darsliklar', 6),
    ('Geografiya 7-sinf', 'A. Karimov', 'Darsliklar', 6),
    ('Tabiat haqida 100 ta fakt', 'M. Saidova', 'Bolalar adabiyoti', 3),
    ('Ertaklar to\'plami', 'Xalq ertaklari', 'Bolalar adabiyoti', 5),
    ('Bolalar ensiklopediyasi', 'O. Karimov', 'Bolalar adabiyoti', 2),
    ('Kichik astronomiya', 'N. Islomov', 'Ilmiy adabiyot', 2),
    ('Fizika olamiga sayohat', 'D. Sultonov', 'Ilmiy adabiyot', 2),
    ('Inglizcha-zbekcha lug\'at', 'J. Musayev', 'Lug\'atlar', 4),
    ('Ruscha-zbekcha lug\'at', 'B. Yusupov', 'Lug\'atlar', 3),
]

TEXTBOOKS = [
    ('Matematika 5-sinf', 'N. Abduraxmonova', 5),
    ('Ona tili 6-sinf', 'Q. Qozogov', 6),
    ('Fizika 8-sinf', 'P. Habibullayev', 8),
    ('Kimyo 9-sinf', 'G. Raximov', 9),
    ('Ingliz tili 6-sinf', 'O. Hoshimov', 6),
]

NEWS = [
    (
        'Kutubxonaga yangi kitoblar keldi!',
        'Yangi o\'quv yilida kutubxona fondi 50 dan ortiq yangi kitoblar bilan to\'ldirildi. Barchani kutubxonaga taklif qilamiz!',
    ),
    (
        'Eng faol kitobxonlar taqdirlandi',
        'O\'tgan hafta yakuniga ko\'ra eng faol kitobxonlar maxsus sovg\'alar bilan taqdirlandi. Davom eting!',
    ),
    (
        'Kutubxona soatlari yangilandi',
        'Diqqat! Kutubxona ish vaqti o\'zgartirildi: dushanba-juma 8:00 dan 18:00 gacha, shanba 9:00 dan 14:00 gacha.',
    ),
]


class Command(BaseCommand):
    help = 'Seeds demo books, categories, textbook loans, issues and news for a school'

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, help='School ID to seed into (default: first school)')
        parser.add_argument('--force', action='store_true', help='Create books even if the school already has books')

    def handle(self, *args, **options):
        if options['school_id']:
            school = School.objects.filter(pk=options['school_id']).first()
            if not school:
                raise CommandError(f'School with id {options["school_id"]} not found')
        else:
            school = School.objects.order_by('id').first()
            if not school:
                raise CommandError('No schools exist. Run seed_test_users or seed_test_school first.')

        existing_books = Book.objects.filter(school=school).count()
        if existing_books and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'School "{school.name}" already has {existing_books} books. '
                    'Use --force to add demo books anyway.'
                )
            )
            return

        self.stdout.write(f'Seeding demo data for school "{school.name}"...')

        # Categories
        cat_map = {}
        for name, _icon in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name)
            cat_map[name] = cat

        # Regular books
        book_count = 0
        descriptions = {
            'Badiiy adabiyot': 'O\'zbek va jahon adabiyoti durdonalari. Maktab o\'quvchilari uchun tavsiya etiladigan badiiy asarlar.',
            'Ilmiy adabiyot': 'Fan va texnika sohasidagi ilmiy-ommabop adabiyotlar.',
            'Darsliklar': 'Maktab darsliklari, barcha sinflar uchun.',
            'Bolalar adabiyoti': 'Yosh o\'quvchilar uchun ertaklar va bolalar ensiklopediyalari.',
            'Tarix': 'Tarixiy asarlar va buyuk ajdodlar haqida kitoblar.',
            'Chet tili': 'Ingliz, rus va boshqa xorijiy tillarni o\'rganish uchun materiallar.',
            'Lug\'atlar': 'Tilli va ikki tilli lug\'atlar.',
        }
        for title, author, category, copies in BOOKS:
            book, created = Book.objects.get_or_create(
                school=school,
                title=title,
                author=author,
                defaults={
                    'description': descriptions.get(category, ''),
                    'category': cat_map[category],
                    'total_count': copies,
                    'available_count': copies,
                    'is_textbook': False,
                },
            )
            if created:
                book_count += 1

        # Textbooks (issued to students for the year)
        textbook_count = 0
        for title, author, grade in TEXTBOOKS:
            book, created = Book.objects.get_or_create(
                school=school,
                title=title,
                author=author,
                defaults={
                    'description': f'{grade}-sinf uchun darslik.',
                    'category': cat_map['Darsliklar'],
                    'total_count': 10,
                    'available_count': 2,
                    'is_textbook': True,
                    'subject': title.split(' ')[0],
                    'grade': grade,
                },
            )
            if created:
                textbook_count += 1

        self.stdout.write(f'  Created {book_count} regular books, {textbook_count} textbooks')

        # Book issues for students
        students = list(User.objects.filter(school=school, role='student'))
        issued = 0
        if students:
            books = list(Book.objects.filter(school=school, is_textbook=False))
            for i, book in enumerate(books[:12]):
                if not students:
                    break
                student = students[i % len(students)]
                issued_dt = timezone.now() - timedelta(days=random.randint(1, 40))
                is_returned = i % 3 == 0
                returned_dt = issued_dt + timedelta(days=random.randint(5, 20)) if is_returned else None
                _, created = BookIssue.objects.get_or_create(
                    book=book,
                    user=student,
                    defaults={
                        'issued_at': issued_dt,
                        'returned_at': returned_dt,
                        'is_returned': is_returned,
                    },
                )
                if created:
                    issued += 1

        self.stdout.write(f'  Created {issued} book issues')

        # News
        news_count = 0
        for title, body in NEWS:
            _, created = News.objects.get_or_create(
                school=school,
                title=title,
                defaults={'body': body, 'is_published': True},
            )
            if created:
                news_count += 1

        self.stdout.write(f'  Created {news_count} news')

        self.stdout.write(
            self.style.SUCCESS(
                f'Done! School "{school.name}" now has:\n'
                f'  Categories: {Category.objects.count()}\n'
                f'  Books: {Book.objects.filter(school=school).count()}\n'
                f'  Issues: {BookIssue.objects.filter(book__school=school).count()}\n'
                f'  News: {News.objects.filter(school=school).count()}'
            )
        )
