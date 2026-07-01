from django.urls import path
from . import views

app_name = 'frontend_user'

urlpatterns = [
    path('', views.library, name='library'),
    path('my-books/', views.my_books, name='my_books'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password/', views.change_password, name='change_password'),
    path('news/', views.news_list, name='news_list'),
    path('achievements/', views.achievements, name='achievements'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('challenges/', views.challenges, name='challenges'),
    path('book/<int:pk>/', views.book_detail, name='book_detail'),
    path('book/<int:pk>/reserve/', views.reserve_book, name='reserve_book'),
    path('request/<int:pk>/qr/', views.request_qr, name='request_qr'),
    path('issue/<int:pk>/qr/', views.issue_qr, name='issue_qr'),
    path('request/<int:pk>/status/', views.check_request_status, name='check_request_status'),
    path('issue/<int:pk>/status/', views.check_return_status, name='check_return_status'),
    path('token/<str:type>/<int:pk>/', views.get_rotating_token, name='get_rotating_token'),
    path('book/<int:book_pk>/join-waitlist/', views.join_waitlist, name='join_waitlist'),
    path('book/<int:book_pk>/leave-waitlist/', views.leave_waitlist, name='leave_waitlist'),
]
