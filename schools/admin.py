from django.contrib import admin
from .models import School, Institution

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name',)

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'contact')
    search_fields = ('name', 'address')
