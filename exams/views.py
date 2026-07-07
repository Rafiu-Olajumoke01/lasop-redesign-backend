from rest_framework import generics, permissions
from .models import Exam
from .serializers import ExamSerializer


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can view exams (GET), but only staff can create/edit/delete.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class ExamListCreateView(generics.ListCreateAPIView):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsStaffOrReadOnly]


class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsStaffOrReadOnly]