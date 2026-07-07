from rest_framework import serializers
from .models import Result


class ResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    exam_title = serializers.CharField(source='exam.title', read_only=True)
    course_title = serializers.CharField(source='exam.course.title', read_only=True)
    cohort_name = serializers.CharField(source='exam.cohort.name', read_only=True)
    is_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = Result
        fields = [
            'id', 'exam', 'exam_title', 'course_title', 'cohort_name',
            'student', 'student_name', 'score', 'status',
            'submitted_at', 'feedback', 'is_late', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate(self, data):
        exam = data.get('exam') or getattr(self.instance, 'exam', None)
        score = data.get('score')
        if score is not None and exam is not None and score > exam.total_marks:
            raise serializers.ValidationError(
                f"Score cannot exceed total marks ({exam.total_marks})."
            )
        return data