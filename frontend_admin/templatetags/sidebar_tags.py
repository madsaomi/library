from django import template
from books.models import BookIssue

register = template.Library()

@register.simple_tag
def active_loans_count():
    return BookIssue.objects.filter(is_returned=False).count()