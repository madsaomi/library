from django.contrib import admin
from .models import Category, Book, BookIssue, BookRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'school', 'total_count', 'available_count')
    list_filter = ('category', 'school')
    search_fields = ('title', 'description')

@admin.register(BookIssue)
class BookIssueAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'issued_at', 'returned_at', 'is_returned')
    list_filter = ('is_returned', 'issued_at')
    search_fields = ('book__title', 'user__username')

@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'requested_at', 'status')
    list_filter = ('status',)
    search_fields = ('book__title', 'user__username')
