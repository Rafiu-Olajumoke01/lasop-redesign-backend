from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from .models import Cohort
from .serializers import CohortSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from exams.models import Exam
from results.models import Result
from .models import ClassSession, Attendance
from .serializers import ClassSessionSerializer, AttendanceSerializer, AttendanceStudentSerializer
from tutors.permissions import IsTutor
from django.shortcuts import get_object_or_404
from tutors.permissions import IsTutor


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Anyone can view cohorts (GET), but only staff can create/edit/delete.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class CohortListCreateView(generics.ListCreateAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [IsStaffOrReadOnly]


class CohortDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [IsStaffOrReadOnly]

class CohortStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            'current_cohorts': Cohort.objects.filter(status='current').count(),
            'completed_cohorts': Cohort.objects.filter(status='completed').count(),
            'total_cohorts': Cohort.objects.count(),
            'upcoming_cohorts': Cohort.objects.filter(status='upcoming').count(),
        }
        return Response(data)
    
class DashboardStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        data = {
            'cohorts': {
                'total': Cohort.objects.count(),
                'current': Cohort.objects.filter(status='current').count(),
                'upcoming': Cohort.objects.filter(status='upcoming').count(),
                'completed': Cohort.objects.filter(status='completed').count(),
            },
            'exams': {
                'total': Exam.objects.count(),
            },
            'results': {
                'total': Result.objects.count(),
                'pending': Result.objects.filter(status='pending').count(),
                'passed': Result.objects.filter(status='passed').count(),
                'failed': Result.objects.filter(status='failed').count(),
            },
        }
        return Response(data)

class TutorClassSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = ClassSessionSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return ClassSession.objects.filter(tutor__user=self.request.user)

    def perform_create(self, serializer):
        tutor = self.request.user.tutor_profile
        serializer.save(tutor=tutor)


class SessionRosterView(APIView):
    """Returns the expected student roster for a session, so the tutor
    can mark attendance against it."""
    permission_classes = [IsTutor]

    def get(self, request, session_id):
        session = get_object_or_404(ClassSession, id=session_id, tutor__user=request.user)
        roster = session.roster
        data = AttendanceStudentSerializer(roster, many=True).data
        return Response(data)


class BulkAttendanceView(APIView):
    """POST a list of {application: id, status: 'present'|'absent'|'late'}
    for a given session. Matches your existing bulk-attendance POST pattern."""
    permission_classes = [IsTutor]

    def post(self, request, session_id):
        session = get_object_or_404(ClassSession, id=session_id, tutor__user=request.user)
        records = request.data.get('records', [])
        created = []
        for r in records:
            obj, _ = Attendance.objects.update_or_create(
                session=session,
                application_id=r['application'],
                defaults={'status': r['status']},
            )
            created.append(obj)
        return Response(AttendanceSerializer(created, many=True).data)