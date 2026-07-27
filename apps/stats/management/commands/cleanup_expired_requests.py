from datetime import timedelta

from books.models import BookRequest
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Auto-cancel pending book requests older than 30 days'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Days after which a pending request expires')

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)

        expired = BookRequest.objects.filter(status='pending', requested_at__lt=cutoff)

        count = expired.count()
        if not count:
            self.stdout.write('No expired requests found.')
            return

        for req in expired:
            req.status = 'rejected'
            req.save(update_fields=['status'])

        self.stdout.write(self.style.SUCCESS(f'Cancelled {count} expired pending request(s) older than {days} days'))
