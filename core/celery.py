import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('kutubxona')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'post-monthly-top-student-news': {
        'task': 'apps.schools.tasks.post_monthly_top_student_news',
        # Run on the 1st of every month at midnight
        'schedule': crontab(day_of_month='1', hour='0', minute='0'),
    },
}
