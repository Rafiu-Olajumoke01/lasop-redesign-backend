from rest_framework import serializers
from .models import Guest


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ['id', 'name', 'email', 'phone_number', 'purpose', 'created_at']
        read_only_fields = ['id', 'created_at']