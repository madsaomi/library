from datetime import timedelta

from accounts.models import CustomUser
from books.models import Book, BookIssue
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from schools.models import District, Institution, School
from stats.models import ActionLog

from api.permissions import IsSuperuser
from api.serializers import (
    ActionLogSerializer,
    BookIssueSerializer,
    BookSerializer,
    CustomUserCreateSerializer,
    CustomUserDetailSerializer,
    DistrictSerializer,
    InstitutionSerializer,
    SchoolSerializer,
)


class SoftDeleteMixin:
    """Soft-delete support: hides is_deleted rows and logs DELETE actions."""

    delete_label = 'Deleted {instance}'

    def perform_destroy(self, instance):
        ActionLog.objects.create(
            user=self.request.user,
            action_type='DELETE',
            message=self.delete_label.format(instance=instance),
        )
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SchoolViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = SchoolSerializer

    def get_queryset(self):
        qs = (
            School.objects.filter(is_deleted=False)
            .select_related('district')
            .annotate(
                has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin')),
                student_count=Count('customuser', filter=Q(customuser__role='student')),
                book_count=Count('book', distinct=True),
            )
            .order_by('-id')
        )
        district_id = self.request.query_params.get('district')
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(district__name__icontains=q))
        if district_id:
            qs = qs.filter(district_id=district_id)
        return qs

    @action(detail=False, methods=['get'])
    def brief(self, request):
        qs = self.filter_queryset(School.objects.filter(is_deleted=False)).only('id', 'name')
        return Response([{'id': s.id, 'name': s.name} for s in qs])


class DistrictViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = DistrictSerializer
    queryset = District.objects.filter(is_deleted=False)

    def get_queryset(self):
        return (
            District.objects.filter(is_deleted=False)
            .annotate(school_count=Count('schools', filter=Q(schools__customuser__role='school_admin')))
            .order_by('name')
        )


class InstitutionViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = InstitutionSerializer
    queryset = Institution.objects.filter(is_deleted=False).order_by('-id')


class AllUsersViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = CustomUserDetailSerializer

    def get_queryset(self):
        qs = CustomUser.objects.filter(is_deleted=False).select_related('school').order_by('-date_joined')
        role = self.request.query_params.get('role')
        school_id = self.request.query_params.get('school')
        archived = self.request.query_params.get('archived')
        q = self.request.query_params.get('q')
        if role:
            qs = qs.filter(role=role)
        if school_id:
            qs = qs.filter(school_id=school_id)
        if archived == '1':
            qs = qs.filter(is_archived=True)
        elif archived == '0':
            qs = qs.filter(is_archived=False)
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs

    @action(detail=False, methods=['get'])
    def stats(self, request):
        roles = CustomUser.objects.values('role').annotate(count=Count('id'))
        return Response({r['role']: r['count'] for r in roles})


class AdminUserViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = CustomUserCreateSerializer
    delete_label = 'Deleted school admin: {instance.username}'

    def get_queryset(self):
        return CustomUser.objects.filter(role='school_admin', is_deleted=False).order_by('-date_joined')

    def perform_create(self, serializer):
        user = serializer.save()
        ActionLog.objects.create(
            user=self.request.user, action_type='CREATE', message=f'Created school admin: {user.username}'
        )

    def perform_update(self, serializer):
        user = serializer.save()
        ActionLog.objects.create(
            user=self.request.user, action_type='UPDATE', message=f'Updated school admin: {user.username}'
        )


class AllBooksViewSet(SoftDeleteMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = BookSerializer
    queryset = Book.objects.filter(is_deleted=False).select_related('category', 'school').order_by('-id')


class AllActiveLoansViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = BookIssueSerializer

    def get_queryset(self):
        qs = BookIssue.objects.select_related('book', 'user').order_by('-issued_at')
        q = self.request.query_params.get('q')
        school_id = self.request.query_params.get('school')
        returned = self.request.query_params.get('returned')
        if returned == '1':
            qs = qs.filter(is_returned=True)
        elif returned == '0':
            qs = qs.filter(is_returned=False)
        if school_id:
            qs = qs.filter(book__school_id=school_id)
        if q:
            qs = qs.filter(Q(book__title__icontains=q) | Q(user__username__icontains=q))
        return qs


class SystemLogsView(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperuser]
    serializer_class = ActionLogSerializer
    queryset = ActionLog.objects.select_related('user').all().order_by('-created_at')


class SuperUserStatsView(viewsets.ViewSet):
    permission_classes = [IsSuperuser]

    def list(self, request):
        active_schools = School.objects.annotate(
            has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin'))
        ).filter(has_admin=True, is_deleted=False)

        monthly_issues = []
        for i in range(11, -1, -1):
            month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            count = BookIssue.objects.filter(issued_at__gte=month_start, issued_at__lt=month_end, is_deleted=False).count()
            monthly_issues.append(count)

        top_books = list(Book.objects.filter(is_deleted=False).order_by('-borrow_count')[:10].values('title', 'borrow_count'))
        roles = CustomUser.objects.filter(is_deleted=False).values('role').annotate(count=Count('id'))

        return Response(
            {
                'school_count': active_schools.count(),
                'user_count': CustomUser.objects.filter(is_deleted=False).count(),
                'total_books': Book.objects.filter(is_deleted=False).count(),
                'active_loans': BookIssue.objects.filter(is_returned=False, is_deleted=False).count(),
                'institutions_count': Institution.objects.filter(is_deleted=False).count(),
                'monthly_issues': monthly_issues,
                'top_books': top_books,
                'roles': {r['role']: r['count'] for r in roles},
            }
        )

    @action(detail=False, methods=['get'])
    def recent_logs(self, request):
        logs = ActionLog.objects.select_related('user').all().order_by('-created_at')[:10]
        return Response(ActionLogSerializer(logs, many=True).data)
