from django import template
from django.utils.translation import gettext as _

register = template.Library()

@register.filter
def action_name(action_type):
    names = {
        'ISSUE': _("Berilgan"),
        'RETURN': _("Qabul qilingan"),
        'CREATE': _("Yaratilgan"),
        'LOGIN': _("Kirish"),
        'UPDATE': _("Yangilangan"),
        'DELETE': _("O'chirilgan"),
    }
    return names.get(action_type, action_type)
