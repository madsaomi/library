from django import template
from django.utils.translation import gettext as _

register = template.Library()

ACHIEVEMENT_NAME_KEYS = {
    'first_book': "Birinchi kitob",
    'ten_books': "Ixtiyoriy o'quvchi",
    'fifty_books': "Kitob qurti",
    'hundred_books': "O'qish afsonasi",
    'five_categories': "Bilimdon",
    'all_categories': "Hammayeydi",
    'speed_return': "Tez o'quvchi",
    'streak_4': "Doimiy o'quvchi",
    'streak_8': "Tinimsiz o'quvchi",
}

ACHIEVEMENT_DESC_KEYS = {
    'first_book': "Kutubxonadan birinchi kitobni oldi",
    'ten_books': "10 ta kitob o'qidi",
    'fifty_books': "50 ta kitob o'qidi",
    'hundred_books': "100 ta kitob o'qidi",
    'five_categories': "5 xil kategoriyadagi kitoblarni o'qidi",
    'all_categories': "Maktabdagi barcha kategoriyalardan kitob o'qidi",
    'speed_return': "3 kun ichida 5 ta kitobni qaytardi",
    'streak_4': "4 haftalik streak-ga erishdi",
    'streak_8': "8 haftalik streak-ga erishdi",
}


@register.filter
def ach_name(achievement):
    msgid = ACHIEVEMENT_NAME_KEYS.get(achievement.key)
    if msgid:
        return _(msgid)
    return achievement.name


@register.filter
def ach_desc(achievement):
    msgid = ACHIEVEMENT_DESC_KEYS.get(achievement.key)
    if msgid:
        return _(msgid)
    return achievement.description


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
