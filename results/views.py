from rest_framework import generics, permissions
from .models import Result
from .serializers import ResultSerializer


class IsStaffOrOwnResult(permissions.BasePermission):
    """
    Staff can view/create/edit any result.
    Students can only view their own results — no write access.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_staff or obj.student_id == request.user.id
        return request.user.is_staff


class ResultListCreateView(generics.ListCreateAPIView):
    serializer_class = ResultSerializer
    permission_classes = [IsStaffOrOwnResult]

    def get_queryset(self):
        qs = Result.objects.select_related('exam', 'exam__cohort', 'exam__course', 'student')
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(student=user)

        exam_id = self.request.query_params.get('exam')
        cohort_id = self.request.query_params.get('cohort')
        course_id = self.request.query_params.get('course')
        status_param = self.request.query_params.get('status')

        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        if cohort_id:
            qs = qs.filter(exam__cohort_id=cohort_id)
        if course_id:
            qs = qs.filter(exam__course_id=course_id)
        if status_param:
            qs = qs.filter(status=status_param)

        return qs


class ResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResultSerializer
    permission_classes = [IsStaffOrOwnResult]

    def get_queryset(self):
        return Result.objects.select_related('exam', 'exam__cohort', 'exam__course', 'student')