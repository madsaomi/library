from books.models import (
    Achievement,
    Book,
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
from rest_framework import serializers


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ['school', 'borrow_count']


class BookListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    currently_reading = serializers.IntegerField(source='currently_reading_count', read_only=True)

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'category',
            'category_name',
            'cover',
            'total_count',
            'available_count',
            'borrow_count',
            'is_textbook',
            'subject',
            'grade',
            'currently_reading',
        ]


class BookIssueSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = BookIssue
        fields = '__all__'

    def get_user_full_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'.strip()


class BookRequestSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = BookRequest
        fields = '__all__'


class BookWaitlistSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = BookWaitlist
        fields = '__all__'

    def get_position(self, obj):
        return BookWaitlist.objects.filter(book=obj.book, created_at__lt=obj.created_at).count() + 1


class TextbookLoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    student_grade = serializers.CharField(source='student.grade', read_only=True)

    class Meta:
        model = TextbookLoan
        fields = '__all__'

    def get_student_name(self, obj):
        return f'{obj.student.first_name} {obj.student.last_name}'.strip()


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = '__all__'


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='achievement.name', read_only=True)
    achievement_description = serializers.CharField(source='achievement.description', read_only=True)
    achievement_icon = serializers.CharField(source='achievement.icon', read_only=True)
    achievement_xp = serializers.IntegerField(source='achievement.xp_reward', read_only=True)

    class Meta:
        model = UserAchievement
        fields = '__all__'


class ChallengeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    class Meta:
        model = Challenge
        fields = '__all__'


class UserChallengeSerializer(serializers.ModelSerializer):
    challenge_title = serializers.CharField(source='challenge.title', read_only=True)
    challenge_description = serializers.CharField(source='challenge.description', read_only=True)
    challenge_type = serializers.CharField(source='challenge.challenge_type', read_only=True)
    challenge_target = serializers.IntegerField(source='challenge.target_count', read_only=True)
    challenge_xp = serializers.IntegerField(source='challenge.xp_reward', read_only=True)

    class Meta:
        model = UserChallenge
        fields = '__all__'


class ReaderOfMonthSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    user_grade = serializers.CharField(source='user.grade', read_only=True)

    class Meta:
        model = ReaderOfMonth
        fields = '__all__'

    def get_user_full_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'.strip()
