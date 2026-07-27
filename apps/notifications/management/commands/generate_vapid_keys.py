from django.core.management.base import BaseCommand
from py_vapid import Vapid


class Command(BaseCommand):
    help = 'Generate VAPID keys for Web Push notifications'

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()
        self.stdout.write('\nVAPID Keys generated! Add these to your .env or Railway variables:\n')
        self.stdout.write(f'VAPID_PUBLIC_KEY={vapid.public_key.decode()}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={vapid.private_key.decode()}')
        self.stdout.write('VAPID_ADMIN_EMAIL=admin@kutubxona.uz')
