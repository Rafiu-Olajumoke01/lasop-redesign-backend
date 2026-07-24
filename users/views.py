from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, StudentDetailSerializer
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


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = StudentDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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