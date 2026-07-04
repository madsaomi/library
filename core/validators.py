from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


def validate_word_limit(value, limit):
    if not value:
        return
    words = value.split()
    if len(words) > limit:
        raise ValidationError(_("Limit: %(limit)s ta so'z. Siz %(count)s ta so'z kiritdingiz.") % {'limit': limit, 'count': len(words)})


def validate_char_limit(value, limit):
    if not value:
        return
    if len(value) > limit:
        raise ValidationError(_("Limit: %(limit)s ta belgi. Siz %(count)s ta belgi kiritdingiz.") % {'limit': limit, 'count': len(value)})
