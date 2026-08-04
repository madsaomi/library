from accounts.models import CustomUser
from books.models import (
    Achievement,
    Book,
    BookIssue,
    BookRequest,
    BookWaitlist,
    Category,
    Challenge,
    ReaderOfMonth,
    UserAchievement,
    UserChallenge,
)
from books.search import search_books
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from schools.models import News

from api.permissions import IsStudent, IsStudentOrTeacher
from api.serializers import (
    AchievementSerializer,
    BookIssueSerializer,
    BookListSerializer,
    BookRequestSerializer,
    BookSerializer,
    BookWaitlistSerializer,
    ChallengeSerializer,
    CustomUserSerializer,
    NewsSerializer,
    ReaderOfMonthSerializer,
    UserAchievementSerializer,
    UserChallengeSerializer,
)


class CatalogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudentOrTeacher]
    serializer_class = BookListSerializer

    def get_queryset(self):
        if not self.request.user.school:
            return Book.objects.none()
        query = self.request.query_params.get('q')
        category_id = self.request.query_params.get('category')
        textbook = self.request.query_params.get('textbook')

        qs = Book.objects.filter(school=self.request.user.school).select_related('category')

        if query:
            qs = search_books(qs, query)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if textbook == '1':
            qs = qs.filter(is_textbook=True)

        if not query:
            qs = qs.order_by('-borrow_count')

        return qs

    @action(detail=False, methods=['get'])
    def categories(self, request):
        return Response([{'id': c.id, 'name': c.name} for c in Category.objects.all()])

    @action(detail=False, methods=['get'])
    def reader_of_month(self, request):
        school = request.user.school
        if not school:
            return Response(None)
        now = timezone.now()
        cache_key = f'reader_month_{school.id}_{now.month}'
        reader = cache.get(cache_key)
        if reader is None:
            reader = (
                ReaderOfMonth.objects.filter(school=school, month=now.month, year=now.year)
                .select_related('user')
                .first()
            )
            if reader:
                cache.set(cache_key, reader, 3600)
        if reader:
            return Response(ReaderOfMonthSerializer(reader).data)
        return Response(None)

    @action(detail=False, methods=['get'])
    def active_reads(self, request):
        reads = (
            BookIssue.objects.filter(book__school=request.user.school, is_returned=False)
            .select_related('user', 'book')
            .order_by('-issued_at')[:10]
        )
        return Response(BookIssueSerializer(reads, many=True).data)


class MyBooksViewSet(viewsets.ViewSet):
    permission_classes = [IsStudentOrTeacher]

    def list(self, request):
        active_issues = BookIssue.objects.filter(user=request.user, is_returned=False).select_related('book')
        history = (
            BookIssue.objects.filter(user=request.user, is_returned=True)
            .select_related('book')
            .order_by('-returned_at')[:20]
        )
        requests = BookRequest.objects.filter(user=request.user).select_related('book').order_by('-requested_at')

        return Response(
            {
                'active': BookIssueSerializer(active_issues, many=True).data,
                'history': BookIssueSerializer(history, many=True).data,
                'requests': BookRequestSerializer(requests, many=True).data,
            }
        )

    @action(detail=False, methods=['get'])
    def reading_summary(self, request):
        user = request.user
        return Response(
            {
                'total_books_read': user.total_books_read,
                'monthly_books_read': user.monthly_books_read,
                'current_streak': user.current_streak,
                'longest_streak': user.longest_streak,
                'xp_points': user.xp_points,
                'level': user.level,
            }
        )


class BookDetailViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudentOrTeacher]
    serializer_class = BookSerializer

    def get_queryset(self):
        if not self.request.user.school:
            return Book.objects.none()
        return Book.objects.select_related('category', 'school').filter(school=self.request.user.school)

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        book = self.get_object()
        if book.available_count <= 0:
            return Response({'detail': 'No copies available.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already requested
        existing = BookRequest.objects.filter(user=request.user, book=book, status='pending').first()
        if existing:
            return Response(BookRequestSerializer(existing).data)

        book_request = BookRequest.objects.create(
            book=book, user=request.user, status='pending'
        )
        return Response(BookRequestSerializer(book_request).data)

    @action(detail=True, methods=['post'])
    def join_waitlist(self, request, pk=None):
        book = self.get_object()
        _, created = BookWaitlist.objects.get_or_create(book=book, user=request.user)
        if created:
            return Response({'detail': 'Added to waitlist.'})
        return Response({'detail': 'Already in waitlist.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def leave_waitlist(self, request, pk=None):
        book = self.get_object()
        BookWaitlist.objects.filter(book=book, user=request.user).delete()
        return Response({'detail': 'Removed from waitlist.'})

    @action(detail=True, methods=['get'])
    def waitlist_info(self, request, pk=None):
        book = self.get_object()
        queue = BookWaitlist.objects.filter(book=book).order_by('created_at')
        user_position = None
        for i, w in enumerate(queue, 1):
            if w.user == request.user:
                user_position = i
                break
        return Response(
            {
                'queue_length': queue.count(),
                'user_position': user_position,
            }
        )


class MyProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsStudentOrTeacher]

    def list(self, request):
        return Response(CustomUserSerializer(request.user).data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        form = PasswordChangeForm(request.user, request.data)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return Response({'detail': 'Password changed.'})
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudentOrTeacher]
    serializer_class = AchievementSerializer
    queryset = Achievement.objects.all()

    @action(detail=False, methods=['get'])
    def my(self, request):
        user_achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
        return Response(UserAchievementSerializer(user_achievements, many=True).data)


class ChallengeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudentOrTeacher]
    serializer_class = ChallengeSerializer

    def get_queryset(self):
        school = self.request.user.school
        return Challenge.objects.filter(
            Q(school=school) | Q(school__isnull=True),
            is_active=True,
        ).select_related('category')

    @action(detail=False, methods=['get'])
    def my(self, request):
        user_challenges = UserChallenge.objects.filter(user=request.user).select_related('challenge')
        return Response(UserChallengeSerializer(user_challenges, many=True).data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        challenge = self.get_object()
        _, created = UserChallenge.objects.get_or_create(user=request.user, challenge=challenge)
        if created:
            return Response({'detail': 'Joined challenge.'})
        return Response({'detail': 'Already joined.'}, status=status.HTTP_400_BAD_REQUEST)


class LeaderboardView(viewsets.ViewSet):
    permission_classes = [IsStudentOrTeacher]

    def list(self, request):
        school = request.user.school
        period = request.query_params.get('period', 'all_time')

        if period == 'monthly':
            users = CustomUser.objects.filter(school=school, role='student').order_by('-monthly_books_read')[:20]
            key = 'monthly_books_read'
        else:
            users = CustomUser.objects.filter(school=school, role='student').order_by('-xp_points')[:20]
            key = 'xp_points'

        return Response(
            [
                {
                    'id': u.id,
                    'username': u.username,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'grade': u.grade,
                    'value': getattr(u, key),
                    'level': u.level,
                    'selected_icon': u.selected_icon,
                }
                for u in users
            ]
        )

    @action(detail=False, methods=['get'])
    def my_rank(self, request):
        school = request.user.school
        period = request.query_params.get('period', 'all_time')
        if period == 'monthly':
            all_users = CustomUser.objects.filter(school=school, role='student').order_by('-monthly_books_read')
        else:
            all_users = CustomUser.objects.filter(school=school, role='student').order_by('-xp_points')

        rank = 1
        for u in all_users:
            if u.id == request.user.id:
                break
            rank += 1
        return Response({'rank': rank, 'total': all_users.count()})


class WaitlistViewSet(viewsets.ViewSet):
    permission_classes = [IsStudentOrTeacher]

    def list(self, request):
        waitlist = BookWaitlist.objects.filter(user=request.user).select_related('book')
        return Response(BookWaitlistSerializer(waitlist, many=True).data)

    @action(detail=False, methods=['delete'])
    def leave(self, request):
        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'detail': 'book_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        BookWaitlist.objects.filter(book_id=book_id, user=request.user).delete()
        return Response({'detail': 'Left waitlist.'})


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudentOrTeacher]
    serializer_class = NewsSerializer

    def get_queryset(self):
        return (
            News.objects.filter(
                Q(school=self.request.user.school) | Q(school__isnull=True),
                is_published=True,
            )
            .select_related('school')
            .order_by('-created_at')
        )


class MyClassView(viewsets.ViewSet):
    permission_classes = [IsStudent]

    def list(self, request):
        if not request.user.grade:
            return Response({'detail': 'No grade assigned.'}, status=status.HTTP_400_BAD_REQUEST)
        classmates = (
            CustomUser.objects.filter(school=request.user.school, role='student', grade=request.user.grade)
            .exclude(id=request.user.id)
            .select_related('school')
            .order_by('first_name')
        )
        return Response(CustomUserSerializer(classmates, many=True).data)
