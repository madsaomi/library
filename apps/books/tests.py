import pytest
from django.db.models import F

from books.models import Book

pytestmark = pytest.mark.django_db


class TestCategory:
    def test_create_category(self, category):
        assert category.name == 'Test Category'
        assert str(category) == 'Test Category'


class TestBook:
    def test_create_book(self, book):
        assert book.title == 'Test Book'
        assert book.total_count == 5
        assert book.available_count == 5
        assert book.borrow_count == 10

    def test_currently_reading_count(self, book):
        assert book.currently_reading_count == 0

    def test_currently_reading_with_issues(self, book):
        """available_count only decreases when view processes the issue"""
        assert book.currently_reading_count == 0

    def test_book_str(self, book):
        assert str(book) == 'Test Book'

    def test_available_count_race_condition_fix(self, book):
        """Test that F() updates work correctly"""
        Book.objects.filter(id=book.id).update(available_count=F('available_count') - 1)
        book.refresh_from_db()
        assert book.available_count == 4

    def test_book_belongs_to_school(self, book, school):
        assert book.school == school


class TestBookIssue:
    def test_create_issue(self, book_issue, book, student):
        assert book_issue.book == book
        assert book_issue.user == student
        assert book_issue.is_returned is False
        assert book_issue.qr_token == 'test-qr-token-123'

    def test_issue_str(self, book_issue):
        expected = f'{book_issue.book.title} -> {book_issue.user.username}'
        assert str(book_issue) == expected

    def test_return_book(self, book_issue, book):
        book_issue.is_returned = True
        book_issue.returned_at = __import__('django').utils.timezone.now()
        book_issue.save()
        assert book_issue.is_returned is True
        assert book_issue.returned_at is not None

    def test_issue_has_qr_token(self, book_issue):
        assert book_issue.qr_token is not None
        assert len(book_issue.qr_token) > 0


class TestBookRequest:
    def test_create_request(self, book_request, book, student):
        assert book_request.book == book
        assert book_request.user == student
        assert book_request.status == 'pending'

    def test_approve_request(self, book_request):
        book_request.status = 'approved'
        book_request.save()
        assert book_request.status == 'approved'

    def test_reject_request(self, book_request):
        book_request.status = 'rejected'
        book_request.save()
        assert book_request.status == 'rejected'

    def test_complete_request(self, book_request):
        book_request.status = 'completed'
        book_request.save()
        assert book_request.status == 'completed'

    def test_request_str(self, book_request):
        expected = f'Request: {book_request.book.title} by {book_request.user.username}'
        assert str(book_request) == expected


class TestAchievements:
    def test_get_level_info(self):
        from books.achievements import get_level_info

        info = get_level_info(1)
        assert info['level'] == 1
        assert info['title'] == 'Boshlang\'ich'

    def test_get_level_info_invalid(self):
        from books.achievements import get_level_info

        info = get_level_info(99)
        assert info['level'] == 99

    def test_get_next_level_info(self):
        from books.achievements import get_next_level_info

        info = get_next_level_info(1)
        assert info['level'] == 2

    def test_get_next_level_info_max(self):
        from books.achievements import get_next_level_info

        info = get_next_level_info(10)
        assert info is None

    def test_check_level_up(self, student):
        from books.achievements import check_level_up

        student.xp_points = 100
        student.level = 1
        student.save()
        result = check_level_up(student)
        assert result is True
        assert student.level == 3

    def test_check_level_up_no_change(self, student):
        from books.achievements import check_level_up

        student.xp_points = 10
        student.level = 1
        student.save()
        result = check_level_up(student)
        assert result is False

    def test_update_streak_first_time(self, student):
        from books.achievements import update_streak

        student.last_activity_date = None
        update_streak(student)
        assert student.current_streak == 1
        assert student.longest_streak == 1

    def test_update_streak_same_day(self, student):
        from datetime import date

        from books.achievements import update_streak

        student.last_activity_date = date.today()
        student.current_streak = 5
        update_streak(student)
        assert student.current_streak == 5

    def test_update_streak_too_long(self, student):
        from datetime import date, timedelta

        from books.achievements import update_streak

        student.last_activity_date = date.today() - timedelta(days=10)
        student.current_streak = 5
        update_streak(student)
        assert student.current_streak == 0

    def test_award_borrow_xp(self, student, monkeypatch):
        from books.achievements import award_xp

        monkeypatch.setattr('random.random', lambda: 0.5)
        result = award_xp(student, 'borrow')
        assert result['xp_earned'] == 10
        assert result['lucky_bonus'] is False
        assert student.total_books_read == 1

    def test_award_borrow_xp_lucky_bonus(self, student, monkeypatch):
        from books.achievements import award_xp

        monkeypatch.setattr('random.random', lambda: 0.05)
        result = award_xp(student, 'borrow')
        assert result['xp_earned'] == 25
        assert result['lucky_bonus'] is True
        assert student.total_books_read == 1

    def test_award_return_xp(self, student):
        from books.achievements import award_xp

        result = award_xp(student, 'return')
        assert result['xp_earned'] == 5

    def test_check_achievements_books_count(self, student):
        from books.models import Achievement

        ach = Achievement.objects.create(
            key='read_5',
            name='Read 5',
            description='Read 5 books',
            condition_type='books_count',
            condition_value=5,
            xp_reward=25,
        )
        student.total_books_read = 5
        student.save()
        from books.achievements import check_achievements

        earned = check_achievements(student)
        assert ach in earned
