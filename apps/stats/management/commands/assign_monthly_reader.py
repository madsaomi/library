from accounts.models import CustomUser
from books.models import ReaderOfMonth
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone
from schools.models import News


class Command(BaseCommand):
    help = 'Assign Reader of the Month for each school and create news'

    def handle(self, *args, **options):
        now = timezone.now()
        month = now.month
        year = now.year
        month_names = {
            1: 'Yanvar',
            2: 'Fevral',
            3: 'Mart',
            4: 'Aprel',
            5: 'May',
            6: 'Iyun',
            7: 'Iyul',
            8: 'Avgust',
            9: 'Sentabr',
            10: 'Oktabr',
            11: 'Noyabr',
            12: 'Dekabr',
        }
        month_name = month_names.get(month, '')

        schools = CustomUser.objects.filter(role='student').values_list('school_id', flat=True).distinct()

        assigned = 0
        for school_id in schools:
            if not school_id:
                continue

            top_student = (
                CustomUser.objects.filter(school_id=school_id, role='student')
                .annotate(
                    month_books=Count(
                        'bookissue',
                        filter=Q(
                            bookissue__issued_at__year=year,
                            bookissue__issued_at__month=month,
                            bookissue__is_returned=True,
                        ),
                    )
                )
                .order_by('-month_books')
                .first()
            )

            if top_student and top_student.month_books > 0:
                ReaderOfMonth.objects.update_or_create(
                    school_id=school_id,
                    month=month,
                    year=year,
                    defaults={
                        'user': top_student,
                        'books_count': top_student.month_books,
                    },
                )

                News.objects.create(
                    school_id=school_id,
                    title=f'Oy kitobxoni — {month_name}!',
                    body='',
                    is_published=True,
                    template_key='top_reader',
                    template_data={
                        'username': top_student.username,
                        'grade': str(top_student.grade or ''),
                        'count': top_student.month_books,
                        'month': month_name,
                        'year': str(year),
                    },
                )
                assigned += 1

        self.stdout.write(self.style.SUCCESS(f'Reader of the Month assigned + news created for {assigned} schools'))
