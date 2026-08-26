from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, StudentDetailSerializer, ProfileUpdateSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from tutors.models import Tutor


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Account created successfully',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentListView(APIView):
    """Admin-only: list every student (User where is_tutor=False),
    regardless of how they enrolled (website signup or manually added)."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = User.objects.filter(is_tutor=False, is_staff=False).order_by('first_name', 'last_name')
        serializer = UserSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AssignTutorView(APIView):
    """Admin-only: assign (or unassign) a tutor for a given student."""
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        try:
            student = User.objects.get(id=user_id, is_tutor=False)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        tutor_id = request.data.get('assigned_tutor', None)

        if tutor_id in (None, '', 'null'):
            student.assigned_tutor = None
        else:
            try:
                tutor = Tutor.objects.get(id=tutor_id)
            except Tutor.DoesNotExist:
                return Response({'error': 'Tutor not found'}, status=status.HTTP_404_NOT_FOUND)
            student.assigned_tutor = tutor

        student.save()
        serializer = UserSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class StudentDetailView(APIView):
    """Admin-only: full details of a single student, including certificate status."""
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            student = User.objects.get(id=user_id, is_tutor=False, is_staff=False)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentDetailSerializer(student, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists — always return success
            return Response({'message': 'If that email exists, a reset link has been sent'}, status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        send_mail(
            subject='Reset your LASOP password',
            message=f'Click the link to reset your password: {reset_link}\n\nThis link expires soon. If you didn\'t request this, ignore this email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({'message': 'If that email exists, a reset link has been sent'}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired reset link'}, status=status.HTTP_400_BAD_REQUEST)

        new_password = request.data.get('new_password')
        if not new_password or len(new_password) < 6:
            return Response({'error': 'Password must be at least 6 characters'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password reset successful'}, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = StudentDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                StudentDetailSerializer(request.user, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)