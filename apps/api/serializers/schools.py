from rest_framework import serializers
from schools.models import District, Institution, School, Subject


class DistrictSerializer(serializers.ModelSerializer):
    school_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = District
        fields = '__all__'


class SchoolSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)
    has_admin = serializers.BooleanField(read_only=True, default=False)
    student_count = serializers.IntegerField(read_only=True, default=0)
    book_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = School
        fields = '__all__'


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
