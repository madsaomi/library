from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Compile .po files to .mo using Babel (no gettext required)'

    def handle(self, *args, **options):
        from babel.messages import mofile, pofile

        locale_dir = Path(settings.BASE_DIR) / 'locale'
        compiled = 0
        for lang_dir in locale_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            po_path = lang_dir / 'LC_MESSAGES' / 'django.po'
            mo_path = lang_dir / 'LC_MESSAGES' / 'django.mo'
            if not po_path.exists():
                continue
            with open(po_path, 'r', encoding='utf-8') as f:
                catalog = pofile.read_po(f)
            with open(mo_path, 'wb') as f:
                mofile.write_mo(f, catalog)
            self.stdout.write(f'Compiled {lang_dir.name}: {len(catalog)} messages')
            compiled += 1
        self.stdout.write(self.style.SUCCESS(f'Done. {compiled} languages compiled.'))
