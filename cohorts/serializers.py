from rest_framework import serializers
from .models import Cohort, ClassSession, Attendance


class CohortSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)
    current_stage = serializers.CharField(read_only=True)
    current_stage_label = serializers.CharField(read_only=True)
    stage_countdown_days = serializers.IntegerField(read_only=True)
    is_learning_today = serializers.BooleanField(read_only=True)
    tutor_name = serializers.SerializerMethodField()

    class Meta:
        model = Cohort
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'status',
            'tutor',
            'tutor_name',
            'class_days',
            'student_count',
            'current_stage',
            'current_stage_label',
            'stage_countdown_days',
            'is_learning_today',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_tutor_name(self, obj):
        if obj.tutor and obj.tutor.user:
            full = f"{obj.tutor.user.first_name} {obj.tutor.user.last_name}".strip()
            return full or obj.tutor.user.email
        return None


class ClassSessionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.ReadOnlyField()
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)

    class Meta:
        model = ClassSession
        fields = [
            'id', 'cohort', 'cohort_name', 'tutor', 'topics_covered', 'project_note',
            'date', 'start_time', 'end_time', 'duration_hours', 'created_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}


class AttendanceStudentSerializer(serializers.Serializer):
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