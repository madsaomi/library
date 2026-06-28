from django.urls import path
from . import views

app_name = 'frontend_admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('schools/', views.schools_list, name='schools_list'),
    path('schools/add/', views.school_add, name='school_add'),
    path('schools/<int:pk>/edit/', views.school_edit, name='school_edit'),
    path('schools/<int:pk>/delete/', views.school_delete, name='school_delete'),
    path('schools/<int:pk>/', views.school_detail, name='school_detail'),
    path('districts/', views.districts_list, name='districts_list'),
    path('districts/add/', views.district_add, name='district_add'),
    path('districts/<int:pk>/edit/', views.district_edit, name='district_edit'),
    path('districts/<int:pk>/delete/', views.district_delete, name='district_delete'),
    path('muassasalar/', views.muassasalar_list, name='muassasalar_list'),
    path('muassasalar/add/', views.muassasa_add, name='muassasa_add'),
    path('muassasalar/<int:pk>/edit/', views.muassasa_edit, name='muassasa_edit'),
    path('muassasalar/<int:pk>/delete/', views.muassasa_delete, name='muassasa_delete'),
    path('statistics/', views.statistics, name='statistics'),
    path('logs/', views.system_logs, name='system_logs'),
    path('users/', views.all_users_list, name='all_users_list'),
    path('books/', views.all_books_list, name='all_books_list'),
    path('active-loans/', views.all_active_loans_list, name='all_active_loans_list'),
    path('admin/add/', views.admin_add, name='admin_add'),
    path('admin/<int:pk>/edit/', views.admin_edit, name='admin_edit'),
    path('profile/', views.profile, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
    
    # News Management
    path('news/', views.news_list, name='news_list'),
    path('news/add/', views.news_add, name='news_add'),
    path('news/<int:pk>/edit/', views.news_edit, name='news_edit'),
    path('news/<int:pk>/delete/', views.news_delete, name='news_delete'),
    path('check-username/', views.check_username, name='check_username'),
]
