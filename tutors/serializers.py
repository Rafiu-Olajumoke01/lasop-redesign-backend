# tutors/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Tutor

User = get_user_model()


class TutorUserSerializer(serializers.ModelSerializer):
    """Small nested serializer — just the user-account fields we need to show."""

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']


class TutorSerializer(serializers.ModelSerializer):
    """
    Full read serializer + admin-edit serializer.
    Used for: admin listing tutors, admin viewing a single tutor,
    admin editing a tutor's details.
    """
    user_detail = TutorUserSerializer(source='user', read_only=True)

    class Meta:
        model = Tutor
        fields = [
            'id', 'user', 'user_detail', 'bio', 'courses_of_instruction',
            'date_of_employment', 'performance_rating', 'profile_picture',
            'cohorts', 'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'user': {'write_only': True},
        }


class TutorCreateSerializer(serializers.ModelSerializer):
    """
    Admin-only. Creates the User account AND the Tutor profile together,
    in one step, since tutors do not self-register.
    Admin provides the tutor's name, email, and an initial password,
    which they then pass on to the tutor.
    """
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    user_detail = TutorUserSerializer(source='user', read_only=True)

    class Meta:
        model = Tutor
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'password',
            'bio', 'courses_of_instruction', 'date_of_employment',
            'performance_rating', 'profile_picture', 'cohorts',
            'user_detail', 'created_at', 'updated_at',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number', '')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            password=password,
            is_tutor=True,
        )

        tutor = Tutor.objects.create(user=user, **validated_data)
        return tutor


class TutorSelfUpdateSerializer(serializers.ModelSerializer):
    """
    Tutor-only. A tutor updating their own profile can ONLY touch these
    three fields. Everything else (performance_rating, date_of_employment,
    cohorts, etc.) stays admin-controlled and is not writable here.
    """
    class Meta:
        model = Tutor
        fields = ['bio', 'profile_picture', 'courses_of_instruction']


class TutorDashboardStatsSerializer(serializers.Serializer):
    courses = serializers.IntegerField()
    cohorts_total = serializers.IntegerField()
    cohorts_completed = serializers.IntegerField()
    cohorts_ongoing = serializers.IntegerField()
    total_hours = serializers.FloatField()
    days_absent = serializers.IntegerField()
    queries_pending = serializers.IntegerField()