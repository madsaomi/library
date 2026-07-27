import pytest

from schools.models import Subject

pytestmark = pytest.mark.django_db


class TestDistrict:
    def test_create_district(self, district):
        assert district.name == 'Test District'
        assert str(district) == 'Test District'


class TestSchool:
    def test_create_school(self, school, district):
        assert school.name == 'Test School'
        assert school.address == '123 Test St'
        assert school.district == district
        assert str(school) == 'Test School'


class TestSubject:
    def test_create_subject(self):
        subject = Subject.objects.create(name='Mathematics')
        assert subject.name == 'Mathematics'
        assert str(subject) == 'Mathematics'
