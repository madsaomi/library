from django.contrib import admin

from .models import (
    Achievement,
    Book,
    BookCart,
    BookCartItem,
    BookIssue,
    BookRequest,
    BookWaitlist,
    Category,
    Challenge,
    ReaderOfMonth,
    TextbookLoan,
    UserAchievement,
    UserChallenge,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'school', 'author', 'total_count', 'available_count')
    list_filter = ('category', 'school')
    search_fields = ('title', 'author', 'description')
    readonly_fields = ('available_count',)


@admin.register(BookIssue)
class BookIssueAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'issued_at', 'returned_at', 'is_returned')
    list_filter = ('is_returned', 'issued_at', 'book__school')
    search_fields = ('book__title', 'user__username', 'book__author')
    date_hierarchy = 'issued_at'


@admin.register(TextbookLoan)
class TextbookLoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'student', 'issued_at', 'returned_at', 'academic_year')
    list_filter = ('book__school',)
    search_fields = ('book__title', 'student__username')
    date_hierarchy = 'issued_at'


@admin.register(BookRequest)
class BookRequestAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'requested_at', 'status')
    list_filter = ('status', 'book__school')
    search_fields = ('book__title', 'user__username', 'notes')
    date_hierarchy = 'requested_at'


@admin.register(BookWaitlist)
class BookWaitlistAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'created_at', 'is_notified')
    list_filter = ('is_notified', 'book__school')
    search_fields = ('book__title', 'user__username')
    date_hierarchy = 'created_at'


@admin.register(BookCart)
class BookCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'status', 'created_at', 'borrowed_at', 'returned_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'qr_token')
    date_hierarchy = 'created_at'


@admin.register(BookCartItem)
class BookCartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'book', 'created_at')
    list_filter = ('cart__user', 'book__school')
    search_fields = ('cart__user__username', 'book__title')
    date_hierarchy = 'created_at'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'icon')
    search_fields = ('name', 'description')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('achievement',)
    search_fields = ('user__username', 'achievement__name')
    date_hierarchy = 'earned_at'


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'progress', 'completed', 'completed_at')
    list_filter = ('completed', 'challenge')
    search_fields = ('user__username', 'challenge__title')


@admin.register(ReaderOfMonth)
class ReaderOfMonthAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'month', 'year', 'books_count')
    list_filter = ('school', 'month', 'year')
    search_fields = ('user__username',)
