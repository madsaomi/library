"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import include, path, re_path
from django.utils.translation import gettext_lazy as _
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from core.views import health_check, offline_view, service_worker

admin.site.site_header = _('Raqamli Kutubxona Admin Paneli')
admin.site.site_title = _('Kutubxona Admin')
admin.site.index_title = _('Boshqaruv')

urlpatterns = [
    path('secret-django-admin/', admin.site.urls),
    path('', lambda r: redirect('login')),  # Redirect root to login
    path('', include('accounts.urls')),
    path('', include('frontend.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('notifications.urls')),
    path('api/', include('api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/health/', health_check, name='health-check'),
    path('offline/', offline_view, name='offline'),
    path('service-worker.js', service_worker, name='service_worker'),
]

# Serve media files
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]


# Custom error handlers
def handler403(request, exception=None):
    return render(request, '403.html', status=403)


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
