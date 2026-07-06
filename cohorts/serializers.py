from rest_framework import serializers
from .models import Cohort


class CohortSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cohort
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'status',
            'student_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']