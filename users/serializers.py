from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User
from tutors.models import Tutor


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'phone_number', 'gender']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            gender=validated_data['gender'],
            password=validated_data['password'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        return user


class AssignedTutorSerializer(serializers.ModelSerializer):
    """Small nested representation of a Tutor, shown inside a student's data
    so the frontend can display who a student's tutor is without a second
    API call."""
    name = serializers.SerializerMethodField()

    class Meta:
        model = Tutor
        fields = ['id', 'name']

    def get_name(self, obj):
        u = obj.user
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.email


class UserSerializer(serializers.ModelSerializer):
    # Read-only nested tutor info (for display)
    assigned_tutor_detail = AssignedTutorSerializer(source='assigned_tutor', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'gender',
            'is_staff', 'is_tutor', 'assigned_tutor', 'assigned_tutor_detail',
        ]
        extra_kwargs = {
            'assigned_tutor': {'write_only': True, 'required': False},
        }

class StudentDetailSerializer(UserSerializer):
    certificate = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['certificate']

    def get_certificate(self, obj):
        # Local import avoids a circular import between users <-> certificate
        from certificate.models import Certificate
        from certificate.serializers import CertificateSerializer

        cert = Certificate.objects.filter(student=obj).first()
        if not cert:
            return None
        return CertificateSerializer(cert, context=self.context).data