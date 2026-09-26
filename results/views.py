from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Result
from .serializers import ResultSerializer


def _tutor_cohort_ids(user):
    tutor = getattr(user, 'tutor_profile', None)
    if not tutor:
        return None
    return set(tutor.cohorts.values_list('id', flat=True))


class IsStaffOrOwnCohortTutorOrOwnResult(permissions.BasePermission):
    """
    Staff can view/create/edit any result.
    Tutors can view/create/edit results only for cohorts assigned to them.
    Students can only view their own results — no write access.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if user.is_staff:
            return True
        return hasattr(user, 'tutor_profile')

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        cohort_ids = _tutor_cohort_ids(user)
        if cohort_ids is not None and obj.exam.cohort_id in cohort_ids:
            return True
        if request.method in permissions.SAFE_METHODS:
            return obj.student_id == user.id
        return False


class ResultListCreateView(generics.ListCreateAPIView):
    serializer_class = ResultSerializer
    permission_classes = [IsStaffOrOwnCohortTutorOrOwnResult]

    def get_queryset(self):
        qs = Result.objects.select_related('exam', 'exam__cohort', 'exam__course', 'student')
        user = self.request.user
        cohort_ids = _tutor_cohort_ids(user)
        if user.is_staff:
            pass
        elif cohort_ids is not None:
            qs = qs.filter(exam__cohort_id__in=cohort_ids)
        else:
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

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff:
            exam = serializer.validated_data.get('exam')
            cohort_ids = _tutor_cohort_ids(user)
            if not exam or not cohort_ids or exam.cohort_id not in cohort_ids:
                raise PermissionDenied("You can only record results for cohorts assigned to you.")
        serializer.save()


class ResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ResultSerializer
    permission_classes = [IsStaffOrOwnCohortTutorOrOwnResult]

    def get_queryset(self):
        return Result.objects.select_related('exam', 'exam__cohort', 'exam__course', 'student')