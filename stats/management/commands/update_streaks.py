from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from datetime import date


class Command(BaseCommand):
    help = "Update streaks for all users — reset if inactive for more than 7 days"

    def handle(self, *args, **options):
        today = date.today()
        updated = 0
        for user in CustomUser.objects.filter(role='student'):
            if user.last_activity_date:
                delta = (today - user.last_activity_date).days
                if delta > 7:
                    user.current_streak = 0
                    user.save()
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"Streaks updated: {updated} users reset"))
