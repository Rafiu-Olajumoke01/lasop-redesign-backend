from django.shortcuts import get_object_or_404
from django.db.models import Count
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
from django.utils import timezone
from applications.models import Application


class IsStaffOrReadOnly(permissions.BasePermission):
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
        serializer.save(tutor=tutor, started_at=timezone.now())


class SessionRosterView(APIView):
    permission_classes = [IsTutor]

    def get(self, request, session_id):
        session = get_object_or_404(ClassSession, id=session_id, tutor__user=request.user)
        roster = session.roster
        data = AttendanceStudentSerializer(roster, many=True).data

        attendance_map = {
            a.application_id: a
            for a in session.attendance_records.select_related('application__student')
        }

        for entry in data:
            att = attendance_map.get(entry['application_id'])
            entry['status'] = att.status if att else None
            entry['marked'] = att is not None

        return Response(data)

class BulkAttendanceView(APIView):
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


class StudentClassSessionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get('course')
        if not course_id:
            return Response({'detail': 'course query param is required.'}, status=400)

        application = Application.objects.filter(
            student=request.user, course_id=course_id
        ).select_related('cohort').first()

        if not application or not application.cohort:
            return Response({
                'today': [],
                'future': [],
                'completed': [],
            })

        today = timezone.now().date()
        sessions = ClassSession.objects.filter(cohort=application.cohort)

        today_sessions = sessions.filter(date=today)
        future_sessions = sessions.filter(date__gt=today)
        completed_sessions = sessions.filter(date__lt=today)

        return Response({
            'today': ClassSessionSerializer(today_sessions, many=True).data,
            'future': ClassSessionSerializer(future_sessions, many=True).data,
            'completed': ClassSessionSerializer(completed_sessions, many=True).data,
        })


class AdminCohortsTodayView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        sessions_today = ClassSession.objects.filter(date=today).select_related('cohort', 'tutor')

        data = []
        for session in sessions_today:
            attendance_taken = session.attendance_records.exists()
            data.append({
                'cohort_id': session.cohort_id,
                'cohort_name': session.cohort.name,
                'session_id': session.id,
                'tutor': session.tutor.user.get_full_name() if session.tutor else None,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'attendance_taken': attendance_taken,
            })

        return Response(data)


class AdminCohortAttendanceView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, cohort_id):
        session_id = request.query_params.get('session')

        if session_id:
            session = get_object_or_404(ClassSession, id=session_id, cohort_id=cohort_id)
        else:
            today = timezone.now().date()
            session = ClassSession.objects.filter(
                cohort_id=cohort_id, date=today
            ).order_by('-start_time').first()

            if not session:
                return Response(
                    {'detail': 'No class session today for this cohort.'},
                    status=404
                )

        roster = session.roster
        roster_data = AttendanceStudentSerializer(roster, many=True).data

        attendance_map = {
            a.application_id: a
            for a in session.attendance_records.select_related('application__student')
        }

        for entry in roster_data:
            att = attendance_map.get(entry['application_id'])
            entry['status'] = att.status if att else None
            entry['marked'] = att is not None

        return Response({
            'session': ClassSessionSerializer(session).data,
            'attendance_taken': session.attendance_records.exists(),
            'roster': roster_data,
        })


def get_todays_session(cohort_id):
    today = timezone.now().date()
    return ClassSession.objects.filter(
        cohort_id=cohort_id, date=today
    ).order_by('-start_time').first()


class AdminCohortDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, cohort_id):
        cohort = get_object_or_404(Cohort, id=cohort_id)

        status_counts = {choice: 0 for choice, _ in Application.STATUS_CHOICES}
        counted = Application.objects.filter(cohort=cohort).values('status').annotate(count=Count('id'))
        for row in counted:
            status_counts[row['status']] = row['count']

        tutor_name = None
        if cohort.tutor and cohort.tutor.user:
            full = f"{cohort.tutor.user.first_name} {cohort.tutor.user.last_name}".strip()
            tutor_name = full or cohort.tutor.user.email

        session = get_todays_session(cohort.id)
        today_data = {
            'is_learning_today': cohort.is_learning_today,
            'session': ClassSessionSerializer(session).data if session else None,
            'attendance_taken': session.attendance_records.exists() if session else False,
            'roster': None,
        }

        if session:
            roster = session.roster
            roster_data = AttendanceStudentSerializer(roster, many=True).data
            attendance_map = {
                a.application_id: a
                for a in session.attendance_records.select_related('application__student')
            }
            for entry in roster_data:
                att = attendance_map.get(entry['application_id'])
                entry['status'] = att.status if att else None
                entry['marked'] = att is not None
            today_data['roster'] = roster_data

        return Response({
            'id': cohort.id,
            'name': cohort.name,
            'status': cohort.status,
            'start_date': cohort.start_date,
            'end_date': cohort.end_date,
            'class_days': cohort.class_days,
            'current_stage_label': cohort.current_stage_label,
            'tutor_name': tutor_name,
            'student_counts': {
                'active': status_counts.get('active', 0),
                'inactive': status_counts.get('inactive', 0),
                'expelled': status_counts.get('expelled', 0),
                'withdrawn': status_counts.get('withdrawn', 0),
                'total': sum(status_counts.values()),
            },
            'today': today_data,
        })



class AdminCohortSessionsView(generics.ListAPIView):
    serializer_class = ClassSessionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        cohort_id = self.kwargs['cohort_id']
        return ClassSession.objects.filter(cohort_id=cohort_id).order_by('-date')

class StopClassSessionView(APIView):
    permission_classes = [IsTutor]

    def post(self, request, session_id):
        session = get_object_or_404(ClassSession, id=session_id, tutor__user=request.user)
        if session.ended_at:
            return Response({'detail': 'This session has already been stopped.'}, status=400)
        session.ended_at = timezone.now()
        session.save(update_fields=['ended_at'])
        return Response(ClassSessionSerializer(session).data)


class ApplicationAnalyticsView(APIView):
    """Admin-only: attendance + timeline analytics for a single Application (course)."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, application_id):
        application = get_object_or_404(
            Application.objects.select_related('cohort', 'course', 'tutor__user', 'student'),
            id=application_id
        )

        cohort = application.cohort

        attendance_qs = Attendance.objects.filter(application=application)
        present = attendance_qs.filter(status='present').count()
        absent = attendance_qs.filter(status='absent').count()
        late = attendance_qs.filter(status='late').count()
        total_marked = present + absent + late

        attendance_rate = round((present / total_marked) * 100, 1) if total_marked else None

        today = timezone.now().date()
        days_since_start = None
        days_remaining = None
        current_stage_label = None

        if cohort and cohort.start_date:
            days_since_start = (today - cohort.start_date).days
            current_stage_label = cohort.current_stage_label

        if cohort and cohort.end_date:
            days_remaining = (cohort.end_date - today).days

        total_sessions_held = ClassSession.objects.filter(cohort=cohort).count() if cohort else 0

        return Response({
            'application_id': application.id,
            'student_id': application.student_id,
            'course_title': application.course.title if application.course else None,
            'cohort': {
                'id': cohort.id if cohort else None,
                'name': cohort.name if cohort else None,
                'start_date': cohort.start_date if cohort else None,
                'end_date': cohort.end_date if cohort else None,
                'status': cohort.status if cohort else None,
            } if cohort else None,
            'tutor_id': application.tutor_id,
            'tutor_name': (
                application.tutor.user.get_full_name() or application.tutor.user.email
            ) if application.tutor and application.tutor.user else None,
            'attendance': {
                'present': present,
                'absent': absent,
                'late': late,
                'total_marked': total_marked,
                'total_sessions_held': total_sessions_held,
                'attendance_rate': attendance_rate,
            },
            'timeline': {
                'days_since_start': days_since_start,
                'days_remaining': days_remaining,
                'current_stage_label': current_stage_label,
            },
        })