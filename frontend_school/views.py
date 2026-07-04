from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse

school_admin_required = user_passes_test(lambda u: u.role == 'school_admin' and u.school is not None, login_url='login')
from django.http import JsonResponse
from django.db.models import Sum, Q, F
from django.utils.crypto import get_random_string
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext as _
from django.utils import timezone
import json
import secrets
import string
import logging

logger = logging.getLogger(__name__)

from accounts.models import CustomUser
from accounts.utils import verify_dynamic_token
from books.models import Book, BookIssue, BookRequest, Category, TextbookLoan
from books.achievements import award_xp
from stats.models import ActionLog
from .models import News
from .forms import BookForm, StudentForm, TeacherForm, NewsForm

def clean_name(name):
    return "".join(c for c in name.lower() if c.isalnum() or c == '_').strip('_')

@login_required(login_url='login')
@school_admin_required
def dashboard(request):
    if request.user.role != 'school_admin':
        return redirect('frontend_user:library')
    school = request.user.school
    context = {}
    if school:
        recent_activities = BookIssue.objects.filter(book__school=school).order_by('-issued_at')[:10]
        stats = Book.objects.filter(school=school).aggregate(
            total_copies=Sum('total_count'),
            available_copies=Sum('available_count')
        )
        from django.db.models import Q, Count
        from django.db.models.functions import TruncMonth
        # Base news filter: current school's news
        news_filter = Q(school=school)
        if request.user.role == 'school_admin' or request.user.is_superuser:
            news_filter |= Q(school__isnull=True)

        # Monthly issues for chart
        today = timezone.now()
        six_months_ago = today - timezone.timedelta(days=180)
        monthly_qs = (
            BookIssue.objects
            .filter(book__school=school, issued_at__gte=six_months_ago)
            .annotate(month=TruncMonth('issued_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        month_labels = []
        monthly_data = []
        months_uz = [_('Yan'), _('Fev'), _('Mar'), _('Apr'), _('May'), _('Iyun'),
                     _('Iyl'), _('Avg'), _('Sen'), _('Okt'), _('Noy'), _('Dek')]
        for entry in monthly_qs:
            if entry['month']:
                m = entry['month'].month - 1
                month_labels.append(months_uz[m] if m < len(months_uz) else str(entry['month'].month))
                monthly_data.append(entry['count'])

        context = {
            'student_count': CustomUser.objects.filter(school=school, role='student').count(),
            'book_count': Book.objects.filter(school=school).count(),
            'total_copies': stats['total_copies'] or 0,
            'available_copies': stats['available_copies'] or 0,
            'issued_count': BookIssue.objects.filter(book__school=school, is_returned=False).count(),
            'recent_activities': recent_activities,
            'news_count': News.objects.filter(news_filter, is_published=True).count(),
            'month_labels': json.dumps(month_labels),
            'monthly_data': json.dumps(monthly_data),
        }
    return render(request, 'school_panel/dashboard.html', context)

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
    active_loans = BookIssue.objects.filter(book__school=school, is_returned=False)
    reading_students = active_loans.values('user').distinct().count()
    today = timezone.now().date()
    entered_today = students.filter(last_login__date=today).count()
    
    if query:
        from django.db.models import Q
        students = students.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(grade__icontains=query)
        )
    
    if grade_filter:
        students = students.filter(grade=grade_filter)
    
    # Get distinct grades in school for filter, sorted numerically
    all_grades_in_school = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True).exclude(grade='')
        .values_list('grade', flat=True).distinct()
    )
    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99
    grades_list = sorted(all_grades_in_school, key=sort_grade)
    
    # Sort students numerically by grade, then by name
    students = sorted(students, key=lambda u: (
        int(re.match(r'(\d+)', u.grade or '99').group(1)) if re.match(r'(\d+)', u.grade or '') else 99,
        u.grade or '',
        u.last_name or '',
        u.first_name or '',
    ))
    
    from django.core.paginator import Paginator
    paginator = Paginator(students, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/students.html', {
        'students': page_obj, 'page_obj': page_obj, 'query': query,
        'total_students': total_students, 'reading_students': reading_students,
        'entered_today': entered_today,
        'grades_list': grades_list,
        'selected_grade': grade_filter,
    })

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
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        
    teachers = teachers.order_by('last_name', 'first_name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(teachers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/teachers.html', {
        'teachers': page_obj, 'page_obj': page_obj, 'query': query,
        'total_teachers': total_teachers, 'entered_today': entered_today,
    })

@login_required(login_url='login')
@school_admin_required
def books_list(request):
    school = request.user.school
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    no_cover = request.GET.get('no_cover')
    textbook = request.GET.get('textbook')
    
    from django.db.models import Sum
    all_books = Book.objects.filter(school=school)
    total_books = all_books.count()
    stats = all_books.aggregate(
        total_copies=Sum('total_count'),
        available_copies=Sum('available_count')
    )
    issued_count = BookIssue.objects.filter(book__school=school, is_returned=False).count()
    
    books = all_books
    
    if query:
        from books.search import search_books
        books = search_books(books, query, fields=("title",))
    
    if category_id:
        books = books.filter(category_id=category_id)
        
    if no_cover == '1':
        from django.db.models import Q
        books = books.filter(Q(cover='') | Q(cover__isnull=True))

    if textbook == '1':
        books = books.filter(is_textbook=True)
        
    books = books.order_by('title')
    
    from books.models import Category
    categories = Category.objects.all().order_by('name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(books, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/books.html', {
        'books': page_obj, 
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': int(category_id) if category_id else None,
        'no_cover': no_cover == '1',
        'textbook_filter': textbook == '1',
        'total_books': total_books,
        'total_copies': stats['total_copies'] or 0,
        'available_copies': stats['available_copies'] or 0,
        'issued_count': issued_count,
    })

@login_required(login_url='login')
@school_admin_required
def issued_books_list(request):
    school = request.user.school
    issues = BookIssue.objects.filter(book__school=school, is_returned=False).select_related('book', 'user').order_by('-issued_at')
    
    total_issued = issues.count()
    unique_students = issues.values('user').distinct().count()
    unique_books = issues.values('book').distinct().count()
    
    from django.core.paginator import Paginator
    paginator = Paginator(issues, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/issued_books.html', {
        'issues': page_obj, 'page_obj': page_obj,
        'total_issued': total_issued, 'unique_students': unique_students,
        'unique_books': unique_books,
    })

@login_required(login_url='login')
@school_admin_required
def history_list(request):
    school = request.user.school
    query = request.GET.get('q')
    
    all_history = BookIssue.objects.filter(book__school=school)
    total_actions = all_history.count()
    returned_count = all_history.filter(is_returned=True).count()
    issued_count = all_history.filter(is_returned=False).count()
    
    history = all_history.select_related('book', 'user').order_by('-issued_at')
    
    if query:
        from django.db.models import Q
        history = history.filter(
            Q(book__title__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )
    
    from django.core.paginator import Paginator
    paginator = Paginator(history, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/history.html', {
        'history': page_obj, 'page_obj': page_obj, 'query': query,
        'total_actions': total_actions, 'returned_count': returned_count,
        'issued_count': issued_count,
    })

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
    
    return render(request, 'school_panel/news.html', {
        'news': page_obj, 'page_obj': page_obj,
        'total_news': total_news, 'school_news': school_news,
        'global_news': global_news,
    })

@login_required(login_url='login')
@school_admin_required
def qr_unified(request):
    school = request.user.school
    today = timezone.now().date()
    today_issues = BookIssue.objects.filter(book__school=school, issued_at__date=today).count()
    today_returns = BookIssue.objects.filter(book__school=school, returned_at__date=today, is_returned=True).count()
    total_scans = today_issues + today_returns
    return render(request, 'school_panel/qr_unified.html', {
        'today_scans': total_scans,
        'today_issues': today_issues,
        'today_returns': today_returns,
    })

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
            else:
                return JsonResponse({'status': 'error', 'message': _('Noma\'lum QR-kod turi. Iltimos, kitob berish yoki qaytarish kodini skanerlang.')})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov formati'})
        except Exception as e:
            logger.error(f"process_qr_unified error: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': _('Tizimda xatolik yuz berdi')})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

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
                return JsonResponse({'status': 'error', 'message': _('Eski yoki noto\'g\'ri QR-kod. Iltimos, o\'quvchi telefonida kodni yangilasini kutib turing.')})
            
            try:
                request_obj = BookRequest.objects.get(id=request_id, status='pending')
            except BookRequest.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': _('Bron topilmadi yoki allaqachon tasdiqlangan')})
            
            if request_obj.user.school != request.user.school:
                return JsonResponse({'status': 'error', 'message': _('Xatolik: Ushbu o\'quvchi boshqa maktabga tegishli!')})
            
            # Students cannot borrow textbooks
            if request_obj.user.role == 'student' and request_obj.book.is_textbook:
                return JsonResponse({'status': 'error', 'message': _("Darsliklarni o'quvchilar ololmaydi. Darsliklar o'quv yili boshida tarqatiladi.")})
            
            from django.db.models import F
            book = request_obj.book
            if book.available_count <= 0:
                return JsonResponse({'status': 'error', 'message': _('Kitob qolmagan')})
            
            request_obj.status = 'approved'
            request_obj.save()
            
            issue = BookIssue.objects.create(book=book, user=request_obj.user)
            
            book.available_count = F('available_count') - 1
            book.borrow_count = F('borrow_count') + 1
            book.save()
            book.refresh_from_db()

            # Notify the user
            from notifications.utils import notify_user
            notify_user(
                request_obj.user,
                _("Kitob tasdiqlandi"),
                _('"{title}" kitobi sizga berildi').format(title=book.title),
                url=reverse('frontend_user:my_books'),
            )

            ActionLog.objects.create(
                user=request.user,
                action_type='ISSUE',
                message=_("{}ga '{}' kitobi berildi").format(request_obj.user.username, book.title)
            )

            xp_result = award_xp(request_obj.user, 'borrow', book=book)
            
            return JsonResponse({
                'status': 'success', 
                'message': _('Kitob muvaffaqiyatli berildi: {}').format(book.title),
                'student': f'{request_obj.user.first_name} {request_obj.user.last_name}',
                'xp_earned': xp_result['xp_earned'],
                'lucky_bonus': xp_result['lucky_bonus'],
                'leveled_up': xp_result['leveled_up'],
                'new_level': xp_result['new_level'],
                'new_achievements': xp_result['new_achievements'],
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov formati'})
        except Exception as e:
            logger.error(f"process_qr error: {e}", exc_info=True)
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
                return JsonResponse({'status': 'error', 'message': _('Eski yoki noto\'g\'ri QR-kod')})
                
            from books.models import BookIssue
            from django.utils import timezone
            from stats.models import ActionLog
            from django.db.models import F
            
            try:
                issue = BookIssue.objects.get(id=issue_id, is_returned=False)
            except BookIssue.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': _('Ushbu kitob uchun faol topshirish topilmadi')})
            
            if issue.user.school != request.user.school:
                return JsonResponse({'status': 'error', 'message': _('Xatolik: Ushbu o\'quvchi boshqa maktabga tegishli!')})
            
            book = issue.book
            user = issue.user
            
            issue.is_returned = True
            issue.returned_at = timezone.now()
            issue.save()
            
            book.available_count = F('available_count') + 1
            book.save()
            book.refresh_from_db()
            
            request_obj = BookRequest.objects.filter(book=book, user=user, status='approved').first()
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
                    _("Kitob mavjud!"),
                    _('"{title}" kitobi bo\'shadi. Navbat sizda!').format(title=book.title),
                    url=reverse('frontend_user:book_detail', args=[book.pk]),
                )

            ActionLog.objects.create(
                user=request.user,
                action_type='RETURN',
                message=_("{}dan '{}' kitobi qabul qilindi").format(user.username, book.title)
            )

            xp_result = award_xp(user, 'return')
            
            return JsonResponse({
                'status': 'success', 
                'message': _('Kitob muvaffaqiyatli qabul qilindi: {}').format(book.title),
                'student': f'{user.first_name} {user.last_name}',
                'xp_earned': xp_result['xp_earned'],
                'lucky_bonus': False,
                'leveled_up': xp_result['leveled_up'],
                'new_level': xp_result['new_level'],
                'new_achievements': xp_result['new_achievements'],
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Noto\'g\'ri so\'rov formati'})
        except Exception:
            return JsonResponse({'status': 'error', 'message': _('Tizimda xatolik yuz berdi')})
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


@login_required(login_url='login')
@school_admin_required
def book_add(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.school = request.user.school
            book.save()
            return redirect('frontend_school:books_list')
    else:
        form = BookForm()
    return render(request, 'school_panel/book_form.html', {'form': form, 'title': _('Yangi kitob qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:books_list')
    else:
        form = BookForm(instance=book)
    return render(request, 'school_panel/book_form.html', {'form': form, 'title': _('Kitobni tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    if request.method == 'POST':
        book.delete()
        return redirect('frontend_school:books_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': book, 'type': _('kitobni')})

@login_required(login_url='login')
@school_admin_required
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = request.user.school
            student.role = 'student'
            
            # 1. Save initially to get ID
            student.username = f"temp_{secrets.token_hex(4)}"
            student.save()
            
            # 2. Generate Smart Login: {district}_{school}_{id}
            district_part = clean_name(student.school.district.name if student.school and student.school.district else "no")
            school_part = clean_name(student.school.name if student.school else "school")
            
            username = f"{district_part}_{school_part}_{student.id}"
            student.username = username
            
            # 3. Generate Random Password (12 chars)
            password = form.cleaned_data.get('password')
            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            student.set_password(password)
            student.save()
            
            messages.success(request, _("Yangi o'quvchi qo'shildi! Login: {}, Parol: {}").format(username, password))
            return redirect('frontend_school:students_list')
    else:
        form = StudentForm()
    return render(request, 'school_panel/student_form.html', {'form': form, 'title': _('Yangi o\'quvchi qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def student_detail(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    classmates = CustomUser.objects.filter(
        school=request.user.school, role='student', grade=student.grade
    ).exclude(pk=student.pk).order_by('last_name', 'first_name')
    
    active_loans = BookIssue.objects.filter(user=student, is_returned=False).select_related('book')
    textbook_loans = TextbookLoan.objects.filter(student=student, returned_at__isnull=True).select_related('book')
    history = BookIssue.objects.filter(user=student, is_returned=True).order_by('-returned_at')[:10]
    total_read = BookIssue.objects.filter(user=student, is_returned=True).count()
    
    return render(request, 'school_panel/student_detail.html', {
        'student': student,
        'classmates': classmates,
        'active_loans': active_loans,
        'textbook_loans': textbook_loans,
        'history': history,
        'total_read': total_read,
    })

@login_required(login_url='login')
@school_admin_required
def student_edit(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:students_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'school_panel/student_form.html', {'form': form, 'title': _('O\'quvchi ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def student_delete(request, pk):
    student = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='student')
    if request.method == 'POST':
        student.delete()
        return redirect('frontend_school:students_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': student, 'type': _('o\'quvchini')})

@login_required(login_url='login')
@school_admin_required
def teacher_add(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            teacher.school = request.user.school
            teacher.role = 'teacher'
            
            # 1. Save initially to get ID
            teacher.username = f"temp_t_{secrets.token_hex(4)}"
            teacher.save()
            
            # 2. Generate Smart Login: {district}_{school}_{id}
            district_part = clean_name(teacher.school.district.name if teacher.school and teacher.school.district else "no")
            school_part = clean_name(teacher.school.name if teacher.school else "school")
            
            username = f"{district_part}_{school_part}_{teacher.id}"
            teacher.username = username
            
            # 3. Generate Random Password (12 chars)
            password = form.cleaned_data.get('password')
            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))
            
            teacher.set_password(password)
            teacher.save()
            
            messages.success(request, _("Yangi o'qituvchi qo'shildi! Login: {login}, Parol: {parol}").format(login=username, parol=password))
            return redirect('frontend_school:teachers_list')
    else:
        form = TeacherForm()
    return render(request, 'school_panel/teacher_form.html', {'form': form, 'title': _('Yangi o\'qituvchi qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def teacher_edit(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:teachers_list')
    else:
        form = TeacherForm(instance=teacher)
    return render(request, 'school_panel/teacher_form.html', {'form': form, 'title': _('O\'qituvchi ma\'lumotlarini tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(CustomUser, pk=pk, school=request.user.school, role='teacher')
    if request.method == 'POST':
        teacher.delete()
        return redirect('frontend_school:teachers_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': teacher, 'type': _('o\'qituvchini')})

@login_required(login_url='login')
@school_admin_required
def news_add(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.school = request.user.school
            news.save()
            return redirect('frontend_school:news_list')
    else:
        form = NewsForm()
    return render(request, 'school_panel/news_form.html', {'form': form, 'title': _('Yangi yangilik qo\'shish')})

@login_required(login_url='login')
@school_admin_required
def news_edit(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('frontend_school:news_list')
    else:
        form = NewsForm(instance=news)
    return render(request, 'school_panel/news_form.html', {'form': form, 'title': _('Yangilikni tahrirlash')})

@login_required(login_url='login')
@school_admin_required
def news_delete(request, pk):
    news = get_object_or_404(News, pk=pk, school=request.user.school)
    if request.method == 'POST':
        news.delete()
        return redirect('frontend_school:news_list')
    return render(request, 'school_panel/confirm_delete.html', {'object': news, 'type': _('yangilikni')})

@login_required(login_url='login')
@school_admin_required
def profile(request):
    if request.user.role != 'school_admin':
        return redirect('frontend_user:library')
    school = request.user.school
    recent_activity = ActionLog.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    from django.db.models import Sum
    stats = Book.objects.filter(school=school).aggregate(
        total_copies=Sum('total_count'),
    )
    return render(request, 'school_panel/profile.html', {
        'recent_activity': recent_activity,
        'total_books': Book.objects.filter(school=school).count(),
        'total_copies': stats['total_copies'] or 0,
        'total_students': CustomUser.objects.filter(school=school, role='student').count(),
        'total_teachers': CustomUser.objects.filter(school=school, role='teacher').count(),
    })

@login_required(login_url='login')
@school_admin_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, _('Parolingiz muvaffaqiyatli o\'zgartirildi!'))
            return redirect('frontend_school:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'school_panel/password_change.html', {'form': form})

@login_required(login_url='login')
@school_admin_required
def statistics(request):
    school = request.user.school
    today = timezone.now().date()

    from django.db.models import Sum, Count
    from books.models import UserAchievement, Challenge, BookIssue

    active_students = CustomUser.objects.filter(
        school=school, role='student', is_archived=False,
        bookissue__is_returned=False
    ).distinct()[:20]
    active_count = CustomUser.objects.filter(
        school=school, role='student', is_archived=False,
        bookissue__is_returned=False
    ).distinct().count()
    top_students = CustomUser.objects.filter(
        school=school, role='student', is_archived=False
    ).order_by('-total_books_read')[:10]
    recent_yutuqlar = UserAchievement.objects.filter(
        user__school=school, user__role='student'
    ).select_related('user', 'achievement').order_by('-earned_at')[:15]
    active_chellenjlar = Challenge.objects.filter(
        is_active=True, start_date__lte=today, end_date__gte=today
    ).filter(
        Q(school=school) | Q(school__isnull=True)
    )
    total_students = CustomUser.objects.filter(school=school, role='student', is_archived=False).count()
    total_books = Book.objects.filter(school=school).count()
    total_issues = BookIssue.objects.filter(book__school=school).count()
    active_issues = BookIssue.objects.filter(book__school=school, is_returned=False).count()

    # Track which top students already have news posted today
    from .models import News
    posted_today_ids = set()
    for s in top_students:
        prefix = _("Eng faol o'quvchi: {name}").format(name=f"{s.first_name} {s.last_name}")
        if News.objects.filter(school=school, title__startswith=prefix, created_at__date=today).exists():
            posted_today_ids.add(s.pk)

    return render(request, 'school_panel/statistics.html', {
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
    })

@login_required(login_url='login')
@school_admin_required
def post_top_student_news(request, pk):
    school = request.user.school
    student = get_object_or_404(CustomUser, pk=pk, school=school, role='student')

    # Check if already posted today
    from django.utils import timezone
    from .models import News
    today = timezone.localdate()
    existing = News.objects.filter(
        school=school,
        title__startswith=_("Eng faol o'quvchi: {name}").format(name=f"{student.first_name} {student.last_name}"),
        created_at__date=today,
    ).exists()
    if existing:
        messages.warning(request, _("Bugun bu haqida yangilik allaqachon chop etilgan!"))
        return redirect('frontend_school:statistics')

    from books.models import UserAchievement
    title = _("Eng faol o'quvchi: {name}").format(name=f"{student.first_name} {student.last_name}")
    News.objects.create(
        school=school, title=title, body="", is_published=True,
        template_key='top_reader',
        template_data={
            'student': {
                'name': f"{student.first_name} {student.last_name}",
                'grade': student.grade or "—",
                'school': school.name,
            },
            'books': student.total_books_read,
            'xp': student.xp_points,
            'level': student.level,
            'streak': student.current_streak,
        },
    )
    messages.success(request, _("Yangilik muvaffaqiyatli yaratildi!"))
    return redirect('frontend_school:statistics')

@login_required(login_url='login')
@school_admin_required
def graduates_list(request):
    school = request.user.school
    query = request.GET.get('q')
    graduates = CustomUser.objects.filter(school=school, role='student', is_archived=True)

    total_graduates = graduates.count()
    total_books = Book.objects.filter(school=school).count()
    total_active = BookIssue.objects.filter(book__school=school, is_returned=False).count()

    if query:
        graduates = graduates.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(grade__icontains=query)
        )

    graduates = graduates.order_by('last_name', 'first_name')

    from django.core.paginator import Paginator
    paginator = Paginator(graduates, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'school_panel/graduates.html', {
        'graduates': page_obj, 'page_obj': page_obj, 'query': query,
        'total_graduates': total_graduates, 'total_books': total_books,
        'total_active': total_active,
    })


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
        .exclude(grade__isnull=True).exclude(grade='')
        .values_list('grade', flat=True).distinct()
    )
    def sort_grade(g):
        m = re.match(r'(\d+)', g)
        return int(m.group(1)) if m else 99
    grades_list = sorted(all_grades, key=sort_grade)
    
    # Academic years for filter
    years = TextbookLoan.objects.filter(book__school=school).values_list('academic_year', flat=True).distinct().order_by('-academic_year')
    
    from django.core.paginator import Paginator
    paginator = Paginator(loans, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/textbook_loans.html', {
        'loans': page_obj, 'page_obj': page_obj,
        'active_loans': active_loans, 'total_loans': total_loans, 'returned_loans': returned_loans,
        'grades_list': grades_list, 'selected_grade': grade_filter,
        'years': years,
    })


@login_required(login_url='login')
@school_admin_required
def textbook_distribute(request):
    import re
    import datetime
    school = request.user.school
    grade_filter = request.GET.get('grade', '')
    
    # Compute current academic year
    now = datetime.date.today()
    if now.month >= 9:
        academic_year = f"{now.year}/{now.year + 1}"
    else:
        academic_year = f"{now.year - 1}/{now.year}"
    
    # Get distinct grades
    all_grades = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True).exclude(grade='')
        .values_list('grade', flat=True).distinct()
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
            existing = TextbookLoan.objects.filter(
                student=student, book=book, academic_year=academic_year
            ).first()
            if not existing:
                TextbookLoan.objects.create(
                    book=book, student=student, academic_year=academic_year,
                    due_date=due_date, condition_on_issue='good', notes='',
                )
                created_count += 1

        if auto:
            # Auto-assign: all textbooks matching this grade to all students
            students = CustomUser.objects.filter(school=school, role='student')
            if grade_filter:
                students = students.filter(grade=grade_filter)
            for student in students:
                grade_num = int(re.match(r'(\d+)', student.grade or '0').group(1)) if re.match(r'(\d+)', student.grade or '') else None
                textbooks_for_grade = Book.objects.filter(school=school, is_textbook=True)
                if grade_num:
                    textbooks_for_grade = textbooks_for_grade.filter(grade=grade_num)
                for book in textbooks_for_grade:
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

        messages.success(request, _("{count} ta darslik tarqatildi.").format(count=created_count))
        return redirect('frontend_school:textbook_loans')
    
    # GET: show students by grade with available textbooks
    students = CustomUser.objects.filter(school=school, role='student')
    if grade_filter:
        students = students.filter(grade=grade_filter)
    
    students = sorted(students, key=lambda u: (
        int(re.match(r'(\d+)', u.grade or '99').group(1)) if re.match(r'(\d+)', u.grade or '') else 99,
        u.last_name or '', u.first_name or '',
    ))
    
    # Get textbooks that match the grade (or any if no grade filter)
    if grade_filter:
        grade_num = int(re.match(r'(\d+)', grade_filter).group(1)) if re.match(r'(\d+)', grade_filter) else None
    else:
        grade_num = None
    
    textbooks = Book.objects.filter(school=school, is_textbook=True)
    if grade_num:
        textbooks = textbooks.filter(grade=grade_num)
    textbooks = textbooks.order_by('subject', 'title')
    
    # Students who already have textbooks this year
    existing_student_ids = set(
        TextbookLoan.objects.filter(
            student__in=students, academic_year=academic_year, returned_at__isnull=True
        ).values_list('student_id', flat=True)
    )
    
    return render(request, 'school_panel/textbook_distribute.html', {
        'students': students, 'textbooks': textbooks,
        'grades_list': grades_list, 'selected_grade': grade_filter,
        'academic_year': academic_year, 'existing_loans': existing_student_ids,
    })


@login_required(login_url='login')
@school_admin_required
def textbook_collect(request):
    import re
    import datetime
    school = request.user.school
    grade_filter = request.GET.get('grade', '')
    
    loans = TextbookLoan.objects.filter(book__school=school, returned_at__isnull=True).select_related('book', 'student').order_by('student__grade', 'student__last_name')
    
    if grade_filter:
        loans = loans.filter(student__grade=grade_filter)
    
    # Distinct grades for filter
    all_grades = (
        CustomUser.objects.filter(school=school, role='student')
        .exclude(grade__isnull=True).exclude(grade='')
        .values_list('grade', flat=True).distinct()
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
        
        messages.success(request, _("{count} ta darslik qaytarib olindi.").format(count=collected))
        return redirect('frontend_school:textbook_loans')
    
    return render(request, 'school_panel/textbook_collect.html', {
        'loans': loans, 'grades_list': grades_list, 'selected_grade': grade_filter,
    })


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
    books = Book.objects.filter(school=school).order_by('title')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="books.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Sarlavha', 'Muallif', 'Kategoriya', 'Umumiy', 'Mavjud', "O'qilgan", 'Darslik'])
    for i, b in enumerate(books, 1):
        writer.writerow([i, b.title, b.author or '', b.category.name if b.category else '', b.total_count, b.available_count, b.borrow_count, 'Ha' if b.is_textbook else ''])
    return response


@login_required(login_url='login')
@school_admin_required
def export_issues_csv(request):
    import csv
    from django.http import HttpResponse
    school = request.user.school
    issues = BookIssue.objects.filter(book__school=school).select_related('book', 'user').order_by('-issued_at')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="book_issues.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Kitob', 'O\'quvchi', 'Sinf', 'Berilgan', 'Qaytarilgan', 'Holati'])
    for i, iss in enumerate(issues, 1):
        writer.writerow([
            i, iss.book.title, iss.user.get_full_name() or iss.user.username,
            iss.user.grade or '',
            iss.issued_at.strftime('%d.%m.%Y'),
            iss.returned_at.strftime('%d.%m.%Y') if iss.returned_at else '',
            'Qaytarilgan' if iss.is_returned else 'Ijarada',
        ])
    return response


@login_required(login_url='login')
@school_admin_required
def import_students_csv(request):
    if request.method != 'POST':
        return render(request, 'school_panel/csv_import.html', {
            'title': _("O'quvchilarni CSV dan import qilish"),
            'action_url': reverse('frontend_school:import_students_csv'),
            'redirect_url': reverse('frontend_school:students_list'),
        })
    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'success': False, 'errors': [_('Fayl yuklanmadi')]}, status=400)
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'success': False, 'errors': [_('Faqat CSV fayl yuklang')]}, status=400)
    school = request.user.school
    import csv, string, secrets
    decoded = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(decoded.splitlines())
    created = 0
    errors = []
    for row_num, row in enumerate(reader, 2):
        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()
        grade = row.get('grade', '').strip()
        if not first_name or not last_name or not grade:
            errors.append(_("Qator {}: ism, familiya va sinf majburiy").format(row_num))
            continue
        try:
            student = CustomUser(
                school=school, role='student',
                first_name=first_name, last_name=last_name, grade=grade,
            )
            student.username = f"temp_{secrets.token_hex(4)}"
            student.save()
            district_part = clean_name(student.school.district.name if student.school and student.school.district else "no")
            school_part = clean_name(student.school.name if student.school else "school")
            student.username = f"{district_part}_{school_part}_{student.id}"
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            student.set_password(password)
            student.save()
            created += 1
        except Exception as e:
            errors.append(_("Qator {}: {}").format(row_num, str(e)))
    if created:
        messages.success(request, _("{} ta o'quvchi muvaffaqiyatli import qilindi.").format(created))
    if errors:
        messages.warning(request, _("Importda {} ta xatolik yuz berdi.").format(len(errors)))
    return JsonResponse({'success': True, 'created': created, 'errors': errors})


@login_required(login_url='login')
@school_admin_required
def import_books_csv(request):
    if request.method != 'POST':
        return render(request, 'school_panel/csv_import.html', {
            'title': _("Kitoblarni CSV dan import qilish"),
            'action_url': reverse('frontend_school:import_books_csv'),
            'redirect_url': reverse('frontend_school:books_list'),
        })
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
            errors.append(_("Qator {}: sarlavha, umumiy soni va mavjud soni majburiy").format(row_num))
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
                school=school, title=title, author=author or None,
                category=category, total_count=total_count,
                available_count=available_count,
                description=description or '',
                is_textbook=(is_textbook_str == 'TRUE'),
            )
            book.save()
            created += 1
        except Exception as e:
            errors.append(_("Qator {}: {}").format(row_num, str(e)))
    if created:
        messages.success(request, _("{} ta kitob muvaffaqiyatli import qilindi.").format(created))
    if errors:
        messages.warning(request, _("Importda {} ta xatolik yuz berdi.").format(len(errors)))
    return JsonResponse({'success': True, 'created': created, 'errors': errors})
