from django.contrib import admin
from .models import ActionLog

@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'message', 'created_at')
    list_filter = ('action_type', 'created_at')
    search_fields = ('user__username', 'message')
