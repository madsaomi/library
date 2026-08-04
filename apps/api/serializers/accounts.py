from accounts.models import CustomUser
from rest_framework import serializers


class CustomUserSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True, default=None)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'role',
            'school',
            'school_name',
            'grade',
            'subject',
            'birth_date',
            'address',
            'is_archived',
            'xp_points',
            'level',
            'current_streak',
            'longest_streak',
            'last_activity_date',
            'total_books_read',
            'monthly_books_read',
            'selected_icon',
            'unlocked_icons',
        ]
        read_only_fields = [
            'username',
            'role',
            'school',
            'school_name',
            'xp_points',
            'level',
            'current_streak',
            'longest_streak',
            'last_activity_date',
            'total_books_read',
            'monthly_books_read',
            'unlocked_icons',
        ]


class CustomUserDetailSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True, default=None)

    class Meta:
        model = CustomUser
        exclude = ['raw_password', 'password']
        read_only_fields = [
            'xp_points',
            'level',
            'current_streak',
            'longest_streak',
            'last_activity_date',
            'total_books_read',
            'monthly_books_read',
            'unlocked_icons',
            'last_login',
            'date_joined',
        ]


class CustomUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'role',
            'school',
            'grade',
            'subject',
            'birth_date',
            'address',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        raw_password = password or CustomUser.objects.make_random_password(length=10)
        user = CustomUser(**validated_data)
        user.raw_password = raw_password
        user.set_password(raw_password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
