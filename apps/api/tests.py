import io

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from stats.models import ActionLog

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestAuth:
    def test_login_jwt(self, student):
        client = APIClient()
        resp = client.post('/api/auth/login/', {'username': 'student', 'password': 'student123'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data
        assert resp.data['user']['role'] == 'student'

    def test_login_no_credentials(self):
        client = APIClient()
        resp = client.post('/api/auth/login/', {}, format='json')
        assert resp.status_code == 400

    def test_login_invalid(self):
        client = APIClient()
        resp = client.post('/api/auth/login/', {'username': 'x', 'password': 'y'}, format='json')
        assert resp.status_code == 401

    def test_token_obtain(self, superuser):
        client = APIClient()
        resp = client.post('/api/auth/token/', {'username': 'admin', 'password': 'admin123'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_token_refresh(self, superuser):
        client = APIClient()
        resp = client.post('/api/auth/token/', {'username': 'admin', 'password': 'admin123'}, format='json')
        refresh = resp.data['refresh']
        resp = client.post('/api/auth/token/refresh/', {'refresh': refresh}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_me_authenticated(self, student):
        client = APIClient()
        resp = client.post('/api/auth/login/', {'username': 'student', 'password': 'student123'}, format='json')
        token = resp.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = client.get('/api/auth/me/')
        assert resp.status_code == 200
        assert resp.data['username'] == 'student'

    def test_me_unauthenticated(self):
        client = APIClient()
        resp = client.get('/api/auth/me/')
        assert resp.status_code == 401

    def test_logout(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post('/api/auth/logout/')
        assert resp.status_code == 200

    def test_login_superuser_redirect(self, superuser):
        client = APIClient()
        resp = client.post('/api/auth/login/', {'username': 'admin', 'password': 'admin123'}, format='json')
        assert resp.data['redirect'] == '/admin-panel/'

    def test_login_school_admin_redirect(self, school_admin):
        client = APIClient()
        resp = client.post('/api/auth/login/', {'username': 'school_admin', 'password': 'admin123'}, format='json')
        assert resp.data['redirect'] == '/school-panel/'


class TestAdminAPI:
    """Superuser endpoints"""

    def test_admin_stats(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/stats/')
        assert resp.status_code == 200
        assert 'school_count' in resp.data

    def test_admin_schools_list(self, superuser, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/schools/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_admin_schools_list_unauthorized(self, student, school):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/admin/schools/')
        assert resp.status_code == 403

    def test_admin_districts_list(self, superuser, district):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/districts/')
        assert resp.status_code == 200

    def test_admin_users_list(self, superuser, student, teacher, school_admin):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/users/')
        assert resp.status_code == 200

    def test_admin_books_list(self, superuser, book):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/books/')
        assert resp.status_code == 200

    def test_admin_loans_list(self, superuser, book_issue):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/loans/')
        assert resp.status_code == 200

    def test_admin_logs(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/logs/')
        assert resp.status_code == 200

    def test_admin_schools_filter_by_district(self, superuser, district, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get(f'/api/admin/schools/?district={district.id}')
        assert resp.status_code == 200

    def test_admin_schools_search(self, superuser, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/schools/?q=Test')
        assert resp.status_code == 200

    def test_admin_schools_brief(self, superuser, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/schools/brief/')
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_admin_schools_create(self, superuser, district):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post(
            '/api/admin/schools/',
            {'name': 'New School', 'address': 'Addr', 'contact': '+998', 'district': district.id},
            format='json',
        )
        assert resp.status_code == 201

    def test_admin_district_create(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post('/api/admin/districts/', {'name': 'New District'}, format='json')
        assert resp.status_code == 201

    def test_admin_institutions_list(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/institutions/')
        assert resp.status_code == 200

    def test_admin_institution_create(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post('/api/admin/institutions/', {'name': 'New Inst', 'address': 'Addr'}, format='json')
        assert resp.status_code == 201

    def test_admin_users_filter_role(self, superuser, student, teacher):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/users/?role=student')
        assert resp.status_code == 200

    def test_admin_users_filter_school(self, superuser, student, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get(f'/api/admin/users/?school={school.id}')
        assert resp.status_code == 200

    def test_admin_users_search(self, superuser, student):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/users/?q=student')
        assert resp.status_code == 200

    def test_admin_users_stats(self, superuser, student, teacher):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/users/stats/')
        assert resp.status_code == 200
        assert resp.data.get('student')

    def test_admin_admins_list(self, superuser, school_admin):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/admins/')
        assert resp.status_code == 200

    def test_admin_admin_create(self, superuser, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post(
            '/api/admin/admins/',
            {'username': 'newadmin', 'password': 'pass12345', 'school': school.id},
            format='json',
        )
        assert resp.status_code == 201

    def test_admin_loans_filter_returned(self, superuser, book_issue):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/loans/?returned=0')
        assert resp.status_code == 200

    def test_admin_loans_filter_school(self, superuser, book_issue, school):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get(f'/api/admin/loans/?school={school.id}')
        assert resp.status_code == 200

    def test_admin_recent_logs(self, superuser):
        ActionLog.objects.create(user=superuser, action_type='LOGIN', message='test')
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/stats/recent_logs/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1


class TestSchoolAPI:
    """School admin endpoints"""

    def test_school_dashboard(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/dashboard/')
        assert resp.status_code == 200

    def test_school_students_list(self, school_admin, student):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/students/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_school_students_list_unauthorized(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/school/students/')
        assert resp.status_code == 403

    def test_school_student_create(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post(
            '/api/school/students/',
            {
                'username': 'newstudent',
                'first_name': 'New',
                'last_name': 'Student',
                'password': 'testpass123',
            },
            format='json',
        )
        assert resp.status_code == 201
        assert User.objects.filter(username='newstudent').exists()

    def test_school_teachers_list(self, school_admin, teacher):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/teachers/')
        assert resp.status_code == 200

    def test_school_books_list(self, school_admin, book):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/books/')
        assert resp.status_code == 200

    def test_school_book_create(self, school_admin, category):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post(
            '/api/school/books/',
            {
                'title': 'New Book',
                'author': 'Author',
                'description': 'Desc',
                'total_count': 3,
                'available_count': 3,
            },
            format='json',
        )
        assert resp.status_code == 201

    def test_school_issues_list(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/issues/')
        assert resp.status_code == 200

    def test_school_history(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/history/')
        assert resp.status_code == 200

    def test_school_stats(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/stats/')
        assert resp.status_code == 200

    def test_school_textbooks(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/textbooks/')
        assert resp.status_code == 200

    def test_school_graduates(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/graduates/')
        assert resp.status_code == 200

    def test_school_qr_issue_missing_token(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post('/api/school/qr/issue/', {}, format='json')
        assert resp.status_code == 400

    def test_school_qr_issue(self, school_admin, book_request):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        book_request.status = 'approved'
        book_request.qr_token = 'test-issue-qr'
        book_request.save()
        resp = client.post('/api/school/qr/issue/', {'token': 'test-issue-qr'}, format='json')
        assert resp.status_code == 200

    def test_school_qr_return_missing_params(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post('/api/school/qr/return_book/', {}, format='json')
        assert resp.status_code == 400

    def test_school_qr_return_by_issue_id(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post('/api/school/qr/return_book/', {'issue_id': book_issue.id}, format='json')
        assert resp.status_code == 200

    def test_school_qr_unified_no_token(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post('/api/school/qr/unified/', {}, format='json')
        assert resp.status_code == 400

    def test_school_qr_unified_request(self, school_admin, book_request):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        book_request.status = 'approved'
        book_request.qr_token = f'qr-{book_request.id}'
        book_request.save()
        token = f'request_{book_request.id}:x'
        resp = client.post('/api/school/qr/unified/', {'token': token}, format='json')
        assert resp.status_code == 200

    def test_school_qr_unified_issue_return(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        token = f'issue_{book_issue.id}:x'
        book_issue.is_returned = False
        book_issue.qr_token = token
        book_issue.save()
        resp = client.post('/api/school/qr/unified/', {'token': token}, format='json')
        assert resp.status_code == 200

    def test_school_csv_export_students(self, school_admin, student):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/export/students/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'

    def test_school_csv_export_books(self, school_admin, book):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/export/books/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'

    def test_school_csv_import_students(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        csv_content = 'Username,First Name,Last Name,Grade\nimp1,Imp,One,5-A\nimp2,Imp,Two,6-B\n'
        resp = client.post(
            '/api/school/import/students/',
            {'file': io.BytesIO(csv_content.encode('utf-8-sig'))},
            format='multipart',
        )
        assert resp.status_code == 200
        assert resp.data['imported'] == 2

    def test_school_csv_import_books(self, school_admin, category):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        csv_content = (
            'Title,Author,Category,Total,Available\nBook1,Auth1,Test Category,10,10\nBook2,Auth2,Test Category,5,5\n'
        )
        resp = client.post(
            '/api/school/import/books/',
            {'file': io.BytesIO(csv_content.encode('utf-8-sig'))},
            format='multipart',
        )
        assert resp.status_code == 200
        assert resp.data['imported'] == 2

    def test_school_import_no_file(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post('/api/school/import/students/', {}, format='multipart')
        assert resp.status_code == 400

    def test_school_students_filter_grade(self, school_admin, student):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/students/?grade=9-A')
        assert resp.status_code == 200

    def test_school_books_filter_category(self, school_admin, book, category):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get(f'/api/school/books/?category={category.id}')
        assert resp.status_code == 200

    def test_school_books_search(self, school_admin, book):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/books/?q=Test')
        assert resp.status_code == 200

    def test_school_issues_filter_returned(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/issues/?returned=0')
        assert resp.status_code == 200

    def test_school_history_filter(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/history/?q=Test')
        assert resp.status_code == 200

    def test_school_teacher_create(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.post(
            '/api/school/teachers/',
            {'username': 'newteacher', 'first_name': 'New', 'last_name': 'Teacher', 'password': 'pass12345'},
            format='json',
        )
        assert resp.status_code == 201

    def test_school_textbooks_filter_returned(self, school_admin, book):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/textbooks/?returned=0')
        assert resp.status_code == 200


class TestUserAPI:
    """Student/teacher endpoints"""

    def test_catalog_list(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/')
        assert resp.status_code == 200

    def test_catalog_categories(self, student, category):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/categories/')
        assert resp.status_code == 200

    def test_catalog_search(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/?q=Test')
        assert resp.status_code == 200
        assert len(resp.data['results']) >= 1

    def test_my_books(self, student, book_issue):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/my-books/')
        assert resp.status_code == 200
        assert 'active' in resp.data
        assert len(resp.data['active']) >= 1

    def test_reading_summary(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/my-books/reading_summary/')
        assert resp.status_code == 200
        assert 'xp_points' in resp.data

    def test_profile(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/profile/')
        assert resp.status_code == 200

    def test_achievements_list(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/achievements/')
        assert resp.status_code == 200

    def test_challenges_list(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/challenges/')
        assert resp.status_code == 200

    def test_leaderboard(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/leaderboard/')
        assert resp.status_code == 200

    def test_my_rank(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/leaderboard/my_rank/')
        assert resp.status_code == 200
        assert 'rank' in resp.data

    def test_my_class(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/my-class/')
        assert resp.status_code == 200

    def test_news(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/news/')
        assert resp.status_code == 200

    def test_waitlist_empty(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/waitlist/')
        assert resp.status_code == 200

    def test_join_waitlist(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post(f'/api/library/books/{book.id}/join_waitlist/')
        assert resp.status_code == 200

    def test_leave_waitlist(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        client.post(f'/api/library/books/{book.id}/join_waitlist/')
        resp = client.post(f'/api/library/books/{book.id}/leave_waitlist/')
        assert resp.status_code == 200

    def test_reserve_book(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post(f'/api/library/books/{book.id}/reserve/')
        assert resp.status_code == 200

    def test_book_detail(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get(f'/api/library/books/{book.id}/')
        assert resp.status_code == 200

    def test_catalog_category_filter(self, student, book, category):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get(f'/api/library/catalog/?category={category.id}')
        assert resp.status_code == 200

    def test_catalog_textbook_filter(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/?textbook=1')
        assert resp.status_code == 200

    def test_catalog_active_reads(self, student, book_issue):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/active_reads/')
        assert resp.status_code == 200

    def test_catalog_reader_of_month(self, student, school):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/catalog/reader_of_month/')
        assert resp.status_code == 200

    def test_my_profile(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/profile/')
        assert resp.status_code == 200

    def test_update_profile(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.patch('/api/library/profile/update_profile/', {'first_name': 'Updated'}, format='json')
        assert resp.status_code == 200
        student.refresh_from_db()
        assert student.first_name == 'Updated'

    def test_change_password_wrong(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post(
            '/api/library/profile/change_password/',
            {
                'old_password': 'wrong',
                'new_password1': 'new123',
                'new_password2': 'new123',
            },
            format='json',
        )
        assert resp.status_code == 400

    def test_achievements_my(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/achievements/my/')
        assert resp.status_code == 200

    def test_join_challenge(self, student, challenge):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post(f'/api/library/challenges/{challenge.id}/join/')
        assert resp.status_code == 200

    def test_join_challenge_twice(self, student, challenge):
        client = APIClient()
        client.force_authenticate(user=student)
        client.post(f'/api/library/challenges/{challenge.id}/join/')
        resp = client.post(f'/api/library/challenges/{challenge.id}/join/')
        assert resp.status_code == 400

    def test_challenges_my(self, student, challenge):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/challenges/my/')
        assert resp.status_code == 200

    def test_leaderboard_monthly(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/leaderboard/?period=monthly')
        assert resp.status_code == 200

    def test_my_class_no_grade(self, student):
        client = APIClient()
        student.grade = None
        student.save()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/my-class/')
        assert resp.status_code == 400

    def test_waitlist_leave(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        client.post(f'/api/library/books/{book.id}/join_waitlist/')
        resp = client.delete('/api/library/waitlist/leave/', {'book_id': book.id}, format='json')
        assert resp.status_code == 200

    def test_waitlist_leave_no_id(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.delete('/api/library/waitlist/leave/', {}, format='json')
        assert resp.status_code == 400

    def test_book_reserve_unavailable(self, student, book):
        book.available_count = 0
        book.save()
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.post(f'/api/library/books/{book.id}/reserve/')
        assert resp.status_code == 400

    def test_book_waitlist_info(self, student, book):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get(f'/api/library/books/{book.id}/waitlist_info/')
        assert resp.status_code == 200
        assert resp.data['queue_length'] == 0

    def test_news_empty(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/news/')
        assert resp.status_code == 200

    def test_my_books_history_empty(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/library/my-books/')
        assert resp.status_code == 200
        assert resp.data['active'] == []


class TestReports:
    def test_school_report_students_csv(self, school_admin, student):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/reports/students/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv; charset=utf-8-sig'

    def test_school_report_teachers_xlsx(self, school_admin, teacher):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/reports/teachers/?output=xlsx')
        assert resp.status_code == 200, resp.content
        assert 'spreadsheetml' in resp['Content-Type']

    def test_school_report_books_pdf(self, school_admin, book):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/reports/books/?output=pdf')
        assert resp.status_code == 200, resp.content
        assert resp['Content-Type'] == 'application/pdf'

    def test_school_report_issues_csv(self, school_admin, book_issue):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/reports/issues/')
        assert resp.status_code == 200

    def test_school_report_stats_xlsx(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/school/reports/stats/?output=xlsx')
        assert resp.status_code == 200, resp.content

    def test_admin_report_stats_pdf(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/reports/admin_stats/?output=pdf')
        assert resp.status_code == 200, resp.content
        assert resp['Content-Type'] == 'application/pdf'

    def test_report_unauthorized(self):
        client = APIClient()
        resp = client.get('/api/school/reports/students/')
        assert resp.status_code == 401

    def test_report_forbidden_student(self, student):
        client = APIClient()
        client.force_authenticate(user=student)
        resp = client.get('/api/school/reports/students/')
        assert resp.status_code == 403

    def test_report_forbidden_school_admin_admin_report(self, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        resp = client.get('/api/admin/reports/admin_stats/')
        assert resp.status_code == 403
