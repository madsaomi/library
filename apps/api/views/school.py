import csv
import io
import secrets
from datetime import timedelta

from accounts.models import CustomUser
from books.achievements import award_xp
from books.models import Book, BookIssue, BookRequest, Category, TextbookLoan
from books.search import search_books
from django.db import connection
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from stats.models import ActionLog

from api.permissions import IsSchoolAdmin, IsSchoolStaff
from api.serializers import (
    BookIssueSerializer,
    BookSerializer,
    CustomUserCreateSerializer,
    CustomUserSerializer,
    TextbookLoanSerializer,
)


class SchoolDashboardView(viewsets.ViewSet):
    permission_classes = [IsSchoolAdmin]

    def list(self, request):
        school = request.user.school
        recent_activities = (
            BookIssue.objects.filter(book__school=school).select_related('book', 'user').order_by('-issued_at')[:10]
        )
        stats = Book.objects.filter(school=school).aggregate(
            total_copies=Sum('total_count'), available_copies=Sum('available_count')
        )
        today = timezone.now()
        six_months_ago = today - timedelta(days=180)
        monthly_qs = (
            BookIssue.objects.filter(book__school=school, issued_at__gte=six_months_ago)
            .annotate(month=TruncMonth('issued_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        return Response(
            {
                'total_books': Book.objects.filter(school=school).count(),
                'total_students': CustomUser.objects.filter(school=school, role='student').count(),
                'total_teachers': CustomUser.objects.filter(school=school, role='teacher').count(),
                'active_loans': BookIssue.objects.filter(book__school=school, is_returned=False).count(),
                'total_copies': stats['total_copies'] or 0,
                'available_copies': stats['available_copies'] or 0,
                'recent_activities': BookIssueSerializer(recent_activities, many=True).data,
                'monthly_chart': {
                    str(m['month'].strftime('%Y-%m') if m['month'] else ''): m['count'] for m in monthly_qs
                },
            }
        )


class SchoolStudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = CustomUserCreateSerializer

    def get_queryset(self):
        qs = CustomUser.objects.filter(school=self.request.user.school, role='student', is_archived=False)
        q = self.request.query_params.get('q')
        grade = self.request.query_params.get('grade')
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        if grade:
            qs = qs.filter(grade=grade)
        return qs.order_by('grade', 'first_name')

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, role='student')
        ActionLog.objects.create(
            user=self.request.user, action_type='CREATE', message=f'Added student: {serializer.instance.username}'
        )

    def perform_destroy(self, instance):
        ActionLog.objects.create(
            user=self.request.user, action_type='DELETE', message=f'Deleted student: {instance.username}'
        )
        instance.is_archived = True
        instance.save()

    @action(detail=False, methods=['get'])
    def graduates(self, request):
        graduates = (
            CustomUser.objects.filter(school=request.user.school, role='student', is_archived=True)
            .select_related('school')
            .order_by('-date_joined')
        )
        page = self.paginate_queryset(graduates)
        if page is not None:
            return self.get_paginated_response(CustomUserSerializer(page, many=True).data)
        return Response(CustomUserSerializer(graduates, many=True).data)


class SchoolTeacherViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = CustomUserCreateSerializer

    def get_queryset(self):
        qs = CustomUser.objects.filter(school=self.request.user.school, role='teacher', is_archived=False)
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs.order_by('first_name')

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school, role='teacher')
        ActionLog.objects.create(
            user=self.request.user, action_type='CREATE', message=f'Added teacher: {serializer.instance.username}'
        )

    def perform_destroy(self, instance):
        ActionLog.objects.create(
            user=self.request.user, action_type='DELETE', message=f'Deleted teacher: {instance.username}'
        )
        instance.is_archived = True
        instance.save()


class SchoolBookViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = BookSerializer

    def get_queryset(self):
        qs = Book.objects.filter(school=self.request.user.school).select_related('category')
        q = self.request.query_params.get('q')
        category_id = self.request.query_params.get('category')
        textbook = self.request.query_params.get('textbook')
        if q:
            qs = search_books(qs, q)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if textbook == '1':
            qs = qs.filter(is_textbook=True)
        if not q or connection.vendor != 'postgresql':
            qs = qs.order_by('-id')
        return qs

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)
        ActionLog.objects.create(
            user=self.request.user, action_type='CREATE', message=f'Added book: {serializer.instance.title}'
        )

    def perform_destroy(self, instance):
        ActionLog.objects.create(
            user=self.request.user, action_type='DELETE', message=f'Deleted book: {instance.title}'
        )
        instance.delete()


class SchoolIssueViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = BookIssueSerializer

    def get_queryset(self):
        qs = BookIssue.objects.filter(book__school=self.request.user.school).select_related('book', 'user')
        returned = self.request.query_params.get('returned')
        if returned == '1':
            qs = qs.filter(is_returned=True)
        elif returned == '0':
            qs = qs.filter(is_returned=False)
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(
                Q(book__title__icontains=q) | Q(user__username__icontains=q) | Q(user__first_name__icontains=q)
            )
        return qs.order_by('-issued_at')


class SchoolHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = BookIssueSerializer

    def get_queryset(self):
        qs = BookIssue.objects.filter(book__school=self.request.user.school, is_returned=True)
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(book__title__icontains=q) | Q(user__username__icontains=q))
        return qs.select_related('book', 'user').order_by('-returned_at')


class SchoolStatsView(viewsets.ViewSet):
    permission_classes = [IsSchoolAdmin]

    def list(self, request):
        school = request.user.school
        today = timezone.now()
        six_months_ago = today - timedelta(days=180)
        monthly_qs = (
            BookIssue.objects.filter(book__school=school, issued_at__gte=six_months_ago)
            .annotate(month=TruncMonth('issued_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        category_dist = (
            Book.objects.filter(school=school).values('category__name').annotate(count=Count('id')).order_by('-count')
        )

        top_readers = (
            CustomUser.objects.filter(school=school, role='student')
            .annotate(books_read=Count('bookissue', filter=Q(bookissue__is_returned=True)))
            .order_by('-books_read')[:10]
        )

        return Response(
            {
                'monthly_issues': {
                    str(m['month'].strftime('%Y-%m') if m['month'] else ''): m['count'] for m in monthly_qs
                },
                'category_distribution': list(category_dist),
                'top_readers': [
                    {
                        'username': u.username,
                        'first_name': u.first_name,
                        'last_name': u.last_name,
                        'grade': u.grade,
                        'books_read': u.books_read,
                    }
                    for u in top_readers
                ],
                'total_books': Book.objects.filter(school=school).count(),
                'total_issues': BookIssue.objects.filter(book__school=school).count(),
                'active_issues': BookIssue.objects.filter(book__school=school, is_returned=False).count(),
            }
        )


class QrProcessView(viewsets.ViewSet):
    permission_classes = [IsSchoolStaff]

    @action(detail=False, methods=['post'])
    def issue(self, request):
        from books.models import BookRequest

        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        book_request = get_object_or_404(BookRequest, qr_token=token, status='approved')
        if book_request.book.school != request.user.school:
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)

        if book_request.book.available_count < 1:
            book_request.status = 'pending'
            book_request.save()
            return Response({'detail': 'No copies available.'}, status=status.HTTP_400_BAD_REQUEST)

        issue = BookIssue.objects.create(book=book_request.book, user=book_request.user)
        book_request.book.available_count -= 1
        book_request.book.borrow_count += 1
        book_request.book.save()
        book_request.status = 'completed'
        book_request.save()

        award_xp(book_request.user, 10)

        ActionLog.objects.create(
            user=request.user,
            action_type='ISSUE',
            message=f'Issued {book_request.book.title} to {book_request.user.username}',
        )
        return Response(BookIssueSerializer(issue).data)

    @action(detail=False, methods=['post'])
    def return_book(self, request):
        token = request.data.get('token')
        issue_id = request.data.get('issue_id')

        if token and not issue_id:
            try:
                real_token = request.data.get('token')
                issue = BookIssue.objects.get(qr_token=real_token, is_returned=False)
                issue_id = issue.id
            except BookIssue.DoesNotExist:
                return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not issue_id:
            return Response({'detail': 'Token or issue_id required.'}, status=status.HTTP_400_BAD_REQUEST)

        issue = get_object_or_404(BookIssue, id=issue_id, book__school=request.user.school, is_returned=False)
        issue.is_returned = True
        issue.returned_at = timezone.now()
        issue.save()

        issue.book.available_count += 1
        issue.book.save()

        if not issue.xp_awarded:
            award_xp(issue.user, 5)
            issue.xp_awarded = True
            issue.save()

        ActionLog.objects.create(
            user=request.user, action_type='RETURN', message=f'Returned {issue.book.title} from {issue.user.username}'
        )
        return Response(BookIssueSerializer(issue).data)

    @action(detail=False, methods=['post'])
    def unified(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        parts = token.split(':')
        if len(parts) == 2:
            payload, _ = parts
            if payload.startswith('issue_'):
                return self.return_book(request)
            elif payload.startswith('request_'):
                request_id = payload.replace('request_', '')
                try:
                    book_request = BookRequest.objects.get(id=request_id, status='approved')
                    request.data['token'] = book_request.qr_token
                    return self.issue(request)
                except BookRequest.DoesNotExist:
                    return Response({'detail': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        return self.issue(request)


class TextbookLoanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = TextbookLoanSerializer

    def get_queryset(self):
        qs = TextbookLoan.objects.filter(book__school=self.request.user.school).select_related('book', 'student')
        returned = self.request.query_params.get('returned')
        if returned == '1':
            qs = qs.filter(returned_at__isnull=False)
        elif returned == '0':
            qs = qs.filter(returned_at__isnull=True)
        return qs.order_by('-issued_at')

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=False, methods=['post'])
    def distribute(self, request):
        book_id = request.data.get('book_id')
        student_ids = request.data.get('student_ids', [])
        due_date = request.data.get('due_date')
        academic_year = request.data.get('academic_year')
        condition = request.data.get('condition', 'new')

        book = get_object_or_404(Book, id=book_id, school=request.user.school, is_textbook=True)
        created = []
        for sid in student_ids:
            student = get_object_or_404(CustomUser, id=sid, school=request.user.school, role='student')
            loan, was_created = TextbookLoan.objects.get_or_create(
                book=book,
                student=student,
                academic_year=academic_year,
                defaults={'due_date': due_date, 'condition_on_issue': condition},
            )
            if was_created:
                book.available_count -= 1
                created.append(TextbookLoanSerializer(loan).data)

        book.save()
        return Response({'created': created})

    @action(detail=False, methods=['post'])
    def collect(self, request):
        loan_id = request.data.get('loan_id')
        condition = request.data.get('condition')
        notes = request.data.get('notes', '')

        loan = get_object_or_404(TextbookLoan, id=loan_id, book__school=request.user.school)
        loan.returned_at = timezone.now().date()
        if condition:
            loan.condition_on_return = condition
        if notes:
            loan.notes = notes
        loan.save()

        loan.book.available_count += 1
        loan.book.save()

        return Response(TextbookLoanSerializer(loan).data)


class GraduateViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSchoolAdmin]
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        return (
            CustomUser.objects.filter(school=self.request.user.school, role='student', is_archived=True)
            .select_related('school')
            .order_by('-date_joined')
        )


class CsvExportView(viewsets.ViewSet):
    permission_classes = [IsSchoolAdmin]

    @action(detail=False, methods=['get'])
    def students(self, request):
        school = request.user.school
        students = CustomUser.objects.filter(school=school, role='student', is_archived=False, is_deleted=False)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="students.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'First Name', 'Last Name', 'Grade'])
        for s in students:
            writer.writerow([s.username, s.first_name, s.last_name, s.grade or ''])
        return response

    @action(detail=False, methods=['get'])
    def books(self, request):
        school = request.user.school
        books = Book.objects.filter(school=school, is_deleted=False).select_related('category')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="books.csv"'
        writer = csv.writer(response)
        writer.writerow(['Title', 'Author', 'Category', 'Total', 'Available', 'Textbook'])
        for b in books:
            writer.writerow(
                [
                    b.title,
                    b.author or '',
                    b.category.name if b.category else '',
                    b.total_count,
                    b.available_count,
                    'Yes' if b.is_textbook else 'No',
                ]
            )
        return response

    @action(detail=False, methods=['get'])
    def issues(self, request):
        school = request.user.school
        issues = BookIssue.objects.filter(book__school=school, is_deleted=False).select_related('book', 'user')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="issues.csv"'
        writer = csv.writer(response)
        writer.writerow(['Book', 'User', 'Issued At', 'Returned At', 'Status'])
        for i in issues:
            writer.writerow(
                [
                    i.book.title,
                    i.user.username,
                    i.issued_at,
                    i.returned_at or '',
                    'Returned' if i.is_returned else 'Active',
                ]
            )
        return response


class CsvImportView(viewsets.ViewSet):
    permission_classes = [IsSchoolAdmin]

    @action(detail=False, methods=['post'])
    def students(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'File is required.'}, status=status.HTTP_400_BAD_REQUEST)
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
        imported = 0
        errors = []
        for i, row in enumerate(reader, 1):
            try:
                username = row.get('Username', '').strip()
                if not username:
                    continue
                if CustomUser.objects.filter(username=username).exists():
                    errors.append(f"Row {i}: Username '{username}' already exists")
                    continue
                password = secrets.token_urlsafe(10)
                user = CustomUser(
                    username=username,
                    first_name=row.get('First Name', '').strip(),
                    last_name=row.get('Last Name', '').strip(),
                    grade=row.get('Grade', '').strip(),
                    school=request.user.school,
                    role='student',
                    raw_password=password,
                )
                user.set_password(password)
                user.save()
                imported += 1
            except Exception as e:
                errors.append(f'Row {i}: {str(e)}')
        return Response({'imported': imported, 'errors': errors})

    @action(detail=False, methods=['post'])
    def books(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'File is required.'}, status=status.HTTP_400_BAD_REQUEST)
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
        imported = 0
        errors = []
        for i, row in enumerate(reader, 1):
            try:
                title = row.get('Title', '').strip()
                if not title:
                    continue
                category_name = row.get('Category', '').strip()
                category = None
                if category_name:
                    category, _ = Category.objects.get_or_create(name=category_name)
                book = Book(
                    title=title,
                    author=row.get('Author', '').strip(),
                    category=category,
                    total_count=int(row.get('Total', 1)),
                    available_count=int(row.get('Available', 1)),
                    is_textbook=row.get('Textbook', 'No').lower() in ('yes', 'true', '1'),
                    school=request.user.school,
                )
                book.save()
                imported += 1
            except Exception as e:
                errors.append(f'Row {i}: {str(e)}')
        return Response({'imported': imported, 'errors': errors})
