from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Exam
from .serializers import ExamSerializer


def _tutor_cohort_ids(user):
    tutor = getattr(user, 'tutor_profile', None)
    if not tutor:
        return None
    return set(tutor.cohorts.values_list('id', flat=True))


class IsStaffOrOwnCohortTutor(permissions.BasePermission):
    """
    Anyone can view exams (GET). Staff can create/edit/delete any exam.
    Tutors can create/edit/delete exams only for cohorts assigned to them.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_staff:
            return True
        return hasattr(user, 'tutor_profile')

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_staff:
            return True
        cohort_ids = _tutor_cohort_ids(user)
        return cohort_ids is not None and obj.cohort_id in cohort_ids


class ExamListCreateView(generics.ListCreateAPIView):
    serializer_class = ExamSerializer
    permission_classes = [IsStaffOrOwnCohortTutor]

    def get_queryset(self):
        qs = Exam.objects.select_related('cohort', 'course').all()
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            cohort_ids = _tutor_cohort_ids(user)
            if cohort_ids is not None:
                qs = qs.filter(cohort_id__in=cohort_ids)
        cohort_id = self.request.query_params.get('cohort')
        course_id = self.request.query_params.get('course')
        if cohort_id:
            qs = qs.filter(cohort_id=cohort_id)
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff:
            cohort = serializer.validated_data.get('cohort')
            cohort_ids = _tutor_cohort_ids(user)
            if not cohort or not cohort_ids or cohort.id not in cohort_ids:
                raise PermissionDenied("You can only create exams for cohorts assigned to you.")
        serializer.save()


class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsStaffOrOwnCohortTutor]