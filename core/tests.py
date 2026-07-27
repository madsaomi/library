from datetime import date
from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings

from core.middleware import GradePromotionMiddleware, TenantSecurityMiddleware

pytestmark = pytest.mark.django_db


class TestTenantSecurityMiddleware:
    def test_middleware_passthrough(self):
        factory = RequestFactory()
        request = factory.get('/')
        middleware = TenantSecurityMiddleware(lambda r: type('Response', (), {'status_code': 200})())
        response = middleware(request)
        assert response.status_code == 200


class TestGradePromotionMiddleware:
    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    @patch('core.middleware.timezone.now')
    def test_middleware_no_promotion_before_september(self, mock_now):
        mock_now.return_value.date.return_value = date(2026, 3, 1)
        factory = RequestFactory()
        request = factory.get('/')
        middleware = GradePromotionMiddleware(lambda r: type('Response', (), {'status_code': 200})())
        response = middleware(request)
        assert response.status_code == 200

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    @patch('core.middleware.timezone.now')
    def test_middleware_promotion_after_september(self, mock_now, student):
        mock_now.return_value.date.return_value = date(2026, 9, 15)
        student.grade = '5-A'
        student.save()
        factory = RequestFactory()
        request = factory.get('/')
        middleware = GradePromotionMiddleware(lambda r: type('Response', (), {'status_code': 200})())
        response = middleware(request)
        assert response.status_code == 200
        student.refresh_from_db()
        assert student.grade == '6-A'

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    @patch('core.middleware.timezone.now')
    def test_middleware_archive_grade_11(self, mock_now, student):
        mock_now.return_value.date.return_value = date(2026, 9, 15)
        student.grade = '11'
        student.save()
        factory = RequestFactory()
        request = factory.get('/')
        middleware = GradePromotionMiddleware(lambda r: type('Response', (), {'status_code': 200})())
        response = middleware(request)
        assert response.status_code == 200
        student.refresh_from_db()
        assert student.is_archived is True
