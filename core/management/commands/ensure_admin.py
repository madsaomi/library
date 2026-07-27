from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates superuser from environment variables or defaults'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'admin'
        password = 'superadmin'

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, password=password, email='')
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created'))
        else:
            self.stdout.write(f'Superuser "{username}" already exists')
