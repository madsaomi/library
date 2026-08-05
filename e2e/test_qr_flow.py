import pytest
from django.contrib.auth import get_user_model

from accounts.utils import generate_static_token
from books.models import Book, BookIssue, Category
from schools.models import District, School

User = get_user_model()


@pytest.fixture
def qr_school(django_db_blocker):
    with django_db_blocker.unblock():
        district, _ = District.objects.get_or_create(name='E2E Tuman')
        school, _ = School.objects.get_or_create(
            name='E2E QR maktab',
            defaults={'address': 'Test', 'contact': '+998901234567', 'district': district},
        )
        school_admin = User.objects.filter(username='qr_admin', role='school_admin', school=school).first()
        if not school_admin:
            school_admin = User(username='qr_admin', role='school_admin', school=school)
            school_admin.set_password('admin123')
            school_admin.save()
        student = User.objects.filter(username='qr_student', role='student', school=school).first()
        if not student:
            student = User(username='qr_student', role='student', school=school, grade='7B')
            student.set_password('student123')
            student.save()
        category, _ = Category.objects.get_or_create(name='E2E Kategoriya')
        book, _ = Book.objects.get_or_create(
            school=school,
            title='E2E Test Kitob',
            author='Test Muallif',
            defaults={
                'description': 'test',
                'category': category,
                'total_count': 3,
                'available_count': 3,
            },
        )
        return school, school_admin, student, book


@pytest.fixture
def qr_login(page, live_server_url, qr_school):
    page.goto(live_server_url + '/login/')
    page.fill('#username', 'qr_admin')
    page.fill('#password', 'admin123')
    page.click('button[type="submit"]')
    page.wait_for_url('**/school/**')
    return page


@pytest.mark.e2e
def test_qr_auto_issue_and_return(page, qr_login, live_server_url, qr_school):
    school, school_admin, student, book = qr_school
    book_token = generate_static_token('BOOK', book.id)
    student_token = generate_static_token('STU', student.id)

    page.goto(live_server_url + '/school/qr/')
    page.wait_for_timeout(500)

    def post(token):
        return page.evaluate(
            """async (args) => {
                const [url, token] = args;
                const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                    body: JSON.stringify({ token })
                });
                return resp.json();
            }""",
            [live_server_url + '/school/qr/process-unified/', token],
        )

    # Scan book -> info (pending book)
    r1 = post(book_token)
    assert r1['status'] == 'info'
    assert r1['pending'] == 'book'

    # Scan student -> auto issue
    r2 = post(student_token)
    assert r2['status'] == 'success'
    assert r2['action'] == 'issue'

    active = BookIssue.objects.filter(book=book, user=student, is_returned=False).first()
    assert active is not None

    # Scan again -> auto return
    post(book_token)
    r3 = post(student_token)
    assert r3['status'] == 'success'
    assert r3['action'] == 'return'

    book.refresh_from_db()
    assert BookIssue.objects.filter(book=book, user=student, is_returned=True).exists()
    assert book.available_count == 3


@pytest.mark.e2e
def test_qr_student_search(page, qr_login, live_server_url, qr_school):
    school, school_admin, student, book = qr_school
    page.goto(live_server_url + '/school/qr/')
    page.wait_for_timeout(500)

    result = page.evaluate(
        """async (url) => {
            const resp = await fetch(url + '/school/qr/search-students/?q=qr_student');
            return resp.json();
        }""",
        live_server_url,
    )
    assert result['status'] == 'success'
    names = [s['username'] for s in result.get('students', [])]
    assert 'qr_student' in names


@pytest.mark.e2e
def test_qr_image_endpoints(page, qr_login, live_server_url, qr_school):
    school, school_admin, student, book = qr_school
    for url in [
        f'/school/qr/book-image/{book.id}/',
        f'/school/qr/student-image/{student.id}/',
    ]:
        resp = page.request.get(live_server_url + url)
        assert resp.status == 200
        assert 'image/png' in resp.headers.get('content-type', '')
