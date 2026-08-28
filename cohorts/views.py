from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from rest_framework import generics, permissions
from .serializers import CohortSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .serializers import PublicStudentProjectSerializer
from exams.models import Exam
from results.models import Result
from .models import Cohort, ClassSession, Attendance, CapstoneProject, Assessment, ClassProject
from .serializers import (
    ClassSessionSerializer,
    AttendanceSerializer,
    AttendanceStudentSerializer,
    CapstoneProjectSerializer,
    AssessmentSerializer,
    ClassProjectSerializer,
    PublicClassProjectSerializer,
)
from tutors.permissions import IsTutor
from django.utils import timezone
from applications.models import Application
from rest_framework.exceptions import PermissionDenied
from .models import StudentProject
from .serializers import StudentProjectSerializer
from itertools import chain


def is_tutor_assigned_to_student(tutor_profile, student):
    """
    A tutor is assigned to a student if the student's Application's cohort
    is one of the tutor's cohorts (Tutor.cohorts M2M) — this is the real
    source of truth. Application.tutor / Cohort.tutor are kept as extra
    checks in case they're set elsewhere, but they are not reliable alone.
    """
    return Application.objects.filter(student=student).filter(
        Q(tutor=tutor_profile) |
        Q(cohort__tutor=tutor_profile) |
        Q(cohort__in=tutor_profile.cohorts.all())
    ).exists()


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
        serializer.save(
            tutor=tutor,
            started_at=timezone.now(),
            start_latitude=self.request.data.get('latitude') or None,
            start_longitude=self.request.data.get('longitude') or None,
        )

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
        session.end_latitude = request.data.get('latitude') or None
        session.end_longitude = request.data.get('longitude') or None
        session.save(update_fields=['ended_at', 'end_latitude', 'end_longitude'])
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

        student_name = None
        if application.student:
            student_name = application.student.get_full_name() or application.student.email

        return Response({
            'application_id': application.id,
            'student_id': application.student_id,
            'student_name': student_name,
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


class TutorCapstoneProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = CapstoneProjectSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return CapstoneProject.objects.filter(tutor__user=self.request.user)

    def perform_create(self, serializer):
        tutor = self.request.user.tutor_profile
        serializer.save(tutor=tutor)


class StudentCapstoneProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get('course')
        if not course_id:
            return Response({'detail': 'course query param is required.'}, status=400)

        application = Application.objects.filter(
            student=request.user, course_id=course_id
        ).select_related('cohort').first()

        if not application or not application.cohort:
            return Response([])

        projects = CapstoneProject.objects.filter(cohort=application.cohort)
        return Response(CapstoneProjectSerializer(projects, many=True).data)

class TutorAssessmentListCreateView(generics.ListCreateAPIView):
    """Tutor: list assessments they've posted, and post a new one."""
    serializer_class = AssessmentSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        return Assessment.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        tutor_profile = self.request.user.tutor_profile
        student = serializer.validated_data.get('student')

        if not is_tutor_assigned_to_student(tutor_profile, student):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only assess your assigned students.")

        serializer.save(author=self.request.user)


class AdminAssessmentListCreateView(generics.ListCreateAPIView):
    """Admin: list all assessments, and post a new one for any student."""
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Assessment.objects.select_related('student', 'author').order_by('-created_at')
        cohort_id = self.request.query_params.get('cohort')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        today = self.request.query_params.get('today')

        if cohort_id:
            qs = qs.filter(student__applications__cohort_id=cohort_id).distinct()
        if today == 'true':
            qs = qs.filter(created_at__date=timezone.now().date())
        else:
            if year:
                qs = qs.filter(created_at__year=year)
            if month:
                qs = qs.filter(created_at__month=month)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class StudentAssessmentsView(APIView):
    """Student: view all assessments posted to them (for their dashboard)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        assessments = Assessment.objects.filter(student=request.user)
        return Response(AssessmentSerializer(assessments, many=True).data)


class AssessmentRespondView(APIView):
    """Student: add or edit their (optional) response to an assessment. Not locked — editable anytime."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, assessment_id):
        assessment = get_object_or_404(Assessment, id=assessment_id, student=request.user)

        assessment.student_response = request.data.get('student_response', '')
        assessment.responded_at = timezone.now()
        assessment.save(update_fields=['student_response', 'responded_at'])

        return Response(AssessmentSerializer(assessment).data)


class AdminOrTutorStudentAssessmentsView(APIView):
    """Admin/Tutor: view all assessments for one specific student (e.g. on the student detail page)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id):
        user = request.user
        if not (user.is_staff or user.is_superuser or user.is_tutor):
            return Response({'detail': 'Not allowed.'}, status=403)

        assessments = Assessment.objects.filter(student_id=student_id)

        # tutor can only view assessments for students on their own assigned cohorts
        if user.is_tutor and not (user.is_staff or user.is_superuser):
            tutor_profile = user.tutor_profile
            assessments = assessments.filter(
                Q(student__applications__cohort__tutor=tutor_profile) |
                Q(student__applications__tutor=tutor_profile) |
                Q(student__applications__cohort__in=tutor_profile.cohorts.all())
            ).distinct()

        return Response(AssessmentSerializer(assessments, many=True).data)


class TutorStudentsListView(APIView):
    """
    Tutor: list every student across the tutor's own cohorts (Tutor.cohorts M2M).
    This is the 'Students' tab — independent of roster/attendance/class sessions.
    From here the tutor can act on a student directly (e.g. send an assessment)
    without needing to have taken attendance for them first.
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor_profile = request.user.tutor_profile
        applications = Application.objects.filter(
            cohort__in=tutor_profile.cohorts.all()
        ).select_related('student', 'cohort')

        data = AttendanceStudentSerializer(applications, many=True).data
        for entry, app in zip(data, applications):
            entry['cohort_id'] = app.cohort_id
            entry['cohort_name'] = app.cohort.name if app.cohort else None

        return Response(data)


class StudentProjectListCreateView(generics.ListCreateAPIView):
    """Student: list their own projects, and post a new one."""
    serializer_class = StudentProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentProject.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class StudentProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Student: view/edit/delete their own project. Locked once reviewed."""
    serializer_class = StudentProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentProject.objects.filter(student=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status == 'submitted':
            raise PermissionDenied("This project has already been reviewed and can no longer be edited.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status == 'submitted':
            raise PermissionDenied("This project has already been reviewed and can no longer be deleted.")
        instance.delete()


class StudentProjectSubmitView(APIView):
    """Student: move a project from draft -> submitted."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(StudentProject, id=project_id, student=request.user)
        if project.status != 'draft':
            return Response({'detail': 'This project has already been submitted.'}, status=400)
        project.status = 'submitted'
        project.submitted_at = timezone.now()
        project.save(update_fields=['status', 'submitted_at'])
        return Response(StudentProjectSerializer(project).data)


class TutorStudentProjectsListView(generics.ListAPIView):
    """Tutor: view projects from students on their assigned cohorts."""
    serializer_class = StudentProjectSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        tutor_profile = self.request.user.tutor_profile
        return StudentProject.objects.filter(
            Q(student__applications__cohort__tutor=tutor_profile) |
            Q(student__applications__tutor=tutor_profile) |
            Q(student__applications__cohort__in=tutor_profile.cohorts.all())
        ).distinct()


class TutorStudentProjectFeedbackView(APIView):
    """Tutor: leave feedback on a submitted project, marks it reviewed."""
    permission_classes = [IsTutor]

    def patch(self, request, project_id):
        project = get_object_or_404(StudentProject, id=project_id)
        tutor_profile = request.user.tutor_profile

        if not is_tutor_assigned_to_student(tutor_profile, project.student):
            raise PermissionDenied("You can only give feedback to your assigned students.")

        project.tutor_feedback = request.data.get('tutor_feedback', project.tutor_feedback)
        project.status = 'submitted'
        project.save(update_fields=['tutor_feedback', 'status'])
        return Response(StudentProjectSerializer(project).data)


class AdminStudentProjectListView(generics.ListAPIView):
    """Admin: view every student project."""
    serializer_class = StudentProjectSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = StudentProject.objects.all()


class AdminStudentProjectFeatureToggleView(APIView):
    """Admin: toggle whether a project shows on the public homepage showcase."""
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, project_id):
        project = get_object_or_404(StudentProject, id=project_id)
        project.is_featured = not project.is_featured
        project.save(update_fields=['is_featured'])
        return Response(StudentProjectSerializer(project).data)


class StudentClassProjectListCreateView(generics.ListCreateAPIView):
    """Student: list their own monthly-project submissions, and submit a new one."""
    serializer_class = ClassProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ClassProject.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        capstone_project = serializer.validated_data.get('capstone_project')
        is_in_cohort = Application.objects.filter(
            student=self.request.user, cohort=capstone_project.cohort
        ).exists()
        if not is_in_cohort:
            raise PermissionDenied("You can only submit to a project posted to your own cohort.")
        serializer.save(student=self.request.user)


class StudentCohortCapstoneProjectsView(APIView):
    """Student: list the monthly project briefs posted to their cohort, so they know what to attempt."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        course_id = request.query_params.get('course')
        if not course_id:
            return Response({'detail': 'course query param is required.'}, status=400)

        application = Application.objects.filter(
            student=request.user, course_id=course_id
        ).select_related('cohort').first()

        if not application or not application.cohort:
            return Response([])

        briefs = CapstoneProject.objects.filter(cohort=application.cohort)
        return Response(CapstoneProjectSerializer(briefs, many=True).data)


class TutorClassProjectListView(generics.ListAPIView):
    """Tutor: view student submissions against monthly project briefs on their cohorts."""
    serializer_class = ClassProjectSerializer
    permission_classes = [IsTutor]

    def get_queryset(self):
        tutor_profile = self.request.user.tutor_profile
        return ClassProject.objects.filter(
            capstone_project__cohort__in=tutor_profile.cohorts.all()
        ).select_related('student', 'capstone_project')


class TutorClassProjectRateView(APIView):
    permission_classes = [IsTutor]

    def patch(self, request, submission_id):
        submission = get_object_or_404(ClassProject, id=submission_id)
        tutor_profile = request.user.tutor_profile

        if not is_tutor_assigned_to_student(tutor_profile, submission.student):
            raise PermissionDenied("You can only rate submissions from your assigned students.")

        rating = request.data.get('tutor_rating', submission.tutor_rating)
        feedback = request.data.get('tutor_feedback', submission.tutor_feedback)
        submission.tutor_rating = rating
        submission.tutor_feedback = feedback
        submission.save(update_fields=['tutor_rating', 'tutor_feedback'])
        return Response(ClassProjectSerializer(submission).data)


class AdminClassProjectListView(generics.ListAPIView):
    serializer_class = ClassProjectSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ClassProject.objects.select_related('student', 'capstone_project').all()


class AdminClassProjectFeatureToggleView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, submission_id):
        submission = get_object_or_404(ClassProject, id=submission_id)
        submission.is_featured = not submission.is_featured
        submission.save(update_fields=['is_featured'])
        return Response(ClassProjectSerializer(submission).data)


class PublicFeaturedStudentProjectsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        student_projects = StudentProject.objects.filter(is_featured=True, status='submitted')
        class_projects = ClassProject.objects.filter(is_featured=True)
        student_data = PublicStudentProjectSerializer(student_projects, many=True).data
        class_data = PublicClassProjectSerializer(class_projects, many=True).data
        combined = sorted(
            chain(student_data, class_data),
            key=lambda x: x.get('created_at') or x.get('submitted_at'),
            reverse=True,
        )
        return Response(combined)

class AdminStudentProjectDeleteView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, project_id):
        project = get_object_or_404(StudentProject, id=project_id)
        project.delete()
        return Response(status=204)

class AdminClassProjectDeleteView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, submission_id):
        submission = get_object_or_404(ClassProject, id=submission_id)
        submission.delete()
        return Response(status=204)

from rest_framework import serializers
from .models import Cohort, ClassSession, Attendance, StudentProject, CapstoneProject, Assessment, ClassProject



class CohortSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)
    current_stage = serializers.CharField(read_only=True)
    current_stage_label = serializers.CharField(read_only=True)
    stage_countdown_days = serializers.IntegerField(read_only=True)
    is_learning_today = serializers.BooleanField(read_only=True)
    tutor_name = serializers.SerializerMethodField()

    class Meta:
        model = Cohort
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'status',
            'tutor',
            'tutor_name',
            'class_days',
            'student_count',
            'current_stage',
            'current_stage_label',
            'stage_countdown_days',
            'is_learning_today',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_tutor_name(self, obj):
        if obj.tutor and obj.tutor.user:
            full = f"{obj.tutor.user.first_name} {obj.tutor.user.last_name}".strip()
            return full or obj.tutor.user.email
        return None


class ClassSessionSerializer(serializers.ModelSerializer):
    duration_hours = serializers.ReadOnlyField()
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    attendance_marked = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = [
            'id', 'cohort', 'cohort_name', 'tutor', 'title', 'topics_covered',
            'lesson_outcome', 'date', 'start_time', 'end_time', 'duration_hours',
            'started_at', 'ended_at', 'attendance_marked', 'created_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}
        read_only_fields = ['started_at', 'ended_at']

    def get_attendance_marked(self, obj):
        return Attendance.objects.filter(session=obj).exists()


class AttendanceStudentSerializer(serializers.Serializer):
    application_id = serializers.IntegerField(source='id')
    student_id = serializers.IntegerField(source='student.id')
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email')

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'session', 'application', 'status', 'marked_at', 'student_name']

    def get_student_name(self, obj):
        s = obj.application.student
        full = f"{s.first_name} {s.last_name}".strip()
        return full or s.email

class CapstoneProjectSerializer(serializers.ModelSerializer):
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    tutor_name = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source='get_stage_display', read_only=True)

    class Meta:
        model = CapstoneProject
        fields = [
            'id', 'cohort', 'cohort_name', 'tutor', 'tutor_name',
            'stage', 'stage_label', 'title', 'description',
            'attachment', 'due_date', 'posted_at',
        ]
        extra_kwargs = {'tutor': {'required': False}}
        read_only_fields = ['posted_at']

    def get_tutor_name(self, obj):
        if obj.tutor and obj.tutor.user:
            full = f"{obj.tutor.user.first_name} {obj.tutor.user.last_name}".strip()
            return full or obj.tutor.user.email
        return None

class StudentProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    project_type_label = serializers.CharField(source='get_project_type_display', read_only=True)

    class Meta:
        model = StudentProject
        fields = [
            'id', 'student', 'student_name', 'cohort', 'cohort_name',
            'project_type', 'project_type_label',
            'title', 'description', 'tech_stack', 'repo_url', 'live_url',
            'cover_image', 'attachment', 'status', 'tutor_feedback',
            'is_featured', 'submitted_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'status', 'tutor_feedback', 'is_featured', 'submitted_at', 'created_at', 'updated_at']


class AssessmentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    cohort_name = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            'id', 'student', 'student_name', 'author', 'author_name',
            'content', 'created_at', 'updated_at',
            'student_response', 'responded_at', 'cohort_name',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'responded_at']

    def get_author_name(self, obj):
        full = f"{obj.author.first_name} {obj.author.last_name}".strip()
        return full or obj.author.email

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email

    def get_cohort_name(self, obj):
        app = obj.student.applications.filter(cohort__isnull=False).order_by('-created_at').first()
        return app.cohort.name if app else None

class PublicStudentProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    tech_stack_list = serializers.SerializerMethodField()

    class Meta:
        model = StudentProject
        fields = [
            'id', 'title', 'description', 'tech_stack_list',
            'repo_url', 'live_url', 'student_name', 'created_at',
        ]

    def get_student_name(self, obj):
        s = obj.student
        return f"{s.first_name} {s.last_name}".strip() or s.email

    def get_tech_stack_list(self, obj):
        return [t.strip() for t in (obj.tech_stack or '').split(',') if t.strip()]


class ClassProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    capstone_project_title = serializers.CharField(source='capstone_project.title', read_only=True)
    cohort_name = serializers.CharField(source='capstone_project.cohort.name', read_only=True)

    class Meta:
        model = ClassProject
        fields = [
            'id', 'capstone_project', 'capstone_project_title', 'cohort_name',
            'student', 'student_name', 'title', 'description', 'tech_stack',
            'repo_url', 'live_url', 'cover_image', 'attachment',
            'tutor_rating', 'tutor_feedback', 'is_featured',
            'submitted_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'tutor_rating', 'tutor_feedback', 'is_featured', 'submitted_at', 'updated_at']

    def get_student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.email


class PublicClassProjectSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    tech_stack_list = serializers.SerializerMethodField()

    class Meta:
        model = ClassProject
        fields = [
            'id', 'title', 'description', 'tech_stack_list',
            'repo_url', 'live_url', 'student_name', 'submitted_at',
        ]

    def get_student_name(self, obj):
        s = obj.student
        return f"{s.first_name} {s.last_name}".strip() or s.email

    def get_tech_stack_list(self, obj):
        return [t.strip() for t in (obj.tech_stack or '').split(',') if t.strip()]

class PublicAllStudentProjectsView(APIView):
    """Public: every submitted student project + class project submission,
    for the full 'See More Projects' page (not just the featured homepage set)."""
    permission_classes = [AllowAny]

    def get(self, request):
        student_projects = StudentProject.objects.filter(status='submitted')
        class_projects = ClassProject.objects.all()
        student_data = PublicStudentProjectSerializer(student_projects, many=True).data
        class_data = PublicClassProjectSerializer(class_projects, many=True).data
        combined = sorted(
            chain(student_data, class_data),
            key=lambda x: x.get('created_at') or x.get('submitted_at'),
            reverse=True,
        )
        return Response(combined)