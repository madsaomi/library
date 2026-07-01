from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
from accounts.models import CustomUser
from books.models import BookIssue, ReaderOfMonth


class Command(BaseCommand):
    help = "Assign Reader of the Month for each school"

    def handle(self, *args, **options):
        now = timezone.now()
        month = now.month
        year = now.year

        schools = CustomUser.objects.filter(role='student').values_list('school_id', flat=True).distinct()

        assigned = 0
        for school_id in schools:
            if not school_id:
                continue

            top_student = CustomUser.objects.filter(
                school_id=school_id, role='student'
            ).annotate(
                month_books=Count('bookissue', filter=Q(
                    bookissue__issued_at__year=year,
                    bookissue__issued_at__month=month,
                    bookissue__is_returned=True
                ))
            ).order_by('-month_books').first()

            if top_student and top_student.month_books > 0:
                ReaderOfMonth.objects.update_or_create(
                    school_id=school_id,
                    month=month,
                    year=year,
                    defaults={
                        'user': top_student,
                        'books_count': top_student.month_books,
                    }
                )
                assigned += 1

        self.stdout.write(self.style.SUCCESS(f"Reader of the Month assigned for {assigned} schools"))
