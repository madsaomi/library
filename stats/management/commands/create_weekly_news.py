from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from schools.models import School
from accounts.models import CustomUser
from frontend_school.models import News

class Command(BaseCommand):
    help = "Create a news item with weekly active schools and top readers"

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help="Period in days (default: 7)")

    def handle(self, *args, **options):
        days = options['days']
        today = timezone.now().date()
        period_start = today - timedelta(days=days)

        top_schools = School.objects.annotate(
            active_count=Count(
                'customuser__bookissue',
                filter=Q(
                    customuser__bookissue__issued_at__date__gte=period_start,
                    customuser__role='student'
                )
            )
        ).filter(active_count__gt=0).order_by('-active_count')[:5]

        top_readers = CustomUser.objects.filter(
            role='student',
            bookissue__issued_at__date__gte=period_start
        ).annotate(
            books_read=Count('bookissue')
        ).order_by('-books_read')[:10]

        if not top_schools and not top_readers:
            self.stdout.write("No data to create news from.")
            return

        schools_data = []
        for s in top_schools:
            schools_data.append({'name': s.name, 'count': s.active_count})

        readers_data = []
        for r in top_readers:
            readers_data.append({'username': r.username, 'grade': r.grade, 'count': r.books_read})

        News.objects.create(
            school=None,
            title=f"So'nggi {days} kun ichidagi faol maktablar va kitobxonlar",
            body="",
            is_published=True,
            template_key='weekly_active',
            template_data={
                'schools': schools_data,
                'readers': readers_data,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"Weekly news created: {len(top_schools)} schools, {len(top_readers)} readers"
        ))
