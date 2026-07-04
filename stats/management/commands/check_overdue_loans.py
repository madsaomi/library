from django.core.management.base import BaseCommand
from django.utils import timezone
from books.models import TextbookLoan, BookIssue
from datetime import timedelta

class Command(BaseCommand):
    help = "Check overdue loans and notify users + school admins"

    def handle(self, *args, **options):
        today = timezone.now().date()

        # Textbook loans past due
        overdue_textbooks = TextbookLoan.objects.filter(
            returned_at__isnull=True,
            due_date__lt=today
        )
        tb_notified = 0
        for loan in overdue_textbooks:
            days = (today - loan.due_date).days
            if days in (1, 3, 7, 14, 30):
                try:
                    from notifications.utils import notify_user
                    notify_user(
                        loan.student,
                        "Darslik muddati o'tdi!",
                        f"'{loan.book.title}' darsligini qaytarish muddati {days} kun oldin tugagan. Iltimos, kutubxonaga topshiring.",
                        url="/"
                    )
                    school_admin = loan.student.school.customuser_set.filter(role='school_admin').first()
                    if school_admin:
                        notify_user(
                            school_admin,
                            "O'quvchi darslikni qaytarmadi",
                            f"{loan.student.get_full_name()} ({loan.student.grade}-sinf) — '{loan.book.title}' darsligini {days} kundan beri qaytarmadi.",
                            url="/school/textbook-loans/"
                        )
                    tb_notified += 1
                except Exception as e:
                    self.stderr.write(f"Error notifying for textbook loan {loan.id}: {e}")

        # Book issues past due (no due_date field on BookIssue, but we can check loans > 30 days)
        cutoff = today - timedelta(days=30)
        overdue_books = BookIssue.objects.filter(
            is_returned=False,
            issued_at__date__lt=cutoff
        )
        bk_notified = 0
        for issue in overdue_books:
            days = (today - issue.issued_at.date()).days
            try:
                from notifications.utils import notify_user
                notify_user(
                    issue.user,
                    "Kitobni qaytarish muddati o'tdi!",
                    f"'{issue.book.title}' kitobini {days} kun oldin olgansiz. Iltimos, qaytarib topshiring.",
                    url="/user/my-books/"
                )
                bk_notified += 1
            except Exception as e:
                self.stderr.write(f"Error notifying for book issue {issue.id}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Overdue checks done: {tb_notified} textbook notices, {bk_notified} book notices sent"
        ))
