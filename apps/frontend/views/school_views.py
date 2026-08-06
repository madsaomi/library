from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

school_admin_required = user_passes_test(
    lambda u: u.role == 'school_admin' and u.school is not None and u.school.is_active and not u.school.is_deleted,
    login_url='login',
)
import json
import logging
import secrets
import string

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

from accounts.models import CustomUser
from books.achievements import award_xp
from books.models import Book, BookIssue, BookRequest, Category, TextbookLoan
from schools.models import News
from stats.models import ActionLog

from frontend.forms import BookForm, NewsForm, StudentForm, TeacherForm


def clean_name(name):
    return ''.join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')


@login_required(login_url='login')
@school_admin_required
def dashboard(request):
    school = request.user.school
    context = {}
    if school:
        recent_activities = (
            BookIssue.objects.select_related('book', 'user').filter(book__school=school).order_by('-issued_at')[:10]
        )
        stats = (
            Book.objects.select_related('school', 'category')
            .filter(school=school)
            .aggregate(total_copies=Sum('total_count'), available_copies=Sum('available_count'))
        )
        from django.db.models import Count, Q
        from django.db.models.functions import TruncMonth

        # Base news filter: current school's news
        news_filter = Q(school=school)

        # Monthly issues for chart
        today = timezone.now()
        six_months_ago = today - timezone.timedelta(days=180)
        monthly_qs = (
            BookIssue.objects.select_related('book', 'user')
            .filter(book__school=school, issued_at__gte=six_months_ago)
            .annotate(month=TruncMonth('issued_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        month_labels = []
        monthly_data = []
        months_uz = [
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
        for entry in monthly_qs:
            if entry['month']:
                m = entry['month'].month - 1
                month_labels.append(months_uz[m] if m < len(months_uz) else str(entry['month'].month))
                monthly_data.append(entry['count'])

        context = {
            'student_count': CustomUser.objects.filter(school=school, role='student').count(),
            'book_count': Book.objects.select_related('school', 'category').filter(school=school).count(),
            'total_copies': stats['total_copies'] or 0,
            'available_copies': stats['available_copies'] or 0,
            'issued_count': BookIssue.objects.select_related('book', 'user')
            .filter(book__school=school, is_returned=False)
            .count(),
            'recent_activities': recent_activities,
            'news_count': News.objects.filter(news_filter, is_published=True).count(),
            'month_labels': month_labels,
            'monthly_data': monthly_data,
        }
    return render(request, 'frontend/school/dashboard.html', context)


@login_required(login_url='login')
@school_admin_required
def students_list(request):
    import re

    school = request.user.school
    query = request.GET.get('q')
    grade_filter = request.GET.get('grade', '')
    students = CustomUser.objects.filter(school=school, role='student')

    # Stats
    total_students = students.count()
    active_loans = BookIssue.objects.select_related('book', 'user').filter(book__school=school, is_returned=False)
    reading_students = active_loans.values('user').distinct().count()
    today = timezone.now().date()
    entered_today = students.filter(last_login__date=today).count()

    if query:
        from django.db.models import Q

        students = students.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(grade__icontains=query)
        )

    if grade_filter:
        students = students.filter(grade=grade_filter)

    # Get distinct grades in school for filter, sorted numerically
    all_grades_in_school = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades_in_school, key=sort_grade)

    # Sort students numerically by grade, then by name
    students = sorted(
        students,
        key=lambda u: (
            int(re.match(r'(\d+)', u.grade or '99').group(1)) if re.match(r'(\d+)', u.grade or '') else 99,
            u.grade or '',
            u.last_name or '',
            u.first_name or '',
        ),
    )

    from django.core.paginator import Paginator

    paginator = Paginator(students, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/students.html',
        {
            'students': page_obj,
            'page_obj': page_obj,
            'query': query,
            'total_students': total_students,
            'reading_students': reading_students,
            'entered_today': entered_today,
            'grades_list': grades_list,
            'selected_grade': grade_filter,
        },
    )


@login_required(login_url='login')
@school_admin_required
def students_promote(request):
    school = request.user.school

    # Get distinct grades for dropdowns
    all_grades = (
        CustomUser.objects.filter(school=school, role='student', is_archived=False)
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    import re

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades, key=sort_grade)

    if request.method == 'POST':
        from_grade = request.POST.get('from_grade', '').strip()
        to_grade = request.POST.get('to_grade', '').strip()
        if from_grade and to_grade:
            updated = CustomUser.objects.filter(
                school=school, role='student', is_archived=False, grade=from_grade
            ).update(grade=to_grade)
            messages.success(
                request,
                _("{count} ta o'quvchi {from_grade} sinfidan {to_grade} sinfiga o'tkazildi.").format(
                    count=updated, from_grade=from_grade, to_grade=to_grade
                ),
            )
            return redirect('frontend:students_list')
        else:
            messages.error(request, _('Sinflarni tanlang.'))

    return render(request, 'frontend/school/students_promote.html', {'grades_list': grades_list})


@login_required(login_url='login')
@school_admin_required
def students_archive(request):
    school = request.user.school

    all_grades = (
        CustomUser.objects.filter(school=school, role='student', is_archived=False)
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    import re

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades, key=sort_grade)

    if request.method == 'POST':
        grade = request.POST.get('grade', '').strip()
        if grade:
            updated = CustomUser.objects.filter(school=school, role='student', is_archived=False, grade=grade).update(
                is_archived=True
            )
            messages.success(
                request, _("{count} ta o'quvchi {grade} sinfidan arxivlandi.").format(count=updated, grade=grade)
            )
            return redirect('frontend:graduates_list')
        else:
            messages.error(request, _('Sinfni tanlang.'))

    return render(request, 'frontend/school/students_archive.html', {'grades_list': grades_list})


@login_required(login_url='login')
@school_admin_required
def teachers_list(request):
    school = request.user.school
    query = request.GET.get('q')
    teachers = CustomUser.objects.filter(school=school, role='teacher')

    total_teachers = teachers.count()
    today = timezone.now().date()
    entered_today = teachers.filter(last_login__date=today).count()

    if query:
        from django.db.models import Q

        teachers = teachers.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )

    teachers = teachers.order_by('last_name', 'first_name')

    from django.core.paginator import Paginator

    paginator = Paginator(teachers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/teachers.html',
        {
            'teachers': page_obj,
            'page_obj': page_obj,
            'query': query,
            'total_teachers': total_teachers,
            'entered_today': entered_today,
        },
    )


@login_required(login_url='login')
@school_admin_required
def books_list(request):
    school = request.user.school
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    no_cover = request.GET.get('no_cover')
    textbook = request.GET.get('textbook')

    from django.db.models import Sum

    all_books = Book.objects.select_related('school', 'category').filter(school=school)
    total_books = all_books.count()
    stats = all_books.aggregate(total_copies=Sum('total_count'), available_copies=Sum('available_count'))
    issued_count = (
        BookIssue.objects.select_related('book', 'user').filter(book__school=school, is_returned=False).count()
    )

    books = all_books

    if query:
        from books.search import search_books

        books = search_books(books, query)

    if category_id:
        books = books.filter(category_id=category_id)

    if no_cover == '1':
        from django.db.models import Q

        books = books.filter(Q(cover='') | Q(cover__isnull=True))

    if textbook == '1':
        books = books.filter(is_textbook=True)

    sort = request.GET.get('sort', 'title')
    sort_map = {
        'title': 'title',
        '-title': '-title',
        'borrow': '-borrow_count',
        'available': 'available_count',
        'newest': '-id',
    }
    books = books.order_by(sort_map.get(sort, 'title'))

    from books.models import Category

    categories = Category.objects.filter(is_deleted=False).order_by('name')

    from django.core.paginator import Paginator

    paginator = Paginator(books, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/books.html',
        {
            'books': page_obj,
            'page_obj': page_obj,
            'categories': categories,
            'query': query,
            'selected_category': category_id if category_id and category_id.isdigit() else None,
            'no_cover': no_cover == '1',
            'textbook_filter': textbook == '1',
            'sort': sort,
            'total_books': total_books,
            'total_copies': stats['total_copies'] or 0,
            'available_copies': stats['available_copies'] or 0,
            'issued_count': issued_count,
            'textbook_count': all_books.filter(is_textbook=True).count(),
        },
    )


@login_required(login_url='login')
@school_admin_required
def issued_books_list(request):
    school = request.user.school
    issues = (
        BookIssue.objects.select_related('book', 'user')
        .filter(book__school=school, is_returned=False)
        .select_related('book', 'user')
        .order_by('-issued_at')
    )

    total_issued = issues.count()
    unique_students = issues.values('user').distinct().count()
    unique_books = issues.values('book').distinct().count()

    from django.core.paginator import Paginator

    paginator = Paginator(issues, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/issued_books.html',
        {
            'issues': page_obj,
            'page_obj': page_obj,
            'total_issued': total_issued,
            'unique_students': unique_students,
            'unique_books': unique_books,
        },
    )


@login_required(login_url='login')
@school_admin_required
def history_list(request):
    school = request.user.school
    query = request.GET.get('q')

    all_history = BookIssue.objects.select_related('book', 'user').filter(book__school=school)
    total_actions = all_history.count()
    returned_count = all_history.filter(is_returned=True).count()
    issued_count = all_history.filter(is_returned=False).count()

    history = all_history.select_related('book', 'user').order_by('-issued_at')

    if query:
        from django.db.models import Q

        history = history.filter(
            Q(book__title__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        )

    from django.core.paginator import Paginator

    paginator = Paginator(history, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/history.html',
        {
            'history': page_obj,
            'page_obj': page_obj,
            'query': query,
            'total_actions': total_actions,
            'returned_count': returned_count,
            'issued_count': issued_count,
        },
    )


@login_required(login_url='login')
@school_admin_required
def news_list(request):
    school = request.user.school
    from django.db.models import Q

    query = Q(school=school)
    if request.user.role == 'school_admin' or request.user.is_superuser:
        query |= Q(school__isnull=True)

    all_news = News.objects.filter(query, is_published=True).order_by('-created_at')
    total_news = all_news.count()
    school_news = all_news.filter(school=school).count()
    global_news = all_news.filter(school__isnull=True).count()

    from django.core.paginator import Paginator

    paginator = Paginator(all_news, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/news.html',
        {
            'news': page_obj,
            'page_obj': page_obj,
            'total_news': total_news,
            'school_news': school_news,
            'global_news': global_news,
        },
    )


@login_required(login_url='login')
@school_admin_required
def qr_unified(request):
    school = request.user.school
    today = timezone.now().date()
    today_issues = (
        BookIssue.objects.select_related('book', 'user').filter(book__school=school, issued_at__date=today).count()
    )
    today_returns = (
        BookIssue.objects.select_related('book', 'user')
        .filter(book__school=school, returned_at__date=today, is_returned=True)
        .count()
    )
    total_scans = today_issues + today_returns
    return render(
        request,
        'frontend/school/qr_unified.html',
        {
            'today_scans': total_scans,
            'today_issues': today_issues,
            'today_returns': today_returns,
        },
    )


@login_required(login_url='login')
@school_admin_required
def process_qr_unified(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token', '')

            if token.startswith('REQ_'):
                return process_qr(request)
            elif token.startswith('RET_'):
                return process_receive_qr(request)
            elif token.startswith('CART_'):
                return process_cart_qr(request, token)
            elif token.startswith('RETCART_'):
                return process_cart_return_qr(request, token)
            elif token.startswith('BOOK_'):
                return qr_book_scanned(request, token)
            elif token.startswith('STU_'):
                return qr_student_scanned(request, token)
            else:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': _("Noma'lum QR-kod turi. Iltimos, kitob berish yoki qaytarish kodini skanerlang."),
                    }
                )
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Noto'g'ri so'rov formati"})
        except Exception as e:
            logger.error(f'process_qr_unified error: {e}', exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('Tizimda xatolik yuz berdi')})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


def _reset_pending_qr(request):
    request.session.pop('qr_pending_book_id', None)
    request.session.pop('qr_pending_student_id', None)


def _pair_result(request, book, student):
    """Auto issue or auto return based on whether the student already holds this book."""
    from accounts.utils import verify_dynamic_token  # noqa: F401
    from django.db.models import F
    from stats.models import ActionLog

    active = (
        BookIssue.objects.select_related('book', 'user')
        .filter(book=book, user=student, is_returned=False, is_deleted=False)
        .first()
    )

    if active:
        # AUTO RETURN
        active.is_returned = True
        active.returned_at = timezone.now()
        active.save(update_fields=['is_returned', 'returned_at'])

        book.available_count = F('available_count') + 1
        book.save(update_fields=['available_count'])
        book.refresh_from_db()

        request_obj = (
            BookRequest.objects.select_related('book', 'user')
            .filter(book=book, user=student, status='approved')
            .first()
        )
        if request_obj:
            request_obj.status = 'completed'
            request_obj.save(update_fields=['status'])

        from books.models import BookWaitlist

        next_in_queue = BookWaitlist.objects.filter(book=book, is_notified=False).first()
        if next_in_queue:
            next_in_queue.is_notified = True
            next_in_queue.save(update_fields=['is_notified'])
            from notifications.utils import notify_user

            notify_user(
                next_in_queue.user,
                _('Kitob mavjud!'),
                _('"{title}" kitobi bo\'shadi. Navbat sizda!').format(title=book.title),
                url=reverse('frontend:book_detail', args=[book.pk]),
            )

        ActionLog.objects.create(
            user=request.user,
            action_type='RETURN',
            message=_("{}dan '{}' kitobi qabul qilindi").format(student.username, book.title),
        )

        xp_result = award_xp(student, 'return')
        from notifications.utils import notify_user

        notify_user(
            student,
            _('Kitob qaytarildi'),
            _('"{title}" kitobi qabul qilindi').format(title=book.title),
            url=reverse('frontend:my_books'),
        )

        _reset_pending_qr(request)
        return JsonResponse(
            {
                'status': 'success',
                'action': 'return',
                'message': _('Qaytarildi: "{title}"').format(title=book.title),
                'student': f'{student.first_name} {student.last_name}',
                'grade': student.grade or '',
                'xp_earned': xp_result['xp_earned'],
                'leveled_up': xp_result['leveled_up'],
                'new_level': xp_result['new_level'],
                'new_achievements': xp_result['new_achievements'],
            }
        )

    # AUTO ISSUE
    if student.role == 'student' and book.is_textbook:
        return JsonResponse(
            {
                'status': 'error',
                'message': _("Darsliklarni o'quvchilar ololmaydi. Darsliklar o'quv yili boshida tarqatiladi."),
            }
        )

    if book.available_count <= 0:
        return JsonResponse({'status': 'error', 'message': _('Kitob qolmagan: "{title}"').format(title=book.title)})

    BookIssue.objects.create(book=book, user=student)

    book.available_count = F('available_count') - 1
    book.borrow_count = F('borrow_count') + 1
    book.save(update_fields=['available_count', 'borrow_count'])
    book.refresh_from_db()

    ActionLog.objects.create(
        user=request.user,
        action_type='ISSUE',
        message=_("{}ga '{}' kitobi berildi").format(student.username, book.title),
    )

    xp_result = award_xp(student, 'borrow', book=book)
    from notifications.utils import notify_user

    notify_user(
        student,
        _('Kitob berildi'),
        _('"{title}" kitobi sizga berildi').format(title=book.title),
        url=reverse('frontend:my_books'),
    )

    _reset_pending_qr(request)
    return JsonResponse(
        {
            'status': 'success',
            'action': 'issue',
            'message': _('Berildi: "{title}"').format(title=book.title),
            'student': f'{student.first_name} {student.last_name}',
            'grade': student.grade or '',
            'xp_earned': xp_result['xp_earned'],
            'lucky_bonus': xp_result['lucky_bonus'],
            'leveled_up': xp_result['leveled_up'],
            'new_level': xp_result['new_level'],
            'new_achievements': xp_result['new_achievements'],
        }
    )


@login_required(login_url='login')
@school_admin_required
def qr_book_scanned(request, token):
    """Handle a scanned static BOOK_ token. Pairs with a pending student for auto action."""
    from accounts.utils import verify_static_token

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

    book_id = verify_static_token(token, 'BOOK')
    if not book_id:
        return JsonResponse({'status': 'error', 'message': _("Noto'g'ri kitob QR-kodi")})

    book = (
        Book.objects.select_related('school', 'category')
        .filter(id=book_id, school=request.user.school, is_deleted=False)
        .first()
    )
    if not book:
        return JsonResponse({'status': 'error', 'message': _('Kitob topilmadi yoki boshqa maktabga tegishli')})

    request.session['qr_pending_book_id'] = book.id

    student_id = request.session.get('qr_pending_student_id')
    if student_id:
        student = (
            CustomUser.objects.filter(id=student_id, school=request.user.school, role='student')
            .exclude(is_archived=True)
            .first()
        )
        if student:
            return _pair_result(request, book, student)

    return JsonResponse(
        {
            'status': 'info',
            'pending': 'book',
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author or '',
                'category': book.category.name if book.category else '',
                'available': book.available_count,
                'total': book.total_count,
                'textbook': book.is_textbook,
                'grade': book.grade,
            },
            'message': _(
                'Kitob: "{title}" (mavjud {available}/{total}). Endi o\'quvchi QR-kodini skanerlang yoki qidiring.'
            ).format(title=book.title, available=book.available_count, total=book.total_count),
        }
    )


@login_required(login_url='login')
@school_admin_required
def qr_student_scanned(request, token):
    """Handle a scanned static STU_ token. Pairs with a pending book for auto action."""
    from accounts.utils import verify_static_token

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

    student_id = verify_static_token(token, 'STU')
    if not student_id:
        return JsonResponse({'status': 'error', 'message': _("Noto'g'ri o'quvchi QR-kodi")})

    student = (
        CustomUser.objects.filter(id=student_id, school=request.user.school, role='student')
        .exclude(is_archived=True)
        .first()
    )
    if not student:
        return JsonResponse({'status': 'error', 'message': _("O'quvchi topilmadi yoki boshqa maktabga tegishli")})

    request.session['qr_pending_student_id'] = student.id

    book_id = request.session.get('qr_pending_book_id')
    if book_id:
        book = (
            Book.objects.select_related('school', 'category')
            .filter(id=book_id, school=request.user.school, is_deleted=False)
            .first()
        )
        if book:
            return _pair_result(request, book, student)

    return JsonResponse(
        {
            'status': 'info',
            'pending': 'student',
            'student': {
                'id': student.id,
                'name': f'{student.first_name} {student.last_name}',
                'username': student.username,
                'grade': student.grade or '',
            },
            'message': _("O'quvchi: {name} ({grade}). Endi kitob QR-kodini skanerlang.").format(
                name=f'{student.first_name} {student.last_name}'.strip(), grade=student.grade or ''
            ),
        }
    )


@login_required(login_url='login')
@school_admin_required
def qr_search_students(request):
    """JSON search endpoint for the scanner's student-picker fallback."""
    q = request.GET.get('q', '').strip()
    school = request.user.school
    students = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(is_archived=True)
        .order_by('last_name', 'first_name')
    )
    if q:
        students = students.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q))
    students = students[:20]
    return JsonResponse(
        {
            'status': 'success',
            'students': [
                {
                    'id': s.id,
                    'name': f'{s.first_name} {s.last_name}'.strip(),
                    'username': s.username,
                    'grade': s.grade or '',
                }
                for s in students
            ],
        }
    )


@login_required(login_url='login')
@school_admin_required
def qr_pick_student(request):
    """Set the pending student from a manual pick, then pair with pending book if any."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'status': 'error', 'message': "Noto'g'ri so'rov"})

    student = (
        CustomUser.objects.filter(id=student_id, school=request.user.school, role='student')
        .exclude(is_archived=True)
        .first()
    )
    if not student:
        return JsonResponse({'status': 'error', 'message': _("O'quvchi topilmadi")})

    request.session['qr_pending_student_id'] = student.id

    book_id = request.session.get('qr_pending_book_id')
    if book_id:
        book = (
            Book.objects.select_related('school', 'category')
            .filter(id=book_id, school=request.user.school, is_deleted=False)
            .first()
        )
        if book:
            return _pair_result(request, book, student)

    return JsonResponse(
        {
            'status': 'info',
            'pending': 'student',
            'student': {
                'id': student.id,
                'name': f'{student.first_name} {student.last_name}',
                'grade': student.grade or '',
            },
            'message': _("O'quvchi tanlandi: {name} ({grade}). Endi kitob QR-kodini skanerlang.").format(
                name=f'{student.first_name} {student.last_name}'.strip(), grade=student.grade or ''
            ),
        }
    )


@login_required(login_url='login')
@school_admin_required
def qr_clear_pending(request):
    """Reset any pending book/student pairing."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})
    _reset_pending_qr(request)
    return JsonResponse({'status': 'success', 'message': _("Boshlang'ich holatga qaytarildi")})


@login_required(login_url='login')
@school_admin_required
def qr_state(request):
    """Return current pending pairing state (for page load / refresh)."""
    book_id = request.session.get('qr_pending_book_id')
    student_id = request.session.get('qr_pending_student_id')
    data = {'status': 'success', 'book': None, 'student': None}

    if book_id:
        book = Book.objects.select_related('category').filter(id=book_id, school=request.user.school).first()
        if book:
            data['book'] = {
                'id': book.id,
                'title': book.title,
                'author': book.author or '',
                'available': book.available_count,
                'total': book.total_count,
            }
    if student_id:
        student = CustomUser.objects.filter(id=student_id, school=request.user.school, role='student').first()
        if student:
            data['student'] = {
                'id': student.id,
                'name': f'{student.first_name} {student.last_name}',
                'grade': student.grade or '',
            }
    return JsonResponse(data)


def _qr_image_response(token):
    """Generate and return a QR PNG image for the given token."""
    import io

    import qrcode as qrcode_lib

    qr = qrcode_lib.QRCode(
        version=1,
        error_correction=qrcode_lib.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    from django.http import HttpResponse

    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required(login_url='login')
@school_admin_required
def book_qr_image(request, pk):
    """Render the printable static QR for a book."""
    from accounts.utils import generate_static_token

    book = (
        Book.objects.select_related('school', 'category')
        .filter(id=pk, school=request.user.school, is_deleted=False)
        .first()
    )
    if not book:
        return JsonResponse({'status': 'error', 'message': _('Kitob topilmadi')}, status=404)
    token = generate_static_token('BOOK', book.id)
    return _qr_image_response(token)


@login_required(login_url='login')
@school_admin_required
def book_qr_label(request, pk):
    """Printable label (sticker) for a book: title, author, category + static QR."""
    book = (
        Book.objects.select_related('school', 'category')
        .filter(id=pk, school=request.user.school, is_deleted=False)
        .first()
    )
    if not book:
        from django.http import Http404

        raise Http404
    return render(request, 'frontend/school/book_qr_label.html', {'book': book})


@login_required(login_url='login')
@school_admin_required
def qr_labels_batch(request):
    """Printable batch of QR labels for all books and/or students."""
    school = request.user.school
    kind = request.GET.get('kind', 'books')

    if kind == 'students':
        items = (
            CustomUser.objects.filter(school=school, role='student')
            .exclude(is_archived=True)
            .order_by('last_name', 'first_name')
        )
    else:
        items = (
            Book.objects.select_related('school', 'category').filter(school=school, is_deleted=False).order_by('title')
        )

    return render(
        request,
        'frontend/school/qr_labels_batch.html',
        {'kind': kind, 'items': items},
    )


@login_required(login_url='login')
@school_admin_required
def student_qr_image(request, pk):
    """Render the printable static QR for a student."""
    from accounts.utils import generate_static_token

    student = (
        CustomUser.objects.filter(id=pk, school=request.user.school, role='student').exclude(is_archived=True).first()
    )
    if not student:
        return JsonResponse({'status': 'error', 'message': _("O'quvchi topilmadi")}, status=404)
    token = generate_static_token('STU', student.id)
    return _qr_image_response(token)


@login_required(login_url='login')
@school_admin_required
def student_card(request, pk):
    """Printable library card for a student: name, grade, school + static QR."""
    student = (
        CustomUser.objects.filter(id=pk, school=request.user.school, role='student')
        .exclude(is_archived=True)
        .select_related('school', 'school__district')
        .first()
    )
    if not student:
        from django.http import Http404

        raise Http404
    return render(request, 'frontend/school/student_card.html', {'student': student})


@login_required(login_url='login')
@school_admin_required
def process_qr(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')

            from accounts.utils import verify_dynamic_token

            request_id = verify_dynamic_token(token, 'REQ')

            if not request_id:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': _(
                            "Eski yoki noto'g'ri QR-kod. Iltimos, o'quvchi telefonida kodni yangilasini kutib turing."
                        ),
                    }
                )

            try:
                request_obj = BookRequest.objects.get(id=request_id, status='pending')
            except BookRequest.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': _('Bron topilmadi yoki allaqachon tasdiqlangan')})

            if request_obj.user.school != request.user.school:
                return JsonResponse(
                    {'status': 'error', 'message': _("Xatolik: Ushbu o'quvchi boshqa maktabga tegishli!")}
                )

            # Students cannot borrow textbooks
            if request_obj.user.role == 'student' and request_obj.book.is_textbook:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': _("Darsliklarni o'quvchilar ololmaydi. Darsliklar o'quv yili boshida tarqatiladi."),
                    }
                )

            from django.db.models import F

            book = request_obj.book
            if book.available_count <= 0:
                return JsonResponse({'status': 'error', 'message': _('Kitob qolmagan')})

            request_obj.status = 'approved'
            request_obj.save()

            BookIssue.objects.create(book=book, user=request_obj.user)

            book.available_count = F('available_count') - 1
            book.borrow_count = F('borrow_count') + 1
            book.save()
            book.refresh_from_db()

            # Notify the user
            from notifications.utils import notify_user

            notify_user(
                request_obj.user,
                _('Kitob tasdiqlandi'),
                _('"{title}" kitobi sizga berildi').format(title=book.title),
                url=reverse('frontend:my_books'),
            )

            ActionLog.objects.create(
                user=request.user,
                action_type='ISSUE',
                message=_("{}ga '{}' kitobi berildi").format(request_obj.user.username, book.title),
            )

            xp_result = award_xp(request_obj.user, 'borrow', book=book)

            return JsonResponse(
                {
                    'status': 'success',
                    'message': _('Kitob muvaffaqiyatli berildi: {}').format(book.title),
                    'student': f'{request_obj.user.first_name} {request_obj.user.last_name}',
                    'xp_earned': xp_result['xp_earned'],
                    'lucky_bonus': xp_result['lucky_bonus'],
                    'leveled_up': xp_result['leveled_up'],
                    'new_level': xp_result['new_level'],
                    'new_achievements': xp_result['new_achievements'],
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Noto'g'ri so'rov formati"})
        except Exception as e:
            logger.error(f'process_qr error: {e}', exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('Tizimda xatolik yuz berdi')})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


@login_required(login_url='login')
@school_admin_required
def process_receive_qr(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')

            from accounts.utils import verify_dynamic_token

            issue_id = verify_dynamic_token(token, 'RET')

            if not issue_id:
                return JsonResponse({'status': 'error', 'message': _("Eski yoki noto'g'ri QR-kod")})

            from books.models import BookIssue
            from django.db.models import F
            from django.utils import timezone
            from stats.models import ActionLog

            try:
                issue = BookIssue.objects.get(id=issue_id, is_returned=False)
            except BookIssue.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': _('Ushbu kitob uchun faol topshirish topilmadi')})

            if issue.user.school != request.user.school:
                return JsonResponse(
                    {'status': 'error', 'message': _("Xatolik: Ushbu o'quvchi boshqa maktabga tegishli!")}
                )

            book = issue.book
            user = issue.user

            issue.is_returned = True
            issue.returned_at = timezone.now()
            issue.save()

            book.available_count = F('available_count') + 1
            book.save()
            book.refresh_from_db()

            request_obj = (
                BookRequest.objects.select_related('book', 'user')
                .filter(book=book, user=user, status='approved')
                .first()
            )
            if request_obj:
                request_obj.status = 'completed'
                request_obj.save()

            # Notify next person in waitlist
            from books.models import BookWaitlist

            next_in_queue = BookWaitlist.objects.filter(book=book, is_notified=False).first()
            if next_in_queue:
                next_in_queue.is_notified = True
                next_in_queue.save()
                from notifications.utils import notify_user

                notify_user(
                    next_in_queue.user,
                    _('Kitob mavjud!'),
                    _('"{title}" kitobi bo\'shadi. Navbat sizda!').format(title=book.title),
                    url=reverse('frontend:book_detail', args=[book.pk]),
                )

            ActionLog.objects.create(
                user=request.user,
                action_type='RETURN',
                message=_("{}dan '{}' kitobi qabul qilindi").format(user.username, book.title),
            )

            xp_result = award_xp(user, 'return')

            return JsonResponse(
                {
                    'status': 'success',
                    'message': _('Kitob muvaffaqiyatli qabul qilindi: {}').format(book.title),
                    'student': f'{user.first_name} {user.last_name}',
                    'xp_earned': xp_result['xp_earned'],
                    'lucky_bonus': False,
                    'leveled_up': xp_result['leveled_up'],
                    'new_level': xp_result['new_level'],
                    'new_achievements': xp_result['new_achievements'],
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Noto'g'ri so'rov formati"})
        except Exception:
            return JsonResponse({'status': 'error', 'message': _('Tizimda xatolik yuz berdi')})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


@login_required(login_url='login')
@school_admin_required
def process_cart_qr(request, token):
    from books.models import BookCart, BookCartItem
    from django.db import transaction
    from django.db.models import F

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

    cart = (
        BookCart.objects.select_related('user')
        .filter(
            qr_token=token,
            school=request.user.school,
            status='pending',
            purpose='borrow',
            is_deleted=False,
        )
        .first()
    )
    if not cart:
        return JsonResponse({'status': 'error', 'message': _('Savat topilmadi yoki allaqachon ishlatilgan')})

    items = list(BookCartItem.objects.filter(cart=cart, is_deleted=False).select_related('book'))
    if not items:
        return JsonResponse({'status': 'error', 'message': _("Savat bo'sh")})

    student = cart.user
    issued_titles = []
    skipped = []

    with transaction.atomic():
        for item in items:
            book = Book.objects.select_for_update().filter(pk=item.book_id).first()
            if not book or book.is_deleted or book.school != request.user.school:
                skipped.append(item.book.title)
                continue
            if student.role == 'student' and book.is_textbook:
                skipped.append(item.book.title)
                continue
            if book.available_count < 1:
                skipped.append(item.book.title)
                continue
            BookIssue.objects.create(book=book, user=student)
            Book.objects.filter(pk=book.pk).update(
                available_count=F('available_count') - 1,
                borrow_count=F('borrow_count') + 1,
            )
            award_xp(student, 'borrow', book=book)
            issued_titles.append(book.title)

        cart.status = 'borrowed'
        cart.borrowed_at = timezone.now()
        cart.save(update_fields=['status', 'borrowed_at'])

    if not issued_titles:
        return JsonResponse(
            {
                'status': 'error',
                'message': _('Hech qanday kitob berilmadi: {skipped}').format(skipped=', '.join(skipped)),
            }
        )

    from notifications.utils import notify_user

    notify_user(
        student,
        _('Kitoblar tasdiqlandi'),
        _('Sizga {count} ta kitob berildi').format(count=len(issued_titles)),
        url=reverse('frontend:my_books'),
    )
    ActionLog.objects.create(
        user=request.user,
        action_type='ISSUE',
        message=_('{n}ga {count} ta kitob berildi (savat)').format(n=student.username, count=len(issued_titles)),
    )

    message = _('Berildi: {issued}').format(issued=', '.join(issued_titles))
    if skipped:
        message += ' | ' + _("O'tkazib yuborildi: {skipped}").format(skipped=', '.join(skipped))
    return JsonResponse(
        {'status': 'success', 'message': message, 'student': f'{student.first_name} {student.last_name}'}
    )


@login_required(login_url='login')
@school_admin_required
def process_cart_return_qr(request, token):
    from books.models import BookCart, BookCartItem
    from django.db.models import F

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

    cart = (
        BookCart.objects.select_related('user')
        .filter(
            qr_token=token,
            school=request.user.school,
            status='pending',
            purpose='return',
            is_deleted=False,
        )
        .first()
    )
    if not cart:
        return JsonResponse({'status': 'error', 'message': _('Savat topilmadi yoki allaqachon ishlatilgan')})

    items = list(BookCartItem.objects.filter(cart=cart, is_deleted=False).select_related('book'))
    if not items:
        return JsonResponse({'status': 'error', 'message': _("Savat bo'sh")})

    student = cart.user
    returned_titles = []
    skipped = []

    for item in items:
        book = item.book
        issue = BookIssue.objects.filter(book=book, user=student, is_returned=False).first()
        if not issue:
            skipped.append(book.title)
            continue
        issue.is_returned = True
        issue.returned_at = timezone.now()
        issue.save(update_fields=['is_returned', 'returned_at'])
        Book.objects.filter(pk=book.pk).update(available_count=F('available_count') + 1)
        if not issue.xp_awarded:
            award_xp(student, 'return')
            issue.xp_awarded = True
            issue.save(update_fields=['xp_awarded'])
        request_obj = BookRequest.objects.filter(book=book, user=student, status='approved').first()
        if request_obj:
            request_obj.status = 'completed'
            request_obj.save(update_fields=['status'])
        from books.models import BookWaitlist

        next_in_queue = BookWaitlist.objects.filter(book=book, is_notified=False).first()
        if next_in_queue:
            next_in_queue.is_notified = True
            next_in_queue.save()
            from notifications.utils import notify_user

            notify_user(
                next_in_queue.user,
                _('Kitob mavjud!'),
                _('"{title}" kitobi bo\'shadi. Navbat sizda!').format(title=book.title),
                url=reverse('frontend:book_detail', args=[book.pk]),
            )
        returned_titles.append(book.title)

    cart.status = 'returned'
    cart.returned_at = timezone.now()
    cart.save(update_fields=['status', 'returned_at'])

    if returned_titles:
        ActionLog.objects.create(
            user=request.user,
            action_type='RETURN',
            message=_('{n}dan {count} ta kitob qabul qilindi (savat)').format(
                n=student.username, count=len(returned_titles)
            ),
        )

    if not returned_titles:
        return JsonResponse({'status': 'error', 'message': _('Hech qanday kitob qabul qilinmadi')})

    message = _('Qabul qilindi: {returned}').format(returned=', '.join(returned_titles))
    if skipped:
        message += ' | ' + _('Topilmadi: {skipped}').format(skipped=', '.join(skipped))
    return JsonResponse(
        {'status': 'success', 'message': message, 'student': f'{student.first_name} {student.last_name}'}
    )


@login_required(login_url='login')
@school_admin_required
def book_add(request):
    if request.method == 'POST':
        from books.models import Category

        titles = request.POST.getlist('title')
        authors = request.POST.getlist('author')
        descriptions = request.POST.getlist('description')
        total_counts = request.POST.getlist('total_count')
        available_counts = request.POST.getlist('available_count')
        grades = request.POST.getlist('grade')
        category_names = request.POST.getlist('category_name')
        subjects = request.POST.getlist('subject')

        created = 0
        skipped = []
        for i in range(len(titles)):
            title = titles[i].strip()
            if not title:
                continue

            # Check for duplicate title within the same school
            if Book.objects.filter(school=request.user.school, title__iexact=title, is_deleted=False).exists():
                skipped.append(f'"{title}" — kitob allaqachon mavjud')
                continue

            # Get cover by dynamic name cover_{idx} — idx is 1-based bookCount
            # We look through request.FILES to find cover at index i
            cover_key = None
            for key in request.FILES:
                if key.startswith('cover_'):
                    try:
                        key_idx = int(key.split('_', 1)[1])
                        if key_idx == i + 1:
                            cover_key = key
                            break
                    except (ValueError, IndexError):
                        pass

            textbook_key = f'is_textbook_{i + 1}'

            book = Book(
                title=title,
                author=authors[i].strip() if i < len(authors) else '',
                description=descriptions[i].strip() if i < len(descriptions) else '',
                total_count=int(total_counts[i]) if i < len(total_counts) and total_counts[i].strip() else 1,
                available_count=int(available_counts[i])
                if i < len(available_counts) and available_counts[i].strip()
                else 1,
                is_textbook=textbook_key in request.POST,
                subject=subjects[i].strip() if i < len(subjects) else '',
                school=request.user.school,
            )

            grade_val = grades[i].strip() if i < len(grades) else ''
            if grade_val.isdigit():
                book.grade = int(grade_val)

            if cover_key and cover_key in request.FILES:
                book.cover = request.FILES[cover_key]

            book.save()

            cat_name = category_names[i].strip() if i < len(category_names) else ''
            if cat_name:
                category, _created = Category.objects.get_or_create(name=cat_name)
                book.category = category
                book.save(update_fields=['category'])

            created += 1

        if created:
            messages.success(request, _(f"{created} ta kitob muvaffaqiyatli qo'shildi!"))
        else:
            messages.error(request, _("Hech qanday kitob qo'shilmadi."))
        if skipped:
            for msg in skipped:
                messages.warning(request, msg)
        return redirect('frontend:school_books_list')
    else:
        form = BookForm()
    return render(request, 'frontend/school/book_form.html', {'form': form, 'title': _("Ko'p kitob qo'shish")})


@login_required(login_url='login')
@school_admin_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            return redirect('frontend:school_books_list')
    else:
        form = BookForm(instance=book)
    return render(request, 'frontend/school/book_form.html', {'form': form, 'title': _('Kitobni tahrirlash')})


@login_required(login_url='login')
@school_admin_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        book.delete()
        return redirect('frontend:school_books_list')
    return render(request, 'frontend/school/confirm_delete.html', {'object': book, 'type': _('kitobni')})


@login_required(login_url='login')
@school_admin_required
def student_add(request):
    import datetime

    if request.method == 'POST':
        first_names = request.POST.getlist('first_name')
        last_names = request.POST.getlist('last_name')
        patronymics = request.POST.getlist('patronymic')
        birth_dates = request.POST.getlist('birth_date')

        # Global grade for all these students
        g_num = request.POST.get('grade_number', '')
        g_let = request.POST.get('grade_letter', '')

        created_students = []

        def translit_cyrillic(text):
            if not text:
                return ''
            mapping = {
                'а': 'a',
                'б': 'b',
                'в': 'v',
                'г': 'g',
                'д': 'd',
                'е': 'e',
                'ё': 'yo',
                'ж': 'zh',
                'з': 'z',
                'и': 'i',
                'й': 'y',
                'к': 'k',
                'л': 'l',
                'м': 'm',
                'н': 'n',
                'о': 'o',
                'п': 'p',
                'р': 'r',
                'с': 's',
                'т': 't',
                'у': 'u',
                'ф': 'f',
                'х': 'x',
                'ц': 'ts',
                'ч': 'ch',
                'ш': 'sh',
                'щ': 'shch',
                'ъ': '',
                'ы': 'y',
                'ь': '',
                'э': 'e',
                'ю': 'yu',
                'я': 'ya',
                'ў': 'o',
                'қ': 'q',
                'ғ': 'g',
                'ҳ': 'x',
            }
            return ''.join(mapping.get(c, c) for c in text.lower()).replace(' ', '')

        for i in range(len(first_names)):
            f_name = first_names[i].strip()
            l_name = last_names[i].strip()
            if not f_name or not l_name:
                continue

            patronymic = patronymics[i].strip() if i < len(patronymics) else ''
            b_date_str = birth_dates[i] if i < len(birth_dates) else ''

            full_first = f'{f_name} {patronymic}'.strip() if patronymic else f_name

            # Create user instance
            student = CustomUser(
                first_name=full_first,
                last_name=l_name,
                role='student',
                school=request.user.school,
                grade=f'{g_num}-{g_let}' if g_num and g_let else None,
            )

            if b_date_str:
                try:
                    student.birth_date = datetime.datetime.strptime(b_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Temporary username
            student.username = f'temp_{secrets.token_hex(4)}'
            student.save()

            # Generate Login and Password
            first_lat = translit_cyrillic(f_name)
            last_lat = translit_cyrillic(l_name)

            base_username = clean_name(f'{first_lat}_{last_lat}')
            if not base_username:
                base_username = f'student_{student.id}'

            username = base_username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f'{base_username}_{counter}'
                counter += 1

            student.username = username

            if first_lat and last_lat:
                password = f'{first_lat.capitalize()}{last_lat.capitalize()}!'
            else:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(12))

            student.set_password(password)
            student.raw_password = password
            student.save()

            created_students.append(student.id)

        if created_students:
            request.session['bulk_created_students'] = created_students
            messages.success(request, _(f"{len(created_students)} ta o'quvchi muvaffaqiyatli qo'shildi!"))
            return redirect('frontend:bulk_credentials_prompt')
        else:
            messages.error(request, _("Hech qanday o'quvchi qo'shilmadi."))
            return redirect('frontend:student_add')

    else:
        form = StudentForm()
    return render(
        request, 'frontend/school/student_form.html', {'form': form, 'title': _("Ko'p o'quvchilarni qo'shish")}
    )


@login_required(login_url='login')
@school_admin_required
def bulk_credentials_prompt(request):
    student_ids = request.session.get('bulk_created_students', [])
    if not student_ids:
        return redirect('frontend:students_list')

    students = CustomUser.objects.filter(id__in=student_ids)
    return render(request, 'frontend/school/bulk_credentials_prompt.html', {'students': students})


@login_required(login_url='login')
@school_admin_required
def download_bulk_credentials_csv(request):
    import csv

    from django.http import HttpResponse

    student_ids = request.session.get('bulk_created_students', [])
    if not student_ids:
        return redirect('frontend:students_list')

    students = CustomUser.objects.filter(id__in=student_ids).order_by('grade', 'last_name', 'first_name')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="oquvchilar_parollari_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    )

    # Use utf-8-sig for proper excel opening with cyrillic
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow([_('Sinf'), _('Familiya'), _('Ism'), _('Login'), _('Parol')])

    for s in students:
        writer.writerow([s.grade or '-', s.last_name, s.first_name, s.username, s.raw_password or ''])

    return response


@login_required(login_url='login')
@school_admin_required
def student_detail(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    classmates = (
        CustomUser.objects.filter(school=request.user.school, role='student', grade=student.grade)
        .exclude(pk=student.pk)
        .order_by('last_name', 'first_name')
    )

    active_loans = (
        BookIssue.objects.select_related('book', 'user').filter(user=student, is_returned=False).select_related('book')
    )
    textbook_loans = TextbookLoan.objects.filter(student=student, returned_at__isnull=True).select_related('book')
    history = (
        BookIssue.objects.select_related('book', 'user')
        .filter(user=student, is_returned=True)
        .order_by('-returned_at')[:10]
    )
    total_read = BookIssue.objects.select_related('book', 'user').filter(user=student, is_returned=True).count()

    return render(
        request,
        'frontend/school/student_detail.html',
        {
            'student': student,
            'classmates': classmates,
            'active_loans': active_loans,
            'textbook_loans': textbook_loans,
            'history': history,
            'total_read': total_read,
        },
    )


@login_required(login_url='login')
@school_admin_required
def student_edit(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('frontend:students_list')
    else:
        form = StudentForm(instance=student)
    return render(
        request, 'frontend/school/student_form.html', {'form': form, 'title': _("O'quvchi ma'lumotlarini tahrirlash")}
    )


@login_required(login_url='login')
@school_admin_required
def student_delete(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        student.delete()
        return redirect('frontend:students_list')
    return render(request, 'frontend/school/confirm_delete.html', {'object': student, 'type': _("o'quvchini")})


@login_required(login_url='login')
@school_admin_required
def teacher_add(request):
    import datetime

    if request.method == 'POST':
        first_names = request.POST.getlist('first_name')
        last_names = request.POST.getlist('last_name')
        patronymics = request.POST.getlist('patronymic')
        birth_dates = request.POST.getlist('birth_date')
        subjects = request.POST.getlist('subject')
        addresses = request.POST.getlist('address')

        created_teachers = []

        def translit_cyrillic(text):
            if not text:
                return ''
            mapping = {
                'а': 'a',
                'б': 'b',
                'в': 'v',
                'г': 'g',
                'д': 'd',
                'е': 'e',
                'ё': 'yo',
                'ж': 'zh',
                'з': 'z',
                'и': 'i',
                'й': 'y',
                'к': 'k',
                'л': 'l',
                'м': 'm',
                'н': 'n',
                'о': 'o',
                'п': 'p',
                'р': 'r',
                'с': 's',
                'т': 't',
                'у': 'u',
                'ф': 'f',
                'х': 'x',
                'ц': 'ts',
                'ч': 'ch',
                'ш': 'sh',
                'щ': 'shch',
                'ъ': '',
                'ы': 'y',
                'ь': '',
                'э': 'e',
                'ю': 'yu',
                'я': 'ya',
                'ў': 'o',
                'қ': 'q',
                'ғ': 'g',
                'ҳ': 'x',
            }
            return ''.join(mapping.get(c, c) for c in text.lower()).replace(' ', '')

        for i in range(len(first_names)):
            f_name = first_names[i].strip()
            l_name = last_names[i].strip()
            if not f_name or not l_name:
                continue

            patronymic = patronymics[i].strip() if i < len(patronymics) else ''
            b_date_str = birth_dates[i] if i < len(birth_dates) else ''
            subject = subjects[i].strip() if i < len(subjects) else ''
            address = addresses[i].strip() if i < len(addresses) else ''

            full_first = f'{f_name} {patronymic}'.strip() if patronymic else f_name

            teacher = CustomUser(
                first_name=full_first,
                last_name=l_name,
                role='teacher',
                school=request.user.school,
                subject=subject,
                address=address,
            )

            if b_date_str:
                try:
                    teacher.birth_date = datetime.datetime.strptime(b_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Temporary username to save
            teacher.username = f'temp_t_{secrets.token_hex(4)}'
            teacher.save()

            # Generate Login and Password
            first_lat = translit_cyrillic(f_name)
            last_lat = translit_cyrillic(l_name)

            base_username = clean_name(f'{first_lat}_{last_lat}')
            if not base_username:
                base_username = f'teacher_{teacher.id}'

            username = base_username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f'{base_username}_{counter}'
                counter += 1

            teacher.username = username

            if first_lat and last_lat:
                password = f'{first_lat.capitalize()}{last_lat.capitalize()}!'
            else:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for _ in range(12))

            teacher.set_password(password)
            teacher.raw_password = password
            teacher.save()

            created_teachers.append(teacher.id)

        if created_teachers:
            request.session['bulk_created_teachers'] = created_teachers
            messages.success(request, _(f"{len(created_teachers)} ta o'qituvchi muvaffaqiyatli qo'shildi!"))
            return redirect('frontend:bulk_teacher_credentials_prompt')
        else:
            messages.error(request, _("Hech qanday o'qituvchi qo'shilmadi."))
            return redirect('frontend:teacher_add')

    else:
        form = TeacherForm()
    return render(
        request, 'frontend/school/teacher_form.html', {'form': form, 'title': _("Ko'p o'qituvchilarni qo'shish")}
    )


@login_required(login_url='login')
@school_admin_required
def bulk_teacher_credentials_prompt(request):
    teacher_ids = request.session.get('bulk_created_teachers', [])
    if not teacher_ids:
        return redirect('frontend:teachers_list')

    teachers = CustomUser.objects.filter(id__in=teacher_ids)
    return render(request, 'frontend/school/bulk_teacher_credentials_prompt.html', {'teachers': teachers})


@login_required(login_url='login')
@school_admin_required
def download_bulk_teacher_credentials_csv(request):
    import csv

    from django.http import HttpResponse

    teacher_ids = request.session.get('bulk_created_teachers', [])
    if not teacher_ids:
        return redirect('frontend:teachers_list')

    teachers = CustomUser.objects.filter(id__in=teacher_ids).order_by('last_name', 'first_name')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="oqituvchilar_parollari_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    )

    # Use utf-8-sig for proper excel opening with cyrillic
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow([_('Familiya'), _('Ism'), _('Fan'), _('Login'), _('Parol')])

    for t in teachers:
        writer.writerow([t.last_name, t.first_name, t.subject, t.username, t.raw_password or ''])

    return response


@login_required(login_url='login')
@school_admin_required
def teacher_edit(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            return redirect('frontend:teachers_list')
    else:
        form = TeacherForm(instance=teacher)
    return render(
        request, 'frontend/school/teacher_form.html', {'form': form, 'title': _("O'qituvchi ma'lumotlarini tahrirlash")}
    )


@login_required(login_url='login')
@school_admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        teacher.delete()
        return redirect('frontend:teachers_list')
    return render(request, 'frontend/school/confirm_delete.html', {'object': teacher, 'type': _("o'qituvchini")})


@login_required(login_url='login')
@school_admin_required
def news_add(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.school = request.user.school
            news.save()
            return redirect('frontend:school_news_list')
    else:
        form = NewsForm()
    return render(request, 'frontend/school/news_form.html', {'form': form, 'title': _("Yangi yangilik qo'shish")})


@login_required(login_url='login')
@school_admin_required
def news_edit(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('frontend:school_news_list')
    else:
        form = NewsForm(instance=news)
    return render(request, 'frontend/school/news_form.html', {'form': form, 'title': _('Yangilikni tahrirlash')})


@login_required(login_url='login')
@school_admin_required
def news_delete(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        news.delete()
        return redirect('frontend:school_news_list')
    return render(request, 'frontend/school/confirm_delete.html', {'object': news, 'type': _('yangilikni')})


@login_required(login_url='login')
@school_admin_required
def profile(request):
    if request.user.role != 'school_admin':
        return redirect('frontend:library')
    school = request.user.school
    recent_activity = ActionLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncMonth

    stats = (
        Book.objects.select_related('school', 'category')
        .filter(school=school)
        .aggregate(
            total_copies=Sum('total_count'),
            available_copies=Sum('available_count'),
        )
    )

    issue_qs = BookIssue.objects.select_related('book', 'user').filter(book__school=school, is_returned=False)
    today = timezone.now().date()
    recent_issues = (
        BookIssue.objects.select_related('book', 'user').filter(book__school=school).order_by('-issued_at')[:8]
    )

    # Monthly issues for chart (last 6 months)
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    monthly_qs = (
        BookIssue.objects.select_related('book', 'user')
        .filter(book__school=school, issued_at__gte=six_months_ago)
        .annotate(month=TruncMonth('issued_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    month_labels = []
    monthly_data = []
    months_uz = [
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
    for entry in monthly_qs:
        if entry['month']:
            m = entry['month'].month - 1
            month_labels.append(months_uz[m] if m < len(months_uz) else str(entry['month'].month))
            monthly_data.append(entry['count'])

    return render(
        request,
        'frontend/school/profile.html',
        {
            'recent_activity': recent_activity,
            'recent_issues': recent_issues,
            'total_books': Book.objects.select_related('school', 'category').filter(school=school).count(),
            'total_copies': stats['total_copies'] or 0,
            'available_copies': stats['available_copies'] or 0,
            'total_students': CustomUser.objects.filter(school=school, role='student').count(),
            'total_teachers': CustomUser.objects.filter(school=school, role='teacher').count(),
            'active_issues': issue_qs.count(),
            'overdue_issues': issue_qs.filter(issued_at__lt=timezone.now() - timezone.timedelta(days=30)).count(),
            'issued_today': BookIssue.objects.filter(book__school=school, issued_at__date=today).count(),
            'returned_today': BookIssue.objects.filter(
                book__school=school, returned_at__date=today, is_returned=True
            ).count(),
            'month_labels': month_labels,
            'monthly_data': monthly_data,
        },
    )


@login_required(login_url='login')
@school_admin_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, _("Parolingiz muvaffaqiyatli o'zgartirildi!"))
            return redirect('frontend:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'frontend/school/password_change.html', {'form': form})


@login_required(login_url='login')
@school_admin_required
def statistics(request):
    school = request.user.school
    today = timezone.now().date()

    from books.models import BookIssue, Challenge, UserAchievement

    active_students = CustomUser.objects.filter(
        school=school, role='student', is_archived=False, bookissue__is_returned=False
    ).distinct()[:20]
    active_count = (
        CustomUser.objects.filter(school=school, role='student', is_archived=False, bookissue__is_returned=False)
        .distinct()
        .count()
    )
    top_students = CustomUser.objects.filter(school=school, role='student', is_archived=False).order_by(
        '-total_books_read'
    )[:10]
    recent_yutuqlar = (
        UserAchievement.objects.filter(user__school=school, user__role='student')
        .select_related('user', 'achievement')
        .order_by('-earned_at')[:15]
    )
    active_chellenjlar = Challenge.objects.filter(is_active=True, start_date__lte=today, end_date__gte=today).filter(
        Q(school=school) | Q(school__isnull=True)
    )
    total_students = CustomUser.objects.filter(school=school, role='student', is_archived=False).count()
    total_books = Book.objects.select_related('school', 'category').filter(school=school).count()
    total_issues = BookIssue.objects.select_related('book', 'user').filter(book__school=school).count()
    active_issues = (
        BookIssue.objects.select_related('book', 'user').filter(book__school=school, is_returned=False).count()
    )

    # Track which top students already have news posted today
    from schools.models import News

    posted_today_ids = set()
    for s in top_students:
        prefix = _("Eng faol o'quvchi: {name}").format(name=f'{s.first_name} {s.last_name}')
        if News.objects.filter(school=school, title__startswith=prefix, created_at__date=today).exists():
            posted_today_ids.add(s.pk)

    return render(
        request,
        'frontend/school/statistics.html',
        {
            'active_students': active_students,
            'active_count': active_count,
            'top_students': top_students,
            'recent_yutuqlar': recent_yutuqlar,
            'active_chellenjlar': active_chellenjlar,
            'total_students': total_students,
            'total_books': total_books,
            'total_issues': total_issues,
            'active_issues': active_issues,
            'posted_today_ids': posted_today_ids,
        },
    )


@login_required(login_url='login')
@school_admin_required
def post_top_student_news(request, pk):
    school = request.user.school
    student = get_object_or_404(CustomUser, pk=pk, school=school, role='student')

    # Check if already posted today
    from django.utils import timezone
    from schools.models import News

    today = timezone.localdate()
    existing = News.objects.filter(
        school=school,
        title__startswith=_("Eng faol o'quvchi: {name}").format(name=f'{student.first_name} {student.last_name}'),
        created_at__date=today,
    ).exists()
    if existing:
        messages.warning(request, _('Bugun bu haqida yangilik allaqachon chop etilgan!'))
        return redirect('frontend:school_statistics')

    title = _("Eng faol o'quvchi: {name}").format(name=f'{student.first_name} {student.last_name}')
    News.objects.create(
        school=school,
        title=title,
        body='',
        is_published=True,
        template_key='top_reader',
        template_data={
            'student': {
                'name': f'{student.first_name} {student.last_name}',
                'grade': student.grade or '—',
                'school': school.name,
            },
            'books': student.total_books_read,
            'xp': student.xp_points,
            'level': student.level,
            'streak': student.current_streak,
        },
    )
    messages.success(request, _('Yangilik muvaffaqiyatli yaratildi!'))
    return redirect('frontend:school_statistics')


@login_required(login_url='login')
@school_admin_required
def graduates_list(request):
    school = request.user.school
    query = request.GET.get('q')
    graduates = CustomUser.objects.filter(school=school, role='student', is_archived=True)

    total_graduates = graduates.count()
    total_books = Book.objects.select_related('school', 'category').filter(school=school).count()
    total_active = (
        BookIssue.objects.select_related('book', 'user').filter(book__school=school, is_returned=False).count()
    )

    if query:
        graduates = graduates.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(grade__icontains=query)
        )

    graduates = graduates.order_by('last_name', 'first_name')

    from django.core.paginator import Paginator

    paginator = Paginator(graduates, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/graduates.html',
        {
            'graduates': page_obj,
            'page_obj': page_obj,
            'query': query,
            'total_graduates': total_graduates,
            'total_books': total_books,
            'total_active': total_active,
        },
    )


@login_required(login_url='login')
@school_admin_required
def textbook_loans(request):
    import re

    school = request.user.school
    grade_filter = request.GET.get('grade', '')

    loans = TextbookLoan.objects.filter(book__school=school).select_related('book', 'student').order_by('-issued_at')

    active_loans = loans.filter(returned_at__isnull=True).count()
    total_loans = loans.count()
    returned_loans = loans.filter(returned_at__isnull=False).count()

    if grade_filter:
        loans = loans.filter(student__grade=grade_filter)

    # Distinct grades for filter
    all_grades = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades, key=sort_grade)

    # Academic years for filter
    years = (
        TextbookLoan.objects.filter(book__school=school)
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )

    from django.core.paginator import Paginator

    paginator = Paginator(loans, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'frontend/school/textbook_loans.html',
        {
            'loans': page_obj,
            'page_obj': page_obj,
            'active_loans': active_loans,
            'total_loans': total_loans,
            'returned_loans': returned_loans,
            'grades_list': grades_list,
            'selected_grade': grade_filter,
            'years': years,
        },
    )


@login_required(login_url='login')
@school_admin_required
def textbook_distribute(request):
    import datetime
    import re

    school = request.user.school
    grade_filter = request.GET.get('grade', '')

    # Compute current academic year
    now = datetime.date.today()
    if now.month >= 9:
        academic_year = f'{now.year}/{now.year + 1}'
    else:
        academic_year = f'{now.year - 1}/{now.year}'

    # Get distinct grades
    all_grades = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades, key=sort_grade)

    if request.method == 'POST':
        auto = request.POST.get('auto') == '1'
        due_date = datetime.date(now.year + 1, 6, 1) if now.month >= 9 else datetime.date(now.year, 6, 1)
        created_count = 0

        def create_loan(student, book):
            nonlocal created_count
            existing = TextbookLoan.objects.filter(student=student, book=book, academic_year=academic_year).first()
            if not existing:
                TextbookLoan.objects.create(
                    book=book,
                    student=student,
                    academic_year=academic_year,
                    due_date=due_date,
                    condition_on_issue='good',
                    notes='',
                )
                created_count += 1

        if auto:
            # Auto-assign: all textbooks matching this grade to all students
            students = CustomUser.objects.filter(school=school, role='student')
            if grade_filter:
                students = students.filter(grade=grade_filter)
            for student in students:
                grade_num = (
                    int(re.match(r'(\d+)', student.grade or '0').group(1))
                    if re.match(r'(\d+)', student.grade or '')
                    else None
                )
                textbooks_for_grade = Book.objects.select_related('school', 'category').filter(
                    school=school, is_textbook=True
                )
                if grade_num:
                    textbooks_for_grade = textbooks_for_grade.filter(grade=grade_num)
                for book in textbooks_for_grade:
                    create_loan(student, book)
        elif request.POST.get('distribute_all_book_id'):
            # Distribute a single specific book to all students in the selected grade
            book_id = request.POST.get('distribute_all_book_id')
            book = get_object_or_404(Book, pk=book_id, school=school, is_textbook=True)
            students = CustomUser.objects.filter(school=school, role='student')
            if grade_filter:
                students = students.filter(grade=grade_filter)
            for student in students:
                create_loan(student, book)
        else:
            selected = {}
            for key, value in request.POST.items():
                if key.startswith('book_'):
                    parts = key.split('_', 1)
                    student_id = parts[1]
                    selected[student_id] = value
            for student_id, book_id in selected.items():
                if not book_id:
                    continue
                student = get_object_or_404(CustomUser, pk=student_id, school=school, role='student')
                book = get_object_or_404(Book, pk=book_id, school=school, is_textbook=True)
                create_loan(student, book)

        messages.success(request, _('{count} ta darslik tarqatildi.').format(count=created_count))
        return redirect('frontend:textbook_loans')

    # GET: show students by grade with available textbooks
    students = CustomUser.objects.filter(school=school, role='student')
    if grade_filter:
        students = students.filter(grade=grade_filter)

    students = sorted(
        students,
        key=lambda u: (
            int(re.match(r'(\d+)', u.grade or '99').group(1)) if re.match(r'(\d+)', u.grade or '') else 99,
            u.last_name or '',
            u.first_name or '',
        ),
    )

    # Get textbooks that match the grade (or any if no grade filter)
    if grade_filter:
        grade_num = int(re.match(r'(\d+)', grade_filter).group(1)) if re.match(r'(\d+)', grade_filter) else None
    else:
        grade_num = None

    textbooks = Book.objects.select_related('school', 'category').filter(school=school, is_textbook=True)
    if grade_num:
        textbooks = textbooks.filter(grade=grade_num)
    textbooks = textbooks.order_by('subject', 'title')

    # Students who already have textbooks this year
    existing_student_ids = set(
        TextbookLoan.objects.filter(
            student__in=students, academic_year=academic_year, returned_at__isnull=True
        ).values_list('student_id', flat=True)
    )

    return render(
        request,
        'frontend/school/textbook_distribute.html',
        {
            'students': students,
            'textbooks': textbooks,
            'grades_list': grades_list,
            'selected_grade': grade_filter,
            'academic_year': academic_year,
            'existing_loans': existing_student_ids,
        },
    )


@login_required(login_url='login')
@school_admin_required
def textbook_collect(request):
    import datetime
    import re

    school = request.user.school
    grade_filter = request.GET.get('grade', '')

    loans = (
        TextbookLoan.objects.filter(book__school=school, returned_at__isnull=True)
        .select_related('book', 'student')
        .order_by('student__grade', 'student__last_name')
    )

    if grade_filter:
        loans = loans.filter(student__grade=grade_filter)

    # Distinct grades for filter
    all_grades = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True)
        .exclude(grade='')
        .values_list('grade', flat=True)
        .distinct()
    )

    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99

    grades_list = sorted(all_grades, key=sort_grade)

    if request.method == 'POST':
        collected = 0
        for key, value in request.POST.items():
            if key.startswith('return_'):
                loan_id = key.split('_', 1)[1]
                try:
                    loan = TextbookLoan.objects.get(id=loan_id, book__school=school, returned_at__isnull=True)
                    loan.returned_at = datetime.date.today()
                    condition = request.POST.get(f'condition_{loan_id}', 'fair')
                    loan.condition_on_return = condition
                    loan.notes = request.POST.get(f'notes_{loan_id}', loan.notes or '')
                    loan.save()
                    collected += 1
                except TextbookLoan.DoesNotExist:
                    continue

        messages.success(request, _('{count} ta darslik qaytarib olindi.').format(count=collected))
        return redirect('frontend:textbook_loans')

    return render(
        request,
        'frontend/school/textbook_collect.html',
        {
            'loans': loans,
            'grades_list': grades_list,
            'selected_grade': grade_filter,
        },
    )


@login_required(login_url='login')
@school_admin_required
def export_students_csv(request):
    import csv

    from django.http import HttpResponse

    school = request.user.school
    students = CustomUser.objects.filter(school=school, role='student').order_by('grade', 'last_name')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Username', 'Ism', 'Familiya', 'Sinf', 'Kitoblar soni'])
    for i, s in enumerate(students, 1):
        writer.writerow([i, s.username, s.first_name, s.last_name, s.grade, s.total_books_read])
    return response


@login_required(login_url='login')
@school_admin_required
def export_books_csv(request):
    import csv

    from django.http import HttpResponse

    school = request.user.school
    books = Book.objects.select_related('school', 'category').filter(school=school).order_by('title')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="books.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Sarlavha', 'Muallif', 'Kategoriya', 'Umumiy', 'Mavjud', "O'qilgan", 'Darslik'])
    for i, b in enumerate(books, 1):
        writer.writerow(
            [
                i,
                b.title,
                b.author or '',
                b.category.name if b.category else '',
                b.total_count,
                b.available_count,
                b.borrow_count,
                'Ha' if b.is_textbook else '',
            ]
        )
    return response


@login_required(login_url='login')
@school_admin_required
def export_issues_csv(request):
    import csv

    from django.http import HttpResponse

    school = request.user.school
    issues = (
        BookIssue.objects.select_related('book', 'user')
        .filter(book__school=school)
        .select_related('book', 'user')
        .order_by('-issued_at')
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="book_issues.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Kitob', "O'quvchi", 'Sinf', 'Berilgan', 'Qaytarilgan', 'Holati'])
    for i, iss in enumerate(issues, 1):
        writer.writerow(
            [
                i,
                iss.book.title,
                iss.user.get_full_name() or iss.user.username,
                iss.user.grade or '',
                iss.issued_at.strftime('%d.%m.%Y'),
                iss.returned_at.strftime('%d.%m.%Y') if iss.returned_at else '',
                'Qaytarilgan' if iss.is_returned else 'Ijarada',
            ]
        )
    return response


@login_required(login_url='login')
@school_admin_required
def import_students_csv(request):
    if request.method != 'POST':
        return render(
            request,
            'frontend/school/csv_import.html',
            {
                'title': _("O'quvchilarni CSV dan import qilish"),
                'action_url': reverse('frontend:import_students_csv'),
                'redirect_url': reverse('frontend:students_list'),
            },
        )
    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'success': False, 'errors': [_('Fayl yuklanmadi')]}, status=400)
    if not (csv_file.name.endswith('.csv') or csv_file.name.endswith('.xlsx')):
        return JsonResponse({'success': False, 'errors': [_('Faqat CSV yoki XLSX fayl yuklang')]}, status=400)

    school = request.user.school
    import csv
    import secrets
    import string

    data_rows = []

    if csv_file.name.endswith('.xlsx'):
        import openpyxl

        wb = openpyxl.load_workbook(csv_file, data_only=True)
        sheet = wb.active
        headers = [cell.value.strip() if isinstance(cell.value, str) else cell.value for cell in sheet[1]]

        # Determine column indexes
        first_name_idx, last_name_idx, grade_idx = None, None, None
        for i, header in enumerate(headers):
            if header == 'first_name':
                first_name_idx = i
            elif header == 'last_name':
                last_name_idx = i
            elif header == 'grade':
                grade_idx = i

        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
            if first_name_idx is not None and last_name_idx is not None and grade_idx is not None:
                first_name = str(row[first_name_idx] or '').strip()
                last_name = str(row[last_name_idx] or '').strip()
                grade = str(row[grade_idx] or '').strip()
                data_rows.append({'row_num': row_num, 'first_name': first_name, 'last_name': last_name, 'grade': grade})
    else:
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(decoded.splitlines())
        for row_num, row in enumerate(reader, 2):
            data_rows.append(
                {
                    'row_num': row_num,
                    'first_name': row.get('first_name', '').strip(),
                    'last_name': row.get('last_name', '').strip(),
                    'grade': row.get('grade', '').strip(),
                }
            )

    created = 0
    errors = []
    credentials = []

    for item in data_rows:
        row_num = item['row_num']
        first_name = item['first_name']
        last_name = item['last_name']
        grade = item['grade']

        if not first_name or not last_name or not grade:
            errors.append(_('Qator {}: ism, familiya va sinf majburiy').format(row_num))
            continue
        try:
            student = CustomUser(
                school=school,
                role='student',
                first_name=first_name,
                last_name=last_name,
                grade=grade,
            )
            student.username = f'temp_{secrets.token_hex(4)}'
            student.save()
            district_part = clean_name(
                student.school.district.name if student.school and student.school.district else 'no'
            )
            school_part = clean_name(student.school.name if student.school else 'school')
            student.username = f'{district_part}_{school_part}_{student.id}'
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            student.set_password(password)
            student.save()
            created += 1
            credentials.append({'username': student.username, 'password': password})
        except Exception as e:
            errors.append(_('Qator {}: {}').format(row_num, str(e)))
    if created:
        messages.success(request, _("{} ta o'quvchi muvaffaqiyatli import qilindi.").format(created))
    if errors:
        messages.warning(request, _('Importda {} ta xatolik yuz berdi.').format(len(errors)))
    return JsonResponse(
        {
            'success': True,
            'created': created,
            'errors': errors,
            'credentials': credentials,
        }
    )


@login_required(login_url='login')
@school_admin_required
def import_books_csv(request):
    if request.method != 'POST':
        return render(
            request,
            'frontend/school/csv_import.html',
            {
                'title': _('Kitoblarni CSV dan import qilish'),  # noqa: F823
                'action_url': reverse('frontend:import_books_csv'),
                'redirect_url': reverse('frontend:school_books_list'),
            },
        )
    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'success': False, 'errors': [_('Fayl yuklanmadi')]}, status=400)
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'success': False, 'errors': [_('Faqat CSV fayl yuklang')]}, status=400)
    school = request.user.school
    import csv

    decoded = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(decoded.splitlines())
    created = 0
    errors = []
    for row_num, row in enumerate(reader, 2):
        title = row.get('title', '').strip()
        author = row.get('author', '').strip()
        category_name = row.get('category', '').strip()
        total_count_str = row.get('total_count', '').strip()
        available_count_str = row.get('available_count', '').strip()
        description = row.get('description', '').strip()
        is_textbook_str = row.get('is_textbook', '').strip().upper()
        if not title or not total_count_str or not available_count_str:
            errors.append(_('Qator {}: sarlavha, umumiy soni va mavjud soni majburiy').format(row_num))
            continue
        try:
            total_count = int(total_count_str)
            available_count = int(available_count_str)
        except ValueError:
            errors.append(_("Qator {}: sonlar noto'g'ri formatda").format(row_num))
            continue
        try:
            category = None
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)
            book = Book(
                school=school,
                title=title,
                author=author or None,
                category=category,
                total_count=total_count,
                available_count=available_count,
                description=description or '',
                is_textbook=(is_textbook_str == 'TRUE'),
            )
            book.save()
            created += 1
        except Exception as e:
            errors.append(_('Qator {}: {}').format(row_num, str(e)))
    if created:
        messages.success(request, _('{} ta kitob muvaffaqiyatli import qilindi.').format(created))
    if errors:
        messages.warning(request, _('Importda {} ta xatolik yuz berdi.').format(len(errors)))
    return JsonResponse({'success': True, 'created': created, 'errors': errors})
