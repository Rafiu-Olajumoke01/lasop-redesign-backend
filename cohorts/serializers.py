from rest_framework import serializers
from .models import Cohort
from .models import Cohort, ClassSession, Attendance


class CohortSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)
    current_stage = serializers.CharField(read_only=True)
    current_stage_label = serializers.CharField(read_only=True)
    stage_countdown_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cohort
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'status',
            'student_count',
            'current_stage',
            'current_stage_label',
            'stage_countdown_days',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

class ClassSessionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.ReadOnlyField()
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)

    class Meta:
        model = ClassSession
        fields = [
        'id', 'cohort', 'cohort_name', 'tutor', 'topics_covered',
        'date', 'start_time', 'end_time', 'duration_hours', 'created_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}


class AttendanceStudentSerializer(serializers.Serializer):
    """Small nested shape for the roster — one entry per enrolled student."""
    application_id = serializers.IntegerField(source='id')
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email')

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'session', 'application', 'status', 'marked_at', 'student_name']

    def get_student_name(self, obj):
        s = obj.application.student
        full = f"{s.first_name} {s.last_name}".strip()
        return full or s.email