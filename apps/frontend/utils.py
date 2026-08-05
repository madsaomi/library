

def month_bounds(ref_date, months_back):
    """Return (start_date, end_date) of the calendar month `months_back` months before ref_date.

    end_date is exclusive (first day of the following month).
    """
    month_index = ref_date.month - 1 - months_back
    year = ref_date.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1
    from datetime import datetime

    from django.utils import timezone

    start = datetime(year, month, 1)
    end = datetime(next_year, next_month, 1)
    return timezone.make_aware(start), timezone.make_aware(end)
