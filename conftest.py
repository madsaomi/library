import pytest
from django.contrib.auth import get_user_model
from schools.models import School, District
from books.models import Book, Category, BookIssue, BookRequest

User = get_user_model()


@pytest.fixture
def district():
    return District.objects.create(name='Test District')


@pytest.fixture
def school(district):
    return School.objects.create(
        name='Test School',
        address='123 Test St',
        contact='+998901234567',
        district=district,
    )


@pytest.fixture
def superuser(school):
    user = User.objects.create(
        username='admin',
        email='admin@test.uz',
        role='superuser',
        is_superuser=True,
        is_staff=True,
    )
    user.set_password('admin123')
    user.save()
    return user


@pytest.fixture
def school_admin(school):
    user = User.objects.create(
        username='school_admin',
        email='school_admin@test.uz',
        role='school_admin',
        school=school,
    )
    user.set_password('admin123')
    user.save()
    return user


@pytest.fixture
def student(school):
    user = User.objects.create(
        username='student',
        email='student@test.uz',
        role='student',
        school=school,
        grade='9-A',
    )
    user.set_password('student123')
    user.save()
    return user


@pytest.fixture
def teacher(school):
    user = User.objects.create(
        username='teacher',
        email='teacher@test.uz',
        role='teacher',
        school=school,
        subject='Mathematics',
    )
    user.set_password('teacher123')
    user.save()
    return user


@pytest.fixture
def category():
    return Category.objects.create(name='Test Category')


@pytest.fixture
def book(school, category):
    return Book.objects.create(
        school=school,
        title='Test Book',
        author='Test Author',
        description='A book for testing',
        category=category,
        total_count=5,
        available_count=5,
        borrow_count=10,
    )


@pytest.fixture
def book_issue(book, student):
    return BookIssue.objects.create(
        book=book,
        user=student,
        qr_token='test-qr-token-123',
    )


@pytest.fixture
def book_request(book, student):
    return BookRequest.objects.create(
        book=book,
        user=student,
        status='pending',
    )


@pytest.fixture
def challenge(school, category):
    from books.models import Challenge

    return Challenge.objects.create(
        title='Test Challenge',
        description='Read 5 books',
        challenge_type='books_count',
        target_count=5,
        xp_reward=50,
        category=category,
        start_date='2026-01-01',
        end_date='2027-12-31',
        school=school,
        is_active=True,
    )
