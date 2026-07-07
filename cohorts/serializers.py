from rest_framework import serializers
from .models import Cohort


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