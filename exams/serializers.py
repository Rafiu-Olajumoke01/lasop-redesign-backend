from rest_framework import serializers
from .models import Exam


class ExamSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'cohort',
            'cohort_name',
            'course',
            'course_title',
            'title',
            'exam_type',
            'start_date',
            'due_date',
            'total_marks',
            'pass_mark',
            'instructions',
            'is_open',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']