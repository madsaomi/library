from django.core.management.base import BaseCommand
from books.models import Achievement


ACHIEVEMENTS = [
    {
        'key': 'first_book',
        'name': 'Первая книга',
        'description': 'Взял первую книгу в библиотеке',
        'icon': 'fa-star',
        'xp_reward': 15,
        'condition_type': 'books_count',
        'condition_value': 1,
    },
    {
        'key': 'ten_books',
        'name': 'Заядлый читатель',
        'description': 'Прочитал 10 книг',
        'icon': 'fa-book',
        'xp_reward': 30,
        'condition_type': 'books_count',
        'condition_value': 10,
    },
    {
        'key': 'fifty_books',
        'name': 'Книжный червь',
        'description': 'Прочитал 50 книг',
        'icon': 'fa-book-open',
        'xp_reward': 100,
        'condition_type': 'books_count',
        'condition_value': 50,
    },
    {
        'key': 'hundred_books',
        'name': 'Легенда чтения',
        'description': 'Прочитал 100 книг',
        'icon': 'fa-crown',
        'xp_reward': 250,
        'condition_type': 'books_count',
        'condition_value': 100,
    },
    {
        'key': 'five_categories',
        'name': 'Эрудит',
        'description': 'Прочитал книги из 5 разных категорий',
        'icon': 'fa-graduation-cap',
        'xp_reward': 50,
        'condition_type': 'categories',
        'condition_value': 5,
    },
    {
        'key': 'all_categories',
        'name': 'Всеядный',
        'description': 'Прочитал книги из всех категорий школы',
        'icon': 'fa-globe',
        'xp_reward': 100,
        'condition_type': 'all_categories',
        'condition_value': 0,
    },
    {
        'key': 'speed_return',
        'name': 'Скорочтение',
        'description': 'Вернул 5 книг в течение 3 дней',
        'icon': 'fa-rocket',
        'xp_reward': 40,
        'condition_type': 'speed_return',
        'condition_value': 5,
    },
    {
        'key': 'streak_4',
        'name': 'Завсегдатай',
        'description': 'Достиг streak в 4 недели',
        'icon': 'fa-fire',
        'xp_reward': 50,
        'condition_type': 'streak',
        'condition_value': 4,
    },
    {
        'key': 'streak_8',
        'name': 'Неутомимый',
        'description': 'Достиг streak в 8 недель',
        'icon': 'fa-infinity',
        'xp_reward': 150,
        'condition_type': 'streak',
        'condition_value': 8,
    },
]


class Command(BaseCommand):
    help = "Seed default achievements into the database"

    def handle(self, *args, **options):
        created = 0
        for data in ACHIEVEMENTS:
            _, is_new = Achievement.objects.get_or_create(
                key=data['key'],
                defaults=data
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} achievements"))
