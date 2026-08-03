from books.achievements import get_level_info, get_next_level_info
from books.models import Book, Category
from books.search import search_books
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _


@login_required(login_url='login')
def library(request):
    query = request.GET.get('q')
    page = request.GET.get('page', 1)
    if not query:
        cache_key = f'library_ids_{request.user.school_id}'
        book_ids = cache.get(cache_key)
        if book_ids is None:
            book_ids = list(
                Book.objects.select_related('school', 'category')
                .filter(school=request.user.school)
                .order_by('-borrow_count')
                .values_list('id', flat=True)
            )
            cache.set(cache_key, book_ids, 120)
        books = (
            Book.objects.select_related('school', 'category')
            .filter(id__in=book_ids)
            .select_related('category')
            .order_by('-borrow_count')
        )
    else:
        books = (
            Book.objects.select_related('school', 'category')
            .filter(school=request.user.school)
            .select_related('category')
            .order_by('-borrow_count')
        )
        books = search_books(books, query)

    paginator = Paginator(books, 24)
    try:
        books_page = paginator.page(page)
    except PageNotAnInteger:
        books_page = paginator.page(1)
    except EmptyPage:
        books_page = paginator.page(paginator.num_pages)

    categories = Category.objects.all()

    from schools.models import News

    latest_news = News.objects.filter(school=request.user.school, is_published=True).order_by('-created_at')[:3]

    from books.models import BookIssue, ReaderOfMonth
    from django.utils import timezone
    from stats.models import ActionLog

    reader_cache_key = f'reader_month_{request.user.school_id}_{timezone.now().month}'
    reader_of_month = cache.get(reader_cache_key)
    if reader_of_month is None:
        try:
            reader_of_month = (
                ReaderOfMonth.objects.filter(
                    school=request.user.school, month=timezone.now().month, year=timezone.now().year
                )
                .select_related('user')
                .first()
            )
            if reader_of_month:
                cache.set(reader_cache_key, reader_of_month, 3600)
        except Exception:
            reader_of_month = None

    active_reads = (
        BookIssue.objects.select_related('book', 'user')
        .filter(user__school=request.user.school, is_returned=False)
        .select_related('user', 'book')
        .order_by('-issued_at')[:5]
    )

    school_activity = (
        ActionLog.objects.filter(user__school=request.user.school).select_related('user').order_by('-created_at')[:10]
    )

    return render(
        request,
        'frontend/user/library.html',
        {
            'books': books_page,
            'categories': categories,
            'current_query': query or '',
            'latest_news': latest_news,
            'reader_of_month': reader_of_month,
            'active_reads': active_reads,
            'school_activity': school_activity,
        },
    )


@login_required(login_url='login')
def my_books(request):
    from books.models import BookIssue, BookRequest

    issues = (
        BookIssue.objects.select_related('book', 'user')
        .filter(user=request.user, is_returned=False)
        .select_related('book', 'book__category')
        .order_by('-issued_at')
    )
    requests = (
        BookRequest.objects.select_related('book', 'user')
        .filter(user=request.user, status='pending')
        .select_related('book', 'book__category')
        .order_by('-requested_at')
    )
    history = (
        BookIssue.objects.select_related('book', 'user')
        .filter(user=request.user, is_returned=True)
        .select_related('book', 'book__category')
        .order_by('-returned_at')
    )

    return render(request, 'frontend/user/my_books.html', {'issues': issues, 'requests': requests, 'history': history})


@login_required(login_url='login')
def news_list(request):
    from schools.models import News

    news = News.objects.filter(school=request.user.school, is_published=True).order_by('-created_at')
    return render(request, 'frontend/user/news.html', {'news_list': news})


@login_required(login_url='login')
def profile(request):
    if request.user.role == 'school_admin':
        return redirect('frontend:profile')
    if request.user.role == 'superuser' or request.user.is_superuser:
        return redirect('frontend:profile')

    import json
    from datetime import timedelta

    from books.models import Achievement, BookIssue, UserAchievement
    from django.db.models import Count
    from django.utils import timezone

    user = request.user
    level_info = get_level_info(user.level)
    next_level = get_next_level_info(user.level)
    next_xp = next_level['xp_required'] if next_level else 0
    current_xp = user.xp_points or 0

    # Books by month chart
    months_uz = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
    monthly_data = []
    for i in range(11, -1, -1):
        month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        count = (
            BookIssue.objects.select_related('book', 'user')
            .filter(user=user, issued_at__gte=month_start, issued_at__lt=month_end)
            .count()
        )
        monthly_data.append(count)

    # Category distribution
    cat_data = (
        BookIssue.objects.select_related('book', 'user')
        .filter(user=user, is_returned=True, book__category__isnull=False)
        .values('book__category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

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

    return render(
        request,
        'frontend/user/profile.html',
        {
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
        },
    )


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
        return redirect('frontend:profile')
    unlocked_icons = request.user.unlocked_icons or ['fa-book']
    return render(
        request,
        'frontend/user/profile_edit.html',
        {
            'unlocked_icons': unlocked_icons,
        },
    )


@login_required(login_url='login')
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
    return render(request, 'frontend/user/password_change.html', {'form': form})


@login_required(login_url='login')
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk, school=request.user.school)
    return render(request, 'frontend/user/book_detail.html', {'book': book})


@login_required(login_url='login')
def reserve_book(request, pk):
    import uuid

    from books.models import BookRequest
    from django.shortcuts import redirect

    # Secure: Ensure book belongs to the same school as the user
    book = get_object_or_404(Book, pk=pk, school=request.user.school)

    # Students cannot borrow textbooks (use TextbookLoan system instead)
    if request.user.role == 'student' and book.is_textbook:
        from django.contrib import messages

        messages.error(
            request, _("Darsliklarni o'quvchilar bron qila olmaydi. Darsliklar o'quv yili boshida tarqatiladi.")
        )
        return redirect('frontend:book_detail', pk=book.pk)

    # Check if already requested
    request_obj = (
        BookRequest.objects.select_related('book', 'user')
        .filter(user=request.user, book=book, status='pending')
        .first()
    )
    if not request_obj:
        request_obj = BookRequest.objects.create(user=request.user, book=book)

    if not request_obj.qr_token:
        # Generate unique token for QR if it doesn't exist
        token = f'REQ_{request_obj.id}_{uuid.uuid4().hex[:8]}'
        request_obj.qr_token = token
        request_obj.save()

    return redirect('frontend:request_qr', pk=request_obj.pk)


@login_required(login_url='login')
def request_qr(request, pk):
    import uuid

    from books.models import BookRequest
    from django.shortcuts import get_object_or_404

    request_obj = get_object_or_404(BookRequest, pk=pk, user=request.user)

    if not request_obj.qr_token:
        token = f'REQ_{request_obj.id}_{uuid.uuid4().hex[:8]}'
        request_obj.qr_token = token
        request_obj.save()

    return render(request, 'frontend/user/request_qr.html', {'request_obj': request_obj})


@login_required(login_url='login')
def issue_qr(request, pk):
    import uuid

    from books.models import BookIssue
    from django.shortcuts import get_object_or_404

    issue_obj = get_object_or_404(BookIssue, pk=pk, user=request.user)

    if not issue_obj.qr_token:
        issue_obj.qr_token = f'RET_{issue_obj.id}_{uuid.uuid4().hex[:8]}'
        issue_obj.save()

    return render(request, 'frontend/user/issue_qr.html', {'issue_obj': issue_obj})


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
    from books.models import BookIssue, BookRequest

    if type == 'request':
        get_object_or_404(BookRequest, pk=pk, user=request.user)
        return JsonResponse({'token': generate_dynamic_token('REQ', pk)})
    elif type == 'issue':
        get_object_or_404(BookIssue, pk=pk, user=request.user)
        return JsonResponse({'token': generate_dynamic_token('RET', pk)})
    return JsonResponse({'error': 'Invalid type'}, status=400)


@login_required(login_url='login')
def achievements(request):
    from books.models import Achievement, UserAchievement

    user = request.user
    earned = UserAchievement.objects.filter(user=user).select_related('achievement')
    earned_ids = set(earned.values_list('achievement_id', flat=True))
    all_ach = Achievement.objects.all()
    unlocked_icons = user.unlocked_icons or ['fa-book']

    current_xp = user.xp_points or 0
    next_level = get_next_level_info(user.level)
    next_xp = next_level['xp_required'] if next_level else 0
    if next_xp > 0:
        prev_xp = get_level_info(user.level)['xp_required']
        xp_percent = min(100, int((current_xp - prev_xp) / (next_xp - prev_xp) * 100))
    else:
        xp_percent = 100

    return render(
        request,
        'frontend/user/achievements.html',
        {
            'earned': earned,
            'earned_ids': earned_ids,
            'all_achievements': all_ach,
            'unlocked_icons': unlocked_icons,
            'next_xp': next_xp,
            'xp_percent': xp_percent,
        },
    )


@login_required(login_url='login')
def leaderboard(request):
    from django.db.models import Count

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
            from datetime import timedelta

            from django.utils import timezone

            base_q = base_q & Q(bookissue__issued_at__gte=timezone.now() - timedelta(days=7))
        students = list(
            school_students.annotate(period_books=Count('bookissue', filter=base_q)).order_by('-period_books')[:20]
        )
        cache.set(cache_key, students, 120)

    return render(
        request,
        'frontend/user/leaderboard.html',
        {
            'students': students,
            'current_period': period,
        },
    )


@login_required(login_url='login')
def my_class(request):
    from books.models import BookIssue, UserAchievement

    user = request.user
    if user.role != 'student' or not user.grade or not user.school:
        return redirect('frontend:profile')

    classmates = (
        user.__class__.objects.filter(school=user.school, role='student', grade=user.grade)
        .exclude(pk=user.pk)
        .order_by('-xp_points')
    )

    class_data = []
    for c in classmates:
        active_loans = BookIssue.objects.select_related('book', 'user').filter(user=c, is_returned=False).count()
        total_read = c.total_books_read or 0
        ach_count = UserAchievement.objects.filter(user=c).count()
        class_data.append(
            {
                'student': c,
                'active_loans': active_loans,
                'total_read': total_read,
                'achievements': ach_count,
            }
        )

    # My own stats for comparison
    my_active = BookIssue.objects.select_related('book', 'user').filter(user=user, is_returned=False).count()
    my_read = user.total_books_read or 0
    my_ach = UserAchievement.objects.filter(user=user).count()

    return render(
        request,
        'frontend/user/my_class.html',
        {
            'class_data': class_data,
            'my_active': my_active,
            'my_read': my_read,
            'my_ach': my_ach,
        },
    )


@login_required(login_url='login')
def challenges(request):
    from books.models import Challenge, UserChallenge
    from django.utils import timezone

    user = request.user
    now = timezone.now()

    active_challenges = Challenge.objects.filter(
        is_active=True, start_date__lte=now.date(), end_date__gte=now.date()
    ).filter(school__isnull=True) | Challenge.objects.filter(
        is_active=True, start_date__lte=now.date(), end_date__gte=now.date(), school=user.school
    )

    user_challenges = UserChallenge.objects.filter(user=user)
    user_chal_map = {uc.challenge_id: uc for uc in user_challenges}

    return render(
        request,
        'frontend/user/challenges.html',
        {
            'challenges': active_challenges,
            'user_challenges': user_chal_map,
        },
    )


@login_required(login_url='login')
def join_waitlist(request, book_pk):
    from books.models import Book, BookWaitlist

    book = get_object_or_404(Book, pk=book_pk)
    if book.school != request.user.school:
        messages.error(request, _('Bu kitob sizning maktabingizga tegishli emas'))  # noqa: F823
        return redirect('frontend:library')

    if book.available_count > 0:
        messages.info(request, _('Kitob mavjud, bron qilishingiz mumkin'))
        return redirect('frontend:book_detail', pk=book.pk)

    _, created = BookWaitlist.objects.get_or_create(book=book, user=request.user)
    if created:
        messages.success(request, _("Siz navbatga qo'shildingiz"))
    else:
        messages.info(request, _('Siz allaqachon navbatdasiz'))

    return redirect('frontend:book_detail', pk=book.pk)


@login_required(login_url='login')
def leave_waitlist(request, book_pk):
    from books.models import Book, BookWaitlist

    book = get_object_or_404(Book, pk=book_pk)
    deleted, _ = BookWaitlist.objects.filter(book=book, user=request.user).delete()
    if deleted:
        messages.success(request, _('Siz navbatdan chiqdingiz'))
    return redirect('frontend:book_detail', pk=book.pk)
