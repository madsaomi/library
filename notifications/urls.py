from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('api/notifications/subscribe/', views.subscribe, name='subscribe'),
    path('api/notifications/unsubscribe/', views.unsubscribe, name='unsubscribe'),
    path('api/notifications/', views.list_notifications, name='list'),
    path('api/notifications/unread-count/', views.unread_count, name='unread_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_read, name='mark_read'),
    path('api/notifications/read-all/', views.mark_all_read, name='mark_all_read'),
    path('api/notifications/top/', views.top_notification_api, name='top'),
]
