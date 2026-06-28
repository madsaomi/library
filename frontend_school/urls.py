from django.urls import path
from . import views

app_name = 'frontend_school'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('books/', views.books_list, name='books_list'),
    path('issued-books/', views.issued_books_list, name='issued_books_list'),
    path('history/', views.history_list, name='history_list'),
    path('news/', views.news_list, name='news_list'),
    path('qr-scanner/', views.qr_unified, name='qr_scanner'),
    path('process-qr/', views.process_qr, name='process_qr'),
    path('process-receive-qr/', views.process_receive_qr, name='process_receive_qr'),
    path('process-qr-unified/', views.process_qr_unified, name='process_qr_unified'),
    path('books/add/', views.book_add, name='book_add'),
    path('books/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('books/<int:pk>/delete/', views.book_delete, name='book_delete'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('teachers/add/', views.teacher_add, name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    path('news/add/', views.news_add, name='news_add'),
    path('news/<int:pk>/edit/', views.news_edit, name='news_edit'),
    path('news/<int:pk>/delete/', views.news_delete, name='news_delete'),
    path('profile/', views.profile, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
]
