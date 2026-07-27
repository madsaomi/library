from django.contrib import admin

from .models import District, GradePromotionLog, Institution, News, School, Subject


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name',)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact', 'district')
    list_filter = ('district',)
    search_fields = ('name', 'address')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'created_at')
    list_filter = ('school', 'created_at')
    search_fields = ('title', 'body')
    date_hierarchy = 'created_at'


@admin.register(GradePromotionLog)
class GradePromotionLogAdmin(admin.ModelAdmin):
    list_display = ('year', 'promoted_at')
    search_fields = ('year',)
    date_hierarchy = 'promoted_at'
