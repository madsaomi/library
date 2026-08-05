import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestCustomUser:
    def test_create_superuser(self, superuser):
        assert superuser.role == 'superuser'
        assert superuser.is_superuser is True
        assert superuser.is_staff is True

    def test_create_school_admin(self, school_admin):
        assert school_admin.role == 'school_admin'
        assert school_admin.school is not None
        assert school_admin.is_superuser is False
        assert school_admin.is_staff is False

    def test_create_student(self, student):
        assert student.role == 'student'
        assert student.grade == '9-A'
        assert student.is_superuser is False

    def test_create_teacher(self, teacher):
        assert teacher.role == 'teacher'
        assert teacher.subject == 'Mathematics'

    def test_password_is_hashed(self, superuser):
        assert superuser.password != 'admin123'
        assert superuser.password.startswith(('pbkdf2_sha256$', 'bcrypt', 'scrypt', 'md5$', 'argon2'))

    def test_user_str(self, superuser):
        expected = f'{superuser.username} ({superuser.get_role_display()})'
        assert str(superuser) == expected

    def test_superuser_role_auto_sync(self, school):
        user = User.objects.create(
            username='auto_sync',
            role='student',
            is_superuser=False,
            is_staff=False,
        )
        user.role = 'superuser'
        user.save()
        user.refresh_from_db()
        assert user.is_superuser is True
        assert user.is_staff is True
