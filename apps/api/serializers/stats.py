from rest_framework import serializers
from stats.models import ActionLog


class ActionLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = ActionLog
        fields = '__all__'
