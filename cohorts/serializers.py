from rest_framework import serializers
from .models import Cohort, ClassSession, Attendance, StudentProject, CapstoneProject, Assessment, ClassProject



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
    attendance_marked = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = [
            'id', 'cohort', 'cohort_name', 'tutor', 'title', 'topics_covered',
            'lesson_outcome', 'date', 'start_time', 'end_time', 'duration_hours',
            'started_at', 'ended_at', 'attendance_marked', 'created_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}
        read_only_fields = ['started_at', 'ended_at']

    def get_attendance_marked(self, obj):
        return Attendance.objects.filter(session=obj).exists()


class AttendanceStudentSerializer(serializers.Serializer):
    application_id = serializers.IntegerField(source='id')
    student_id = serializers.IntegerField(source='student.id')
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

class CapstoneProjectSerializer(serializers.ModelSerializer):
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    tutor_name = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source='get_stage_display', read_only=True)

    class Meta:
        model = CapstoneProject
        fields = [
            'id', 'cohort', 'cohort_name', 'tutor', 'tutor_name',
            'stage', 'stage_label', 'title', 'description',
            'attachment', 'due_date', 'posted_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}
        read_only_fields = ['posted_at']

    def get_tutor_name(self, obj):
        if obj.tutor and obj.tutor.user:
            full = f"{obj.tutor.user.first_name} {obj.tutor.user.last_name}".strip()
            return full or obj.tutor.user.email
        return None

class StudentProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    project_type_label = serializers.CharField(source='get_project_type_display', read_only=True)

    class Meta:
        model = StudentProject
        fields = [
            'id', 'student', 'student_name', 'cohort', 'cohort_name',
            'project_type', 'project_type_label',
            'title', 'description', 'tech_stack', 'repo_url', 'live_url',
            'cover_image', 'attachment', 'status', 'tutor_feedback',
            'is_featured', 'submitted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'status', 'tutor_feedback', 'is_featured', 'submitted_at', 'created_at', 'updated_at']


class AssessmentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    cohort_name = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            'id', 'student', 'student_name', 'author', 'author_name',
            'content', 'created_at', 'updated_at',
            'student_response', 'responded_at', 'cohort_name',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'responded_at']

    def get_author_name(self, obj):
        full = f"{obj.author.first_name} {obj.author.last_name}".strip()
        return full or obj.author.email

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email

    def get_cohort_name(self, obj):
        app = obj.student.applications.filter(cohort__isnull=False).order_by('-created_at').first()
        return app.cohort.name if app else None

class PublicStudentProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    tech_stack_list = serializers.SerializerMethodField()

    class Meta:
        model = StudentProject
        fields = [
            'id', 'title', 'description', 'tech_stack_list',
            'repo_url', 'live_url', 'student_name', 'created_at',
        ]

    def get_student_name(self, obj):
        s = obj.student
        return f"{s.first_name} {s.last_name}".strip() or s.email

    def get_tech_stack_list(self, obj):
        return [t.strip() for t in (obj.tech_stack or '').split(',') if t.strip()]


class ClassProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    capstone_project_title = serializers.CharField(source='capstone_project.title', read_only=True)
    cohort_name = serializers.CharField(source='capstone_project.cohort.name', read_only=True)

    class Meta:
        model = ClassProject
        fields = [
            'id', 'capstone_project', 'capstone_project_title', 'cohort_name',
            'student', 'student_name', 'title', 'description', 'tech_stack',
            'repo_url', 'live_url', 'cover_image', 'attachment',
            'tutor_rating', 'tutor_feedback', 'is_featured',
            'submitted_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'tutor_rating', 'tutor_feedback', 'is_featured', 'submitted_at', 'updated_at']

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email


class PublicClassProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    tech_stack_list = serializers.SerializerMethodField()

    class Meta:
        model = ClassProject
        fields = [
            'id', 'title', 'description', 'tech_stack_list',
            'repo_url', 'live_url', 'student_name', 'submitted_at',
        ]

    def get_student_name(self, obj):
        s = obj.student
        return f"{s.first_name} {s.last_name}".strip() or s.email

    def get_tech_stack_list(self, obj):
        return [t.strip() for t in (obj.tech_stack or '').split(',') if t.strip()]

