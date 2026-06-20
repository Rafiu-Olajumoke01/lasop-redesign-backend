from rest_framework import serializers
from .models import Application
from courses.models import Course, Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'category', 'duration', 'fee']


class ApplicationSerializer(serializers.ModelSerializer):
    course_detail = CourseSerializer(source='course', read_only=True)
    location_detail = LocationSerializer(source='location', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'student', 'course', 'course_detail', 'mode_of_learning', 'location', 'location_detail', 'created_at']
        read_only_fields = ['student', 'created_at']

