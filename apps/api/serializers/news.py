from rest_framework import serializers
from schools.models import News


class NewsSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True, default=None)

    class Meta:
        model = News
        fields = '__all__'
