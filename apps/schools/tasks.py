from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import CustomUser
from apps.schools.models import News, School


@shared_task
def post_monthly_top_student_news():
    """
    Finds the top student based on xp_points in each school and posts a news article.
    Runs periodically via Celery beat.
    """
    today = timezone.localdate()
    schools = School.objects.all()

    for school in schools:
        # Get the top student for the school
        top_student = (
            CustomUser.objects.filter(school=school, role='student', is_active=True, is_archived=False)
            .order_by('-xp_points', '-total_books_read')
            .first()
        )

        if top_student:
            title = _("Eng faol o'quvchi: {name}").format(name=f'{top_student.first_name} {top_student.last_name}')

            # Check if this exact news already exists this month
            existing = News.objects.filter(
                school=school,
                title=title,
                created_at__year=today.year,
                created_at__month=today.month,
            ).exists()

            if not existing:
                News.objects.create(
                    school=school,
                    title=title,
                    body='',
                    is_published=True,
                    template_key='top_reader',
                    template_data={
                        'student': {
                            'name': f'{top_student.first_name} {top_student.last_name}',
                            'grade': top_student.grade or '—',
                            'school': school.name,
                        },
                        'books': top_student.total_books_read,
                        'xp': top_student.xp_points,
                        'level': top_student.level,
                        'streak': top_student.current_streak,
                    },
                )
