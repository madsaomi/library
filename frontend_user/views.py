from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from books.models import Book, Category
from books.search import search_books
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache

@login_required(login_url='login')
def library(request):
    query = request.GET.get('q')
    if not query:
        cache_key = f'library_ids_{request.user.school_id}'
        book_ids = cache.get(cache_key)
        if book_ids is None:
            book_ids = list(Book.objects.filter(school=request.user.school).order_by('-borrow_count').values_list('id', flat=True))
            cache.set(cache_key, book_ids, 120)
        books = Book.objects.filter(id__in=book_ids).order_by('-borrow_count')
    else:
        books = Book.objects.filter(school=request.user.school).order_by('-borrow_count')
        books = search_books(books, query)

    categories = Category.objects.all()

    from frontend_school.models import News
    latest_news = News.objects.filter(school=request.user.school, is_published=True).order_by('-created_at')[:3]

    from django.utils import timezone
    from books.models import ReaderOfMonth, BookIssue
    from stats.models import ActionLog

    reader_cache_key = f'reader_month_{request.user.school_id}_{timezone.now().month}'
    reader_of_month = cache.get(reader_cache_key)
    if reader_of_month is None:
        try:
            reader_of_month = ReaderOfMonth.objects.filter(
                school=request.user.school, month=timezone.now().month, year=timezone.now().year
            ).select_related('user').first()
            cache.set(reader_cache_key, reader_of_month, 3600)
        except ReaderOfMonth.DoesNotExist:
            reader_of_month = None

    active_reads = BookIssue.objects.filter(
        book__school=request.user.school, is_returned=False
    ).select_related('user', 'book').order_by('-issued_at')[:10]

    school_activity = ActionLog.objects.filter(
        action_type__in=['ISSUE', 'RETURN']
    ).order_by('-created_at')[:10]

    return render(request, 'user_panel/library.html', {
        'books': books,
        'categories': categories,
        'current_query': query or '',
        'latest_news': latest_news,
        'reader_of_month': reader_of_month,
        'active_reads': active_reads,
        'school_activity': school_activity,
    })

@login_required(login_url='login')
def my_books(request):
    from books.models import BookIssue, BookRequest
    issues = BookIssue.objects.filter(user=request.user, is_returned=False).order_by('-issued_at')
    requests = BookRequest.objects.filter(user=request.user, status='pending').order_by('-requested_at')
    history = BookIssue.objects.filter(user=request.user, is_returned=True).order_by('-returned_at')
    
    return render(request, 'user_panel/my_books.html', {
        'issues': issues,
        'requests': requests,
        'history': history
    })

@login_required(login_url='login')
def news_list(request):
    from frontend_school.models import News
    news = News.objects.filter(school=request.user.school, is_published=True).order_by('-created_at')
    return render(request, 'user_panel/news.html', {'news_list': news})

def get_level_info(level):
    LEVEL_TABLE = [
        (1, "Новичок", 0), (2, "Читатель", 30), (3, "Книголюб", 80),
        (4, "Начитанный", 150), (5, "Книжный червь", 250), (6, "Эрудит", 400),
        (7, "Интеллектуал", 600), (8, "Профессор", 850), (9, "Мудрец", 1200), (10, "Легенда", 2000),
    ]
    for lvl, title, xp in LEVEL_TABLE:
        if lvl == level:
            return {'level': lvl, 'title': title, 'xp_required': xp}
    return {'level': level, 'title': 'Новичок', 'xp_required': 0}

def get_next_level_xp(level):
    LEVEL_TABLE = [
        (1, "Новичок", 0), (2, "Читатель", 30), (3, "Книголюб", 80),
        (4, "Начитанный", 150), (5, "Книжный червь", 250), (6, "Эрудит", 400),
        (7, "Интеллектуал", 600), (8, "Профессор", 850), (9, "Мудрец", 1200), (10, "Легенда", 2000),
    ]
    for i, (lvl, title, xp) in enumerate(LEVEL_TABLE):
        if lvl == level:
            if i + 1 < len(LEVEL_TABLE):
                return LEVEL_TABLE[i + 1][2]
            return xp
    return 30

@login_required(login_url='login')
def profile(request):
    if request.user.role == 'school_admin':
        return redirect('frontend_school:profile')
    if request.user.role == 'superuser' or request.user.is_superuser:
        return redirect('frontend_admin:profile')

    from books.models import BookIssue, BookRequest, Achievement, UserAchievement, Category
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    import json

    user = request.user
    level_info = get_level_info(user.level)
    next_xp = get_next_level_xp(user.level)
    current_xp = user.xp_points or 0

    # Books by month chart
    months_uz = ["Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
    monthly_data = []
    for i in range(11, -1, -1):
        month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        count = BookIssue.objects.filter(user=user, issued_at__gte=month_start, issued_at__lt=month_end).count()
        monthly_data.append(count)

    # Category distribution
    cat_data = BookIssue.objects.filter(user=user, is_returned=True, book__category__isnull=False).values(
        'book__category__name').annotate(count=Count('id')).order_by('-count')

    # Achievements
    earned_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
    earned_achievement_ids = list(earned_achievements.values_list('achievement_id', flat=True))
    all_achievements = Achievement.objects.all()

    # Unlocked icons
    unlocked_icons = user.unlocked_icons or ['fa-book']
    if not unlocked_icons:
        unlocked_icons = ['fa-book']

    # XP progress
    if next_xp > 0:
        prev_xp = get_level_info(user.level)['xp_required']
        xp_percent = min(100, int((current_xp - prev_xp) / (next_xp - prev_xp) * 100))
    else:
        xp_percent = 100

    return render(request, 'user_panel/profile.html', {
        'level_info': level_info,
        'next_xp': next_xp,
        'xp_percent': xp_percent,
        'monthly_labels': json.dumps([months_uz[(timezone.now().month - 1 - i) % 12] for i in range(11, -1, -1)]),
        'monthly_data': json.dumps(monthly_data),
        'cat_labels': json.dumps([c['book__category__name'] or 'Без категории' for c in cat_data]),
        'cat_data': json.dumps([c['count'] for c in cat_data]),
        'earned_achievements': earned_achievements,
        'earned_achievement_ids': earned_achievement_ids,
        'all_achievements': all_achievements,
        'unlocked_icons': unlocked_icons,
        'xp_range': range(next_xp + 1),
    })

@login_required(login_url='login')
def profile_edit(request):
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        selected_icon = request.POST.get('selected_icon')
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if selected_icon and selected_icon in (user.unlocked_icons or ['fa-book']):
            user.selected_icon = selected_icon
        user.save()
        return redirect('frontend_user:profile')
    unlocked_icons = request.user.unlocked_icons or ['fa-book']
    return render(request, 'user_panel/profile_edit.html', {
        'unlocked_icons': unlocked_icons,
    })

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.raw_password = form.cleaned_data.get('new_password1')
            user.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Parolingiz muvaffaqiyatli o\'zgartirildi!'))
            return redirect('frontend_user:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'user_panel/password_change.html', {'form': form})

@login_required(login_url='login')
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    return render(request, 'user_panel/book_detail.html', {'book': book})

@login_required(login_url='login')
def reserve_book(request, pk):
    from books.models import BookRequest
    from django.shortcuts import redirect
    import uuid
    
    # Secure: Ensure book belongs to the same school as the user
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    
    # Check if already requested
    request_obj = BookRequest.objects.filter(user=request.user, book=book, status='pending').first()
    if not request_obj:
        request_obj = BookRequest.objects.create(user=request.user, book=book)
        
    if not request_obj.qr_token:
        # Generate unique token for QR if it doesn't exist
        token = f"REQ_{request_obj.id}_{uuid.uuid4().hex[:8]}"
        request_obj.qr_token = token
        request_obj.save()
        
    return redirect('frontend_user:request_qr', pk=request_obj.pk)

@login_required(login_url='login')
def request_qr(request, pk):
    from books.models import BookRequest
    import uuid
    from django.shortcuts import get_object_or_404
    request_obj = get_object_or_404(BookRequest, pk=pk, user=request.user)
    
    if not request_obj.qr_token:
        token = f"REQ_{request_obj.id}_{uuid.uuid4().hex[:8]}"
        request_obj.qr_token = token
        request_obj.save()
        
    return render(request, 'user_panel/request_qr.html', {'request_obj': request_obj})

@login_required(login_url='login')
def issue_qr(request, pk):
    from books.models import BookIssue
    import uuid
    from django.shortcuts import get_object_or_404
    issue_obj = get_object_or_404(BookIssue, pk=pk, user=request.user)
    
    if not issue_obj.qr_token:
        issue_obj.qr_token = f"RET_{issue_obj.id}_{uuid.uuid4().hex[:8]}"
        issue_obj.save()
        
    return render(request, 'user_panel/issue_qr.html', {'issue_obj': issue_obj})

@login_required(login_url='login')
def check_request_status(request, pk):
    from books.models import BookRequest
    request_obj = get_object_or_404(BookRequest, pk=pk, user=request.user)
    return JsonResponse({'status': request_obj.status})

@login_required(login_url='login')
def check_return_status(request, pk):
    from books.models import BookIssue
    issue_obj = get_object_or_404(BookIssue, pk=pk, user=request.user)
    return JsonResponse({'is_returned': issue_obj.is_returned})

@login_required(login_url='login')
def get_rotating_token(request, type, pk):
    from accounts.utils import generate_dynamic_token
    from books.models import BookRequest, BookIssue
    
    if type == 'request':
        get_object_or_404(BookRequest, pk=pk, user=request.user)
        return JsonResponse({'token': generate_dynamic_token('REQ', pk)})
    elif type == 'issue':
        get_object_or_404(BookIssue, pk=pk, user=request.user)
        return JsonResponse({'token': generate_dynamic_token('RET', pk)})
    return JsonResponse({'error': 'Invalid type'}, status=400)


from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse

@login_required(login_url='login')
def achievements(request):
    from books.models import Achievement, UserAchievement
    user = request.user
    earned = UserAchievement.objects.filter(user=user).select_related('achievement')
    earned_ids = set(earned.values_list('achievement_id', flat=True))
    all_ach = Achievement.objects.all()
    unlocked_icons = user.unlocked_icons or ['fa-book']

    current_xp = user.xp_points or 0
    next_xp = get_next_level_xp(user.level)
    if next_xp > 0:
        prev_xp = get_level_info(user.level)['xp_required']
        xp_percent = min(100, int((current_xp - prev_xp) / (next_xp - prev_xp) * 100))
    else:
        xp_percent = 100

    return render(request, 'user_panel/achievements.html', {
        'earned': earned,
        'earned_ids': earned_ids,
        'all_achievements': all_ach,
        'unlocked_icons': unlocked_icons,
        'next_xp': next_xp,
        'xp_percent': xp_percent,
    })


@login_required(login_url='login')
def leaderboard(request):
    from django.db.models import Count, Q, Prefetch
    from books.models import BookIssue

    user = request.user
    period = request.GET.get('period', 'all')
    cache_key = f'leaderboard_{user.school_id}_{period}'
    students = cache.get(cache_key)

    if students is None:
        school_students = user.__class__.objects.filter(school=user.school, role='student')
        base_q = Q(bookissue__is_returned=True)
        if period == 'month':
            from django.utils import timezone
            base_q = base_q & Q(bookissue__issued_at__gte=timezone.now().replace(day=1))
        elif period == 'week':
            from django.utils import timezone
            from datetime import timedelta
            base_q = base_q & Q(bookissue__issued_at__gte=timezone.now() - timedelta(days=7))
        students = list(school_students.annotate(
            period_books=Count('bookissue', filter=base_q)
        ).order_by('-period_books')[:20])
        cache.set(cache_key, students, 120)

    return render(request, 'user_panel/leaderboard.html', {
        'students': students,
        'current_period': period,
    })


@login_required(login_url='login')
def challenges(request):
    from books.models import Challenge, UserChallenge
    from django.utils import timezone

    user = request.user
    now = timezone.now()

    active_challenges = Challenge.objects.filter(
        is_active=True, start_date__lte=now.date(), end_date__gte=now.date()
    ).filter(school__isnull=True) | Challenge.objects.filter(
        is_active=True, start_date__lte=now.date(), end_date__gte=now.date(),
        school=user.school
    )

    user_challenges = UserChallenge.objects.filter(user=user)
    user_chal_map = {uc.challenge_id: uc for uc in user_challenges}

    return render(request, 'user_panel/challenges.html', {
        'challenges': active_challenges,
        'user_challenges': user_chal_map,
    })


@login_required(login_url='login')
def join_waitlist(request, book_pk):
    from books.models import Book, BookWaitlist
    book = get_object_or_404(Book, pk=book_pk)
    if book.school != request.user.school:
        messages.error(request, _("Bu kitob sizning maktabingizga tegishli emas"))
        return redirect('frontend_user:library')
    
    if book.available_count > 0:
        messages.info(request, _("Kitob mavjud, bron qilishingiz mumkin"))
        return redirect('frontend_user:book_detail', pk=book.pk)
    
    _, created = BookWaitlist.objects.get_or_create(book=book, user=request.user)
    if created:
        messages.success(request, _("Siz navbatga qo'shildingiz"))
    else:
        messages.info(request, _("Siz allaqachon navbatdasiz"))
    
    return redirect('frontend_user:book_detail', pk=book.pk)

@login_required(login_url='login')
def leave_waitlist(request, book_pk):
    from books.models import Book, BookWaitlist
    book = get_object_or_404(Book, pk=book_pk)
    deleted, _ = BookWaitlist.objects.filter(book=book, user=request.user).delete()
    if deleted:
        messages.success(request, _("Siz navbatdan chiqdingiz"))
    return redirect('frontend_user:book_detail', pk=book.pk)
