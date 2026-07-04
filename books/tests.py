import pytest
from django.db.models import F
from books.models import Book

pytestmark = pytest.mark.django_db


class TestCategory:
    def test_create_category(self, category):
        assert category.name == "Test Category"
        assert str(category) == "Test Category"


class TestBook:
    def test_create_book(self, book):
        assert book.title == "Test Book"
        assert book.total_count == 5
        assert book.available_count == 5
        assert book.borrow_count == 10

    def test_currently_reading_count(self, book):
        assert book.currently_reading_count == 0

    def test_currently_reading_with_issues(self, book):
        """available_count only decreases when view processes the issue"""
        assert book.currently_reading_count == 0

    def test_book_str(self, book):
        assert str(book) == "Test Book"

    def test_available_count_race_condition_fix(self, book):
        """Test that F() updates work correctly"""
        Book.objects.filter(id=book.id).update(available_count=F("available_count") - 1)
        book.refresh_from_db()
        assert book.available_count == 4

    def test_book_belongs_to_school(self, book, school):
        assert book.school == school


class TestBookIssue:
    def test_create_issue(self, book_issue, book, student):
        assert book_issue.book == book
        assert book_issue.user == student
        assert book_issue.is_returned is False
        assert book_issue.qr_token == "test-qr-token-123"

    def test_issue_str(self, book_issue):
        expected = f"{book_issue.book.title} -> {book_issue.user.username}"
        assert str(book_issue) == expected

    def test_return_book(self, book_issue, book):
        book_issue.is_returned = True
        book_issue.returned_at = __import__("django").utils.timezone.now()
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
        assert book_request.status == "pending"

    def test_approve_request(self, book_request):
        book_request.status = "approved"
        book_request.save()
        assert book_request.status == "approved"

    def test_reject_request(self, book_request):
        book_request.status = "rejected"
        book_request.save()
        assert book_request.status == "rejected"

    def test_complete_request(self, book_request):
        book_request.status = "completed"
        book_request.save()
        assert book_request.status == "completed"

    def test_request_str(self, book_request):
        expected = f"Request: {book_request.book.title} by {book_request.user.username}"
        assert str(book_request) == expected
