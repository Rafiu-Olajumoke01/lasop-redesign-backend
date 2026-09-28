from rest_framework import serializers
from .models import Guest


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ['id', 'guest_id', 'name', 'email', 'phone_number', 'purpose', 'created_at']
        read_only_fields = ['id', 'guest_id', 'created_at']