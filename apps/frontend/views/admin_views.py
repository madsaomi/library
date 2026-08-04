from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

superuser_required = user_passes_test(lambda u: u.is_superuser, login_url='login')

import secrets
import string

from accounts.models import CustomUser
from books.models import Book, BookIssue
from django.db.models import Q
from schools.models import District, Institution, News, School

from frontend.forms import NewsForm


def clean_name(name):
    return ''.join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')


@login_required(login_url='login')
@superuser_required
def dashboard(request):

    from accounts.models import CustomUser
    from django.db.models import Count, Exists, OuterRef
    from django.utils import timezone
    from stats.models import ActionLog

    from frontend.utils import month_bounds

    active_schools_query = School.objects.annotate(
        has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin'))
    ).filter(has_admin=True)

    # Chart data: monthly issues
    from django.utils.translation import gettext as _

    month_abbrs = [
        _('Yan'),
        _('Fev'),
        _('Mar'),
        _('Apr'),
        _('May'),
        _('Iyun'),
        _('Iyl'),
        _('Avg'),
        _('Sen'),
        _('Okt'),
        _('Noy'),
        _('Dek'),
    ]
    monthly_issues = []
    today = timezone.now().date()
    for i in range(11, -1, -1):
        month_start, month_end = month_bounds(today, i)
        count = (
            BookIssue.objects.select_related('book', 'user')
            .filter(issued_at__gte=month_start, issued_at__lt=month_end)
            .count()
        )
        monthly_issues.append(count)

    # Top books
    top_books = Book.objects.order_by('-borrow_count')[:10].values('title', 'borrow_count')

    # User roles
    roles = CustomUser.objects.values('role').annotate(count=Count('id'))

    context = {
        'school_count': active_schools_query.count(),
        'user_count': CustomUser.objects.count(),
        'total_books': Book.objects.count(),
        'active_loans': BookIssue.objects.select_related('book', 'user').filter(is_returned=False).count(),
        'schools': active_schools_query.order_by('-id')[:5],
        'institutions_count': Institution.objects.count(),
        'recent_logs': ActionLog.objects.all().order_by('-created_at')[:10],
        'monthly_issues': monthly_issues,
        'month_labels': [month_abbrs[(timezone.now().month - 1 - i) % 12] for i in range(11, -1, -1)],
        'top_books': list(top_books),
        'top_books_labels': [b['title'] for b in top_books],
        'top_books_data': [b['borrow_count'] for b in top_books],
        'roles': {r['role']: r['count'] for r in roles},
        'role_labels': {
            'superuser': _('Superuser'),
            'school_admin': _('School Admin'),
            'student': _('Student'),
            'teacher': _('Teacher'),
        },
    }
    return render(request, 'frontend/admin/dashboard.html', context)


@login_required(login_url='login')
@superuser_required
def schools_list(request):
    from django.db.models import Count, Exists, OuterRef, Q

    district_id = request.GET.get('district')
    q = request.GET.get('q')

    from accounts.models import CustomUser
    from django.db.models import Prefetch

    admins_qs = CustomUser.objects.filter(role='school_admin').only(
        'id', 'username', 'school_id', 'first_name', 'last_name'
    )
    schools = (
        School.objects.annotate(
            has_admin=Exists(CustomUser.objects.filter(school=OuterRef('pk'), role='school_admin')),
            student_count=Count('customuser', filter=Q(customuser__role='student')),
            book_count=Count('book', distinct=True),
            category_count=Count('book__category', distinct=True),
        )
        .filter(has_admin=True)
        .prefetch_related(Prefetch('customuser_set', queryset=admins_qs, to_attr='admins'))
    )

    if q:
        schools = schools.filter(Q(name__icontains=q) | Q(address__icontains=q) | Q(district__name__icontains=q))

    if district_id:
        schools = schools.filter(district_id=district_id)

    schools = schools.order_by('-id')
    districts = District.objects.annotate(
        school_count=Count('schools', filter=Q(schools__customuser__role='school_admin'))
    ).order_by('name')

    total_students = CustomUser.objects.filter(role='student').count()
    total_books = Book.objects.count()
    return render(
        request,
        'frontend/admin/schools.html',
        {
            'schools': schools,
            'districts': districts,
            'current_district': district_id,
            'current_query': q or '',
            'total_students': total_students,
            'total_books': total_books,
        },
    )


from django.http import JsonResponse


@login_required(login_url='login')
@superuser_required
def check_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'error': _('Login kiriting')})

    exists = CustomUser.objects.filter(username=username).exists()
    return JsonResponse({'available': not exists})


@login_required(login_url='login')
@superuser_required
def muassasalar_list(request):
    institutions = Institution.objects.filter(is_deleted=False).order_by('-id')
    return render(request, 'frontend/admin/muassasalar.html', {'institutions': institutions})


@login_required(login_url='login')
@superuser_required
def districts_list(request):
    from django.db.models import Count, Q

    districts = (
        District.objects.filter(is_deleted=False)
        .annotate(school_count=Count('schools', filter=Q(schools__customuser__role='school_admin')))
        .order_by('name')
    )
    total_schools = sum(d.school_count for d in districts)
    return render(
        request,
        'frontend/admin/districts.html',
        {
            'districts': districts,
            'total_schools': total_schools,
        },
    )


@login_required(login_url='login')
@superuser_required
def statistics(request):
    import datetime

    from books.models import Book, BookIssue, Category
    from django.db.models import Count, Q, Sum
    from django.utils import timezone

    today = timezone.now().date()
    period = request.GET.get('period', '30')
    try:
        period_days = int(period)
    except ValueError:
        period_days = 30

    # Generate date range
    days = []
    issue_counts = []
    return_counts = []
    user_counts = []
    for i in range(period_days - 1, -1, -1):
        day = today - datetime.timedelta(days=i)
        days.append(day.strftime('%d.%m'))
        issue_counts.append(BookIssue.objects.select_related('book', 'user').filter(issued_at__date=day).count())
        return_counts.append(BookIssue.objects.select_related('book', 'user').filter(returned_at__date=day).count())
        user_counts.append(CustomUser.objects.filter(date_joined__date=day).count())

    # Category distribution (books)
    cat_stats = Category.objects.filter(is_deleted=False).annotate(count=Count('book')).values('name', 'count')
    cat_labels = [item['name'] for item in cat_stats]
    cat_data = [item['count'] for item in cat_stats]

    # If no categories with books, show "Uncategorized"
    if not cat_labels:
        cat_labels = [_('Kategoriyasiz')]
        cat_data = [Book.objects.count()]

    # Summary stats
    total_books = Book.objects.count()
    total_students = CustomUser.objects.filter(role='student').count()
    total_teachers = CustomUser.objects.filter(role='teacher').count()
    total_schools = School.objects.count()
    issued_today = BookIssue.objects.select_related('book', 'user').filter(issued_at__date=today).count()
    returned_today = BookIssue.objects.select_related('book', 'user').filter(returned_at__date=today).count()
    active_loans = BookIssue.objects.select_related('book', 'user').filter(is_returned=False).count()
    total_xp = CustomUser.objects.aggregate(total=Sum('xp_points'))['total'] or 0

    # Most popular book
    top_book_data = BookIssue.objects.values('book__title').annotate(cnt=Count('id')).order_by('-cnt').first()
    top_book = top_book_data['book__title'] if top_book_data else '—'
    top_book_count = top_book_data['cnt'] if top_book_data else 0

    # Period filter for active schools/readers
    period_start = today - datetime.timedelta(days=period_days)

    # Top schools by active readers (within period)
    top_schools = (
        School.objects.annotate(
            active_count=Count(
                'customuser__bookissue',
                filter=Q(customuser__bookissue__issued_at__date__gte=period_start, customuser__role='student'),
            )
        )
        .filter(active_count__gt=0)
        .order_by('-active_count')[:5]
    )

    # Top individual readers (students with most books read in period)
    top_readers = (
        CustomUser.objects.filter(role='student', bookissue__issued_at__date__gte=period_start)
        .annotate(books_read=Count('bookissue'))
        .order_by('-books_read')[:10]
    )

    context = {
        'category_labels': cat_labels,
        'category_data': cat_data,
        'usage_labels': days,
        'issue_data': issue_counts,
        'return_data': return_counts,
        'user_data': user_counts,
        'period_days': period_days,
        'total_books': total_books,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_schools': total_schools,
        'issued_today': issued_today,
        'returned_today': returned_today,
        'active_loans': active_loans,
        'total_xp': total_xp,
        'top_book': top_book,
        'top_book_count': top_book_count,
        'top_schools': top_schools,
        'top_readers': top_readers,
    }
    return render(request, 'frontend/admin/statistics.html', context)


@login_required(login_url='login')
@superuser_required
def statistics_json(request):
    from books.models import Book, BookIssue
    from django.db.models import Sum
    from django.utils import timezone

    today = timezone.now().date()
    data = {
        'total_books': Book.objects.count(),
        'total_students': CustomUser.objects.filter(role='student').count(),
        'total_schools': School.objects.count(),
        'issued_today': BookIssue.objects.select_related('book', 'user').filter(issued_at__date=today).count(),
        'returned_today': BookIssue.objects.select_related('book', 'user').filter(returned_at__date=today).count(),
        'active_loans': BookIssue.objects.select_related('book', 'user').filter(is_returned=False).count(),
        'total_xp': CustomUser.objects.aggregate(total=Sum('xp_points'))['total'] or 0,
    }
    return JsonResponse(data)


@login_required(login_url='login')
@superuser_required
def create_stats_news(request):
    from datetime import timedelta

    from django.db.models import Count, Q
    from django.utils import timezone
    from schools.models import News, School

    today = timezone.now().date()
    period = request.GET.get('period', '30')
    try:
        period_days = int(period)
    except ValueError:
        period_days = 30
    period_start = today - timedelta(days=period_days)

    top_schools = (
        School.objects.annotate(
            active_count=Count(
                'customuser__bookissue',
                filter=Q(customuser__bookissue__issued_at__date__gte=period_start, customuser__role='student'),
            )
        )
        .filter(active_count__gt=0)
        .order_by('-active_count')[:5]
    )

    top_readers = (
        CustomUser.objects.filter(role='student', bookissue__issued_at__date__gte=period_start)
        .annotate(books_read=Count('bookissue'))
        .order_by('-books_read')[:10]
    )

    if not top_schools and not top_readers:
        messages.warning(request, _("Ma'lumotlar mavjud emas"))
        return redirect('frontend:statistics')

    News.objects.create(
        school=None,
        title=_("So'nggi {n} kun ichidagi faol maktablar va kitobxonlar").format(n=period_days),
        body='',
        is_published=True,
        template_key='weekly_active',
        template_data={
            'schools': [{'name': s.name, 'count': s.active_count} for s in top_schools] if top_schools else [],
            'readers': [{'username': r.username, 'grade': r.grade, 'count': r.books_read} for r in top_readers]
            if top_readers
            else [],
        },
    )
    messages.success(request, _('Yangilik muvaffaqiyatli yaratildi'))
    return redirect('frontend:admin_news_list')


@login_required(login_url='login')
@superuser_required
def system_logs(request):
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone
    from stats.models import ActionLog

    now = timezone.now()

    # Stats
    total_logs = ActionLog.objects.count()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = ActionLog.objects.filter(created_at__gte=today_start).count()
    week_count = ActionLog.objects.filter(created_at__gte=now - timedelta(days=7)).count()

    # Search
    q = request.GET.get('q', '').strip()
    action_filter = request.GET.get('action', '')
    period = request.GET.get('period', '')

    logs_qs = ActionLog.objects.all().select_related('user', 'user__school')

    if q:
        logs_qs = logs_qs.filter(Q(message__icontains=q) | Q(user__username__icontains=q) | Q(action_type__icontains=q))

    if action_filter:
        logs_qs = logs_qs.filter(action_type=action_filter)

    if period == 'today':
        logs_qs = logs_qs.filter(created_at__gte=today_start)
    elif period == 'week':
        logs_qs = logs_qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        logs_qs = logs_qs.filter(created_at__gte=now.replace(day=1))

    logs_qs = logs_qs.order_by('-created_at')

    from django.core.paginator import Paginator

    paginator = Paginator(logs_qs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    action_counts = {
        'ISSUE': ActionLog.objects.filter(action_type='ISSUE').count(),
        'RETURN': ActionLog.objects.filter(action_type='RETURN').count(),
        'CREATE': ActionLog.objects.filter(action_type='CREATE').count(),
        'LOGIN': ActionLog.objects.filter(action_type='LOGIN').count(),
    }

    return render(
        request,
        'frontend/admin/logs.html',
        {
            'logs': page_obj,
            'page_obj': page_obj,
            'query': q,
            'current_action': action_filter,
            'current_period': period,
            'today_count': today_count,
            'week_count': week_count,
            'total_logs': total_logs,
            'action_counts': action_counts,
        },
    )


@login_required(login_url='login')
@superuser_required
def all_users_list(request):
    from django.core.paginator import Paginator
    from django.utils import timezone

    role_filter = request.GET.get('role', '')

    users = CustomUser.objects.all().select_related('school').order_by('-date_joined')
    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_count = CustomUser.objects.count()
    student_count = CustomUser.objects.filter(role='student').count()
    teacher_count = CustomUser.objects.filter(role='teacher').count()
    school_admin_count = CustomUser.objects.filter(role='school_admin').count()
    active_today = CustomUser.objects.filter(last_login__date=timezone.now().date()).count()

    return render(
        request,
        'frontend/admin/all_users.html',
        {
            'users': page_obj,
            'page_obj': page_obj,
            'role_filter': role_filter,
            'total_count': total_count,
            'student_count': student_count,
            'teacher_count': teacher_count,
            'school_admin_count': school_admin_count,
            'active_today': active_today,
        },
    )


@login_required(login_url='login')
@superuser_required
def user_detail(request, pk):
    from books.models import BookIssue

    user = get_object_or_404(CustomUser, pk=pk)
    all_issues = BookIssue.objects.select_related('book', 'user').filter(user=user)
    issued_count = all_issues.filter(is_returned=False).count()
    total_read = all_issues.filter(is_returned=True).count()
    issues = all_issues.select_related('book').order_by('-issued_at')[:20]
    return render(
        request,
        'frontend/admin/user_detail.html',
        {
            'u': user,
            'issues': issues,
            'issued_count': issued_count,
            'total_read': total_read,
        },
    )


@login_required(login_url='login')
@superuser_required
def all_books_list(request):
    books = Book.objects.filter(is_deleted=False).select_related('school', 'category').order_by('-id')

    q = request.GET.get('q')
    if q:
        books = books.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(description__icontains=q))

    from django.core.paginator import Paginator

    paginator = Paginator(books, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request, 'frontend/admin/all_books.html', {'books': page_obj, 'page_obj': page_obj, 'current_query': q or ''}
    )


@login_required(login_url='login')
@superuser_required
def all_active_loans_list(request):
    active_loans = (
        BookIssue.objects.select_related('book', 'user')
        .filter(is_returned=False)
        .select_related('book__school', 'user')
        .order_by('-issued_at')
    )

    q = request.GET.get('q')
    if q:
        active_loans = active_loans.filter(
            Q(book__title__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )

    total_active = active_loans.count()

    loan_users = CustomUser.objects.filter(bookissue__is_returned=False).distinct()
    total_students = loan_users.filter(role='student').count()

    loan_books_qs = Book.objects.select_related('school', 'category').filter(bookissue__is_returned=False).distinct()
    unique_books = loan_books_qs.count()
    unique_schools = loan_books_qs.values('school').distinct().count()

    from django.core.paginator import Paginator

    paginator = Paginator(active_loans, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/admin/all_active_loans.html',
        {
            'active_loans': page_obj,
            'page_obj': page_obj,
            'total_active': total_active,
            'total_students': total_students,
            'unique_books': unique_books,
            'unique_schools': unique_schools,
            'current_query': q or '',
        },
    )


@login_required(login_url='login')
@superuser_required
def school_detail(request, pk):
    school = get_object_or_404(School, pk=pk)
    import re
    from collections import OrderedDict

    all_students = sorted(
        CustomUser.objects.filter(school=school, role='student'),
        key=lambda u: (
            int(re.match(r'(\d+)', u.grade or '99').group(1)) if re.match(r'(\d+)', u.grade or '') else 99,
            u.grade or '',
            u.last_name or '',
            u.first_name or '',
        ),
    )

    grades = OrderedDict()
    for s in all_students:
        g = s.grade or _("Sinfi ko'rsatilmagan")
        if g not in grades:
            grades[g] = []
        grades[g].append(s)

    def grade_sort_key(item):
        g = item[0]
        m = re.match(r'(\d+)', g)
        return (0, int(m.group(1))) if m else (1, g)

    grade_counts = sorted([(g, len(ss)) for g, ss in grades.items()], key=grade_sort_key)

    context = {
        'school': school,
        'student_count': len(all_students),
        'book_count': Book.objects.select_related('school', 'category').filter(school=school).count(),
        'issued_count': BookIssue.objects.select_related('book', 'user')
        .filter(book__school=school, is_returned=False)
        .count(),
        'school_admin': CustomUser.objects.filter(school=school, role='school_admin').first(),
        'grades': grades,
        'grade_counts': grade_counts,
        'books': Book.objects.select_related('school', 'category').filter(school=school).order_by('-id')[:20],
    }
    return render(request, 'frontend/admin/school_detail.html', context)


from frontend.forms import InstitutionForm, UnifiedSchoolForm


@login_required(login_url='login')
@superuser_required
def muassasa_add(request):
    if request.method == 'POST':
        form = InstitutionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('frontend:muassasalar_list')
    else:
        form = InstitutionForm()
    return render(request, 'frontend/admin/muassasa_form.html', {'form': form, 'title': _("Yangi muassasa qo'shish")})


@login_required(login_url='login')
@superuser_required
def muassasa_edit(request, pk):
    inst = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        form = InstitutionForm(request.POST, instance=inst)
        if form.is_valid():
            form.save()
            return redirect('frontend:muassasalar_list')
    else:
        form = InstitutionForm(instance=inst)
    return render(
        request, 'frontend/admin/muassasa_form.html', {'form': form, 'title': _("Muassasa ma'lumotlarini tahrirlash")}
    )


@login_required(login_url='login')
@superuser_required
def muassasa_delete(request, pk):
    inst = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        inst.delete()
        return redirect('frontend:muassasalar_list')
    return render(request, 'frontend/admin/confirm_delete.html', {'object': inst, 'type': _('muassasani')})


from frontend.forms import DistrictForm


@login_required(login_url='login')
@superuser_required
def district_add(request):
    if request.method == 'POST':
        form = DistrictForm(request.POST)
        if form.is_valid():
            district = form.save()

            # Bulk Create Schools
            bulk_count = form.cleaned_data.get('bulk_schools_count')
            if bulk_count:
                existing_count = district.schools.count()
                new_schools = []
                for i in range(1, bulk_count + 1):
                    new_schools.append(
                        School(
                            district=district,
                            name=f'{district.name} {existing_count + i}-sonli maktab',
                            address=f'{district.name} tumani',
                            contact='Aloqa kiritilmagan',
                        )
                    )
                School.objects.bulk_create(new_schools)

            return redirect('frontend:districts_list')
    else:
        form = DistrictForm()
    return render(request, 'frontend/admin/district_form.html', {'form': form, 'title': _("Yangi tuman qo'shish")})


@login_required(login_url='login')
@superuser_required
def district_edit(request, pk):
    district = get_object_or_404(District, pk=pk)
    if request.method == 'POST':
        form = DistrictForm(request.POST, instance=district)
        if form.is_valid():
            form.save()

            # Bulk Create Schools
            bulk_count = form.cleaned_data.get('bulk_schools_count')
            if bulk_count:
                existing_count = district.schools.count()
                new_schools = []
                for i in range(1, bulk_count + 1):
                    new_schools.append(
                        School(
                            district=district,
                            name=f'{district.name} {existing_count + i}-sonli maktab',
                            address=f'{district.name} tumani',
                            contact='Aloqa kiritilmagan',
                        )
                    )
                School.objects.bulk_create(new_schools)

            return redirect('frontend:districts_list')
    else:
        form = DistrictForm(instance=district)
    return render(
        request, 'frontend/admin/district_form.html', {'form': form, 'title': _("Tuman ma'lumotlarini tahrirlash")}
    )


@login_required(login_url='login')
@superuser_required
def district_delete(request, pk):
    district = get_object_or_404(District, pk=pk)
    if request.method == 'POST':
        district.delete()
        return redirect('frontend:districts_list')
    return render(request, 'frontend/admin/confirm_delete.html', {'object': district, 'type': _('tumanni')})


@login_required(login_url='login')
@superuser_required
def school_add(request):
    if request.method == 'POST':
        school_id = request.POST.get('existing_school_id')
        school_name = request.POST.get('name')
        district_id = request.POST.get('district')

        instance = None
        if school_id and school_id.isdigit():
            instance = School.objects.filter(pk=school_id).first()

        # Fallback: if no ID but name and district match an existing school, use that instance
        if not instance and school_name and district_id:
            instance = School.objects.filter(name=school_name, district_id=district_id).first()

        form = UnifiedSchoolForm(request.POST, instance=instance)
        if form.is_valid():
            school = form.save(commit=False)

            # If it's an existing school, check if it already has an admin
            if instance and CustomUser.objects.filter(school=instance, role='school_admin').exists():
                messages.error(request, f"'{instance.name}' maktabi uchun allaqachon admin biriktirilgan.")

                return redirect('frontend:school_add')

            school.save()

            # 2. Create Admin User
            admin_username = form.cleaned_data.get('admin_username')
            admin_password = form.cleaned_data.get('admin_password')

            if admin_username and admin_password:
                admin_user = CustomUser.objects.create_user(
                    username=admin_username,
                    password=admin_password,
                    role='school_admin',
                    school=school,
                    first_name='Admin',
                    last_name=school.name,
                )
                admin_user.save()

                # Log action
                from stats.models import ActionLog

                ActionLog.objects.create(
                    user=request.user,
                    action_type='CREATE',
                    message=_('Yangi maktab ({}) va uning admini ({}) yaratildi.').format(
                        school.name, admin_user.username
                    ),
                )
                messages.success(request, _('Maktab va admin yaratildi! Login: {}').format(admin_user.username))
            else:
                messages.success(request, _('Maktab yaratildi (admin biriktirilmadi).'))

            return redirect('frontend:schools_list')

    else:
        form = UnifiedSchoolForm()
    # Fetch Districts and Schools for the selection UI
    from django.db.models import Prefetch

    districts = District.objects.prefetch_related(
        Prefetch('schools', queryset=School.objects.all().order_by('name'))
    ).order_by('name')

    # Pass which schools already have admins
    schools_with_admins = CustomUser.objects.filter(role='school_admin').values_list('school_id', flat=True)

    return render(
        request,
        'frontend/admin/school_form.html',
        {
            'form': form,
            'title': _("Yangi maktab qo'shish"),
            'districts': districts,
            'schools_with_admins': list(schools_with_admins),
        },
    )


@login_required(login_url='login')
@superuser_required
def school_edit(request, pk):
    school = get_object_or_404(School, pk=pk)
    admin = CustomUser.objects.filter(school=school, role='school_admin').first()

    if request.method == 'POST':
        form = UnifiedSchoolForm(request.POST, instance=school, current_admin_id=admin.pk if admin else None)
        if form.is_valid():
            school = form.save()

            # Logic for updating or creating admin details
            if admin:
                admin_username = form.cleaned_data.get('admin_username')
                admin_password = form.cleaned_data.get('admin_password')

                updated = False
                if admin_username and admin.username != admin_username:
                    admin.username = admin_username
                    updated = True

                if admin_password:
                    admin.set_password(admin_password)
                    updated = True

                if updated:
                    admin.save()
                    messages.success(request, _("Maktab va admin ma'lumotlari yangilandi!"))
                else:
                    messages.success(request, _("Maktab ma'lumotlari yangilandi!"))
            else:
                # Create NEW admin
                admin_username = form.cleaned_data.get('admin_username')
                admin_password = form.cleaned_data.get('admin_password')

                if admin_username and admin_password:
                    new_admin = CustomUser.objects.create_user(
                        username=admin_username,
                        password=admin_password,
                        role='school_admin',
                        school=school,
                        first_name='Admin',
                        last_name=school.name,
                    )
                    new_admin.save()
                    messages.success(request, f'Maktab uchun yangi admin yaratildi! Login: {admin_username}')

            return redirect('frontend:schools_list')

    else:
        initial = {}
        if admin:
            initial['admin_username'] = admin.username

        form = UnifiedSchoolForm(instance=school, initial=initial, current_admin_id=admin.pk if admin else None)

    # Fetch Districts and Schools for consistent template behavior
    from django.db.models import Prefetch

    districts = District.objects.prefetch_related(
        Prefetch('schools', queryset=School.objects.all().order_by('name'))
    ).order_by('name')
    schools_with_admins = CustomUser.objects.filter(role='school_admin').values_list('school_id', flat=True)

    return render(
        request,
        'frontend/admin/school_form.html',
        {
            'form': form,
            'title': _("Maktab ma'lumotlarini tahrirlash"),
            'districts': districts,
            'schools_with_admins': list(schools_with_admins),
        },
    )


@login_required(login_url='login')
@superuser_required
def school_delete(request, pk):
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school.delete()
        return redirect('frontend:schools_list')
    return render(request, 'frontend/admin/confirm_delete.html', {'object': school, 'type': _('maktabni')})


from frontend.forms import SchoolAdminForm


@login_required(login_url='login')
@superuser_required
def admin_add(request):
    if request.method == 'POST':
        form = SchoolAdminForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'school_admin'

            # Use provided username or auto-generate
            admin_username = form.cleaned_data.get('admin_username')
            admin_password = form.cleaned_data.get('admin_password')

            if admin_username:
                admin.username = admin_username
            else:
                # Auto-generate smart username
                admin.username = f'temp_adm_{secrets.token_hex(4)}'
                admin.save()
                district_part = clean_name(
                    admin.school.district.name if admin.school and admin.school.district else 'no'
                )
                school_part = clean_name(admin.school.name if admin.school else 'school')
                admin.username = f'{district_part}_{school_part}_adm_{admin.id}'

            if admin_password:
                admin.set_password(admin_password)
            else:
                # Auto-generate password
                alphabet = string.ascii_letters + string.digits
                admin_password = ''.join(secrets.choice(alphabet) for i in range(12))
                admin.set_password(admin_password)

            admin.save()

            from django.contrib import messages

            messages.success(request, f'Admin yaratildi! Login: {admin.username}, Parol: {admin_password}')

            return redirect('frontend:all_users_list')
    else:
        form = SchoolAdminForm()
    return render(
        request,
        'frontend/admin/admin_edit.html',
        {'form': form, 'title': _("Yangi maktab admini qo'shish"), 'is_add': True},
    )


@login_required(login_url='login')
@superuser_required
def admin_edit(request, pk):
    admin = get_object_or_404(CustomUser, pk=pk, role='school_admin')

    if admin.school:
        return redirect('frontend:school_edit', pk=admin.school.pk)

    if request.method == 'POST':
        form = SchoolAdminForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            return redirect('frontend:all_users_list')
    else:
        form = SchoolAdminForm(instance=admin)
    return render(
        request,
        'frontend/admin/admin_edit.html',
        {'form': form, 'title': _("Admin ma'lumotlarini tahrirlash"), 'is_add': False},
    )


@login_required(login_url='login')
@superuser_required
def profile(request):
    from stats.models import ActionLog

    recent_activity = ActionLog.objects.filter(user=request.user).order_by('-created_at')[:10]

    return render(
        request,
        'frontend/admin/profile.html',
        {
            'recent_activity': recent_activity,
        },
    )


@login_required(login_url='login')
@superuser_required
def change_password(request):
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, _("Parolingiz muvaffaqiyatli o'zgartirildi!"))
            return redirect('frontend:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'frontend/admin/password_change.html', {'form': form})


# News Management
@login_required(login_url='login')
@superuser_required
def news_list(request):
    news = News.objects.filter(school__isnull=True).order_by('-created_at')
    published_count = news.filter(is_published=True).count()
    draft_count = news.filter(is_published=False).count()
    return render(
        request,
        'frontend/admin/news/list.html',
        {
            'news': news,
            'published_count': published_count,
            'draft_count': draft_count,
        },
    )


@login_required(login_url='login')
@superuser_required
def news_add(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.school = None
            news.save()
            return redirect('frontend:admin_news_list')
    else:
        form = NewsForm()
    return render(request, 'frontend/admin/news/form.html', {'form': form, 'title': _("Yangi xabar qo'shish")})


@login_required(login_url='login')
@superuser_required
def news_edit(request, pk):
    news = get_object_or_404(News, pk=pk, school__isnull=True)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('frontend:admin_news_list')
    else:
        form = NewsForm(instance=news)
    return render(request, 'frontend/admin/news/form.html', {'form': form, 'title': _('Xabarni tahrirlash')})


@login_required(login_url='login')
@superuser_required
def news_delete(request, pk):
    news = get_object_or_404(News, pk=pk, school__isnull=True)
    if request.method == 'POST':
        news.delete()
        return redirect('frontend:admin_news_list')
    return render(request, 'frontend/admin/confirm_delete.html', {'object': news, 'type': 'yangilikni'})


@login_required(login_url='login')
@superuser_required
def admin_global_search(request):
    from accounts.models import CustomUser
    from books.models import Book
    from django.utils.translation import gettext_lazy as _
    from schools.models import School

    q = request.GET.get('q', '').strip()
    results = []

    if len(q) >= 2:
        for s in School.objects.filter(name__icontains=q)[:5]:
            results.append(
                {
                    'title': s.name,
                    'type': _('School'),
                    'url': s.get_absolute_url()
                    if hasattr(s, 'get_absolute_url')
                    else '/admin/schools/' + str(s.pk) + '/',
                    'icon': 'fa-school',
                }
            )
        for u in CustomUser.objects.filter(username__icontains=q)[:5]:
            results.append(
                {
                    'title': u.get_full_name() or u.username,
                    'type': _('User'),
                    'url': '/admin/users/' + str(u.pk) + '/',
                    'icon': 'fa-user',
                }
            )
        for b in Book.objects.select_related('school', 'category').filter(title__icontains=q)[:5]:
            results.append(
                {
                    'title': b.title,
                    'type': _('Book'),
                    'url': '/admin/books/?q=' + b.title,
                    'icon': 'fa-book',
                }
            )

    return JsonResponse({'results': results})


@login_required(login_url='login')
@superuser_required
def admin_health(request):

    from django.core.cache import cache
    from django.db import connection

    health = {'db': False, 'cache': False, 'ws': False}
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            health['db'] = True
    except Exception:
        pass
    try:
        cache.set('_ health_check', 'ok', 5)
        health['cache'] = True
    except Exception:
        pass
    try:
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer:
            health['ws'] = True
    except Exception:
        pass
    return JsonResponse(health)
