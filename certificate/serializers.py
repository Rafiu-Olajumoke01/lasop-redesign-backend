from rest_framework import serializers
from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'student', 'file', 'issued_date', 'uploaded_at', 'updated_at']
        read_only_fields = ['id', 'uploaded_at', 'updated_at']