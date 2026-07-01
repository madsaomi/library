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
from books.models import Book, BookIssue, BookRequest, Category
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
    school = request.user.school
    query = request.GET.get('q')
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
        
    students = students.order_by('last_name', 'first_name')
    
    from django.core.paginator import Paginator
    paginator = Paginator(students, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school_panel/students.html', {
        'students': page_obj, 'page_obj': page_obj, 'query': query,
        'total_students': total_students, 'reading_students': reading_students,
        'entered_today': entered_today,
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
            student.raw_password = password # Visible to admin
            student.save()
            
            messages.success(request, _("Yangi o'quvchi qo'shildi! Login: {}, Parol: {}").format(username, password))
            return redirect('frontend_school:students_list')
    else:
        form = StudentForm()
    return render(request, 'school_panel/student_form.html', {'form': form, 'title': _('Yangi o\'quvchi qo\'shish')})

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
            teacher.raw_password = password
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
            user = form.save(commit=False)
            user.raw_password = form.cleaned_data.get('new_password1')
            user.save()
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
    })

@login_required(login_url='login')
@school_admin_required
def post_top_student_news(request, pk):
    school = request.user.school
    student = get_object_or_404(CustomUser, pk=pk, school=school, role='student')
    from books.models import UserAchievement
    achievements = UserAchievement.objects.filter(user=student).select_related('achievement')
    from .models import News
    achievement_lines = ""
    for ach in achievements:
        achievement_lines += f"  • {ach.achievement.name} (+{ach.achievement.xp_reward} XP)\n"
    title = _("Eng faol o'quvchi: {name}").format(name=f"{student.first_name} {student.last_name}")
    body = _(
        "🏆 {name} — {grade}-sinf o'quvchisi\n\n"
        "📚 Jami o'qilgan kitoblar: {books}\n"
        "⭐ XP ball: {xp} ({level}-daraja)\n"
        "🎯 Yutuqlari:\n{achievements}\n\n"
        "{school} jamoasi {name}ni tabriklaydi va barcha o'quvchilarni faol kitob o'qishga chorlaydi! 📖"
    ).format(
        name=f"{student.first_name} {student.last_name}",
        grade=student.grade or "—",
        books=student.total_books_read,
        xp=student.xp_points,
        level=student.level,
        achievements=achievement_lines or "  —",
        school=school.name,
    )
    News.objects.create(school=school, title=title, body=body, is_published=True)
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
