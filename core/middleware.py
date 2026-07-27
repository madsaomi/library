from datetime import date

from django.core.cache import cache
from django.utils import timezone


class TenantSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response


class GradePromotionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        today = timezone.now().date()
        if today >= date(today.year, 9, 1):
            cache_key = f'grade_promotion_done_{today.year}'
            if cache.get(cache_key):
                response = self.get_response(request)
                return response
            from schools.models import GradePromotionLog

            if not GradePromotionLog.objects.filter(year=today.year).exists():
                from accounts.models import CustomUser

                students = CustomUser.objects.filter(role='student', is_archived=False)
                for student in students:
                    if not student.grade:
                        continue
                    parts = student.grade.strip().split('-')
                    try:
                        num = int(parts[0])
                    except ValueError, IndexError:
                        continue
                    num += 1
                    if num > 11:
                        student.is_archived = True
                    else:
                        suffix = f'-{parts[1]}' if len(parts) > 1 else ''
                        student.grade = f'{num}{suffix}'
                    student.save()
                GradePromotionLog.objects.create(year=today.year)
                cache.set(cache_key, True, 86400)
        response = self.get_response(request)
        return response
