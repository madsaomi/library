from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import F
from accounts.models import CustomUser
from frontend_school.models import GradePromotionLog

class Command(BaseCommand):
    help = 'Avtomatik sinf o\'tkazish (1-sentabrdan boshlab)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Yilni tekshirmasdan majburiy o\'tkazish')

    def handle(self, *args, **options):
        today = timezone.now().date()
        current_year = today.year

        if not options['force']:
            if today < date(current_year, 9, 1):
                self.stdout.write(self.style.WARNING(
                    f"Bugun {today}, sinf o'tkazish faqat 1-sentabrdan boshlanadi. Bekor qilindi."
                ))
                return

            if GradePromotionLog.objects.filter(year=current_year).exists():
                self.stdout.write(self.style.WARNING(
                    f"{current_year}-yil uchun sinf o'tkazish allaqachon amalga oshirilgan. Bekor qilindi."
                ))
                return

        students = CustomUser.objects.filter(role='student', is_archived=False)
        promoted = 0
        archived = 0
        skipped = 0

        for student in students:
            if not student.grade:
                skipped += 1
                continue
            parts = student.grade.strip().split('-')
            try:
                num = int(parts[0])
            except (ValueError, IndexError):
                skipped += 1
                continue
            num += 1
            if num > 11:
                student.is_archived = True
                student.grade = f"{num-1}-{parts[1]}" if len(parts) > 1 else str(num-1)
                archived += 1
            else:
                suffix = f"-{parts[1]}" if len(parts) > 1 else ""
                student.grade = f"{num}{suffix}"
                promoted += 1
            student.save()

        GradePromotionLog.objects.create(year=current_year)

        self.stdout.write(self.style.SUCCESS(
            f"O'tkazildi: {promoted} ta o'quvchi keyingi sinfga, "
            f"{archived} ta bitiruvchi arxivlandi. "
            f"Tashlab ketildi (sinf ko'rsatilmagan): {skipped}"
        ))
