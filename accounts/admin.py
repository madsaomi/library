from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'school', 'is_staff')
    list_filter = ('role', 'school', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'school', 'grade')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {'fields': ('role', 'school', 'grade')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
