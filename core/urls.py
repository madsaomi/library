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
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect, render
from django.conf import settings
from django.views.static import serve

from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Raqamli Kutubxona Admin Paneli")
admin.site.site_title = _("Kutubxona Admin")
admin.site.index_title = _("Boshqaruv")

urlpatterns = [
    path('secret-django-admin/', admin.site.urls),
    path('', lambda r: redirect('login')), # Redirect root to login
    path('', include('accounts.urls')),
    path('admin-panel/', include('frontend_admin.urls')),
    path('school-panel/', include('frontend_school.urls')),
    path('library/', include('frontend_user.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('notifications.urls')),
]

# Serve media files
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Custom error handlers
handler403 = lambda request, exception=None: render(request, '403.html', status=403)
handler404 = lambda request, exception=None: render(request, '404.html', status=404)
handler500 = lambda request: render(request, '500.html', status=500)
