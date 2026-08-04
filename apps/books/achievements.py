import random
from datetime import timedelta

from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

LEVEL_TABLE = [
    (1, _("Boshlang'ich"), 0),
    (2, _('Kitobxon'), 30),
    (3, _('Kitobsevar'), 80),
    (4, _("Ko'p o'qigan"), 150),
    (5, _("Kitob g'irti"), 250),
    (6, _('Bilimdon'), 400),
    (7, _('Intellektual'), 600),
    (8, _('Professor'), 850),
    (9, _('Donishmand'), 1200),
    (10, _('Afsonaviy'), 2000),
]


def get_level_info(level):
    for lvl, title, xp in LEVEL_TABLE:
        if lvl == level:
            return {'level': lvl, 'title': title, 'xp_required': xp}
    return {'level': level, 'title': _("Boshlang'ich"), 'xp_required': 0}


def get_next_level_info(level):
    for lvl, title, xp in LEVEL_TABLE:
        if lvl == level + 1:
            return {'level': lvl, 'title': title, 'xp_required': xp}
    return None


def check_level_up(user):
    old_level = user.level
    new_level = user.level
    for lvl, title, xp in reversed(LEVEL_TABLE):
        if user.xp_points >= xp:
            if user.level < lvl:
                new_level = lvl
                user.level = lvl
            break
    return new_level > old_level


def check_achievements(user):
    from .models import Achievement, BookIssue, Category, UserAchievement

    earned_ids = set(UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True))
    books_count = user.total_books_read or 0
    longest_streak = user.longest_streak or 0
    cats_read = (
        BookIssue.objects.filter(user=user, is_returned=True, book__category__isnull=False)
        .values('book__category')
        .distinct()
        .count()
    )
    speed_returns = BookIssue.objects.filter(
        user=user, is_returned=True, returned_at__lte=F('issued_at') + timedelta(days=3)
    ).count()
    all_cats = Category.objects.filter(book__school=user.school).count()

    earned = []
    for ach in Achievement.objects.all():
        if ach.id in earned_ids:
            continue

        achieved = False

        if ach.condition_type == 'books_count':
            achieved = books_count >= ach.condition_value

        elif ach.condition_type == 'categories':
            achieved = cats_read >= ach.condition_value

        elif ach.condition_type == 'all_categories':
            achieved = all_cats > 0 and cats_read >= all_cats

        elif ach.condition_type == 'streak':
            achieved = longest_streak >= ach.condition_value

        elif ach.condition_type == 'speed_return':
            achieved = speed_returns >= ach.condition_value

        if achieved:
            UserAchievement.objects.create(user=user, achievement=ach)
            user.xp_points += ach.xp_reward
            earned.append(ach)

    return earned


def update_streak(user):
    today = timezone.now().date()
    if user.last_activity_date:
        delta = (today - user.last_activity_date).days
        if delta == 1:
            user.current_streak = (user.current_streak or 0) + 1
        elif delta == 0:
            pass  # same day, streak unchanged
        else:
            user.current_streak = 0  # skipped day(s), reset
    else:
        user.current_streak = 1
    user.longest_streak = max(user.longest_streak or 0, user.current_streak or 0)
    user.last_activity_date = today


def award_xp(user, action, book=None):

    xp = 0
    lucky_bonus = False

    if action == 'borrow':
        xp = 10
        if random.random() < 0.1:
            xp += 15
            lucky_bonus = True

        user.total_books_read = (user.total_books_read or 0) + 1
        user.monthly_books_read = (user.monthly_books_read or 0) + 1

    elif action == 'return':
        xp = 5

    user.xp_points = (user.xp_points or 0) + xp

    update_streak(user)

    leveled_up = check_level_up(user)

    new_achievements = check_achievements(user)

    user.save()

    return {
        'xp_earned': xp,
        'lucky_bonus': lucky_bonus,
        'leveled_up': leveled_up,
        'new_level': user.level if leveled_up else None,
        'new_achievements': [a.name for a in new_achievements],
    }
