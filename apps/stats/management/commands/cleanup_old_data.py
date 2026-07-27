from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification
from stats.models import ActionLog


class Command(BaseCommand):
    help = 'Clean up old ActionLog entries, read notifications, and expired sessions'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options.get('dry_run', False)

        # ActionLogs older than 1 year
        log_cutoff = now - timedelta(days=365)
        old_logs = ActionLog.objects.filter(created_at__lt=log_cutoff)
        log_count = old_logs.count()

        # Read notifications older than 90 days
        notif_cutoff = now - timedelta(days=90)
        old_notifs = Notification.objects.filter(is_read=True, created_at__lt=notif_cutoff)
        notif_count = old_notifs.count()

        # Expired sessions older than 30 days
        session_cutoff = now - timedelta(days=30)
        old_sessions = Session.objects.filter(expire_date__lt=session_cutoff)
        session_count = old_sessions.count()

        if not (log_count or notif_count or session_count):
            self.stdout.write('Nothing to clean up.')
            return

        if dry_run:
            self.stdout.write(
                f'Would delete: {log_count} log entries, {notif_count} notifications, {session_count} sessions'
            )
            return

        deleted_logs, _ = old_logs.delete()
        deleted_notifs, _ = old_notifs.delete()
        deleted_sessions, _ = old_sessions.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Cleaned up: {deleted_logs} logs, {deleted_notifs} notifications, {deleted_sessions} sessions'
            )
        )
