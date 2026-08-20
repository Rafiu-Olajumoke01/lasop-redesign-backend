from django.urls import path
from .views import (
    CohortListCreateView, CohortDetailView, CohortStatsView, DashboardStatsView,
    TutorClassSessionListCreateView, SessionRosterView, BulkAttendanceView,
    StudentClassSessionsView, AdminCohortsTodayView, AdminCohortAttendanceView,
    AdminCohortDetailView, AdminCohortSessionsView, StopClassSessionView, ApplicationAnalyticsView,
    TutorCapstoneProjectListCreateView, StudentCapstoneProjectsView,
    TutorAssessmentListCreateView, AdminAssessmentListCreateView, StudentAssessmentsView,
    AssessmentRespondView, AdminOrTutorStudentAssessmentsView, TutorStudentsListView
)

urlpatterns = [
    path('stats/', CohortStatsView.as_view(), name='cohort-stats'),
    path('today/', AdminCohortsTodayView.as_view(), name='admin-cohorts-today'),
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('my-classes/', StudentClassSessionsView.as_view(), name='student-classes'),
    path('sessions/', TutorClassSessionListCreateView.as_view(), name='tutor-sessions'),
    path('sessions/<int:session_id>/roster/', SessionRosterView.as_view(), name='session-roster'),
    path('sessions/<int:session_id>/attendance/', BulkAttendanceView.as_view(), name='session-attendance'),
    path('<int:cohort_id>/admin-attendance/', AdminCohortAttendanceView.as_view(), name='admin-cohort-attendance'),
    path('<int:cohort_id>/admin-detail/', AdminCohortDetailView.as_view(), name='admin-cohort-detail'),
    path('<int:pk>/', CohortDetailView.as_view(), name='cohort-detail'),
    path('', CohortListCreateView.as_view(), name='cohort-list-create'),
    path('<int:cohort_id>/sessions/', AdminCohortSessionsView.as_view(), name='admin-cohort-sessions'),
    path('sessions/<int:session_id>/stop/', StopClassSessionView.as_view(), name='session-stop'),
    path('applications/<int:application_id>/analytics/', ApplicationAnalyticsView.as_view(), name='application-analytics'),
    path('capstone-projects/', TutorCapstoneProjectListCreateView.as_view(), name='tutor-capstone-projects'),
    path('my-capstone-projects/', StudentCapstoneProjectsView.as_view(), name='student-capstone-projects'),

    path('assessments/tutor/', TutorAssessmentListCreateView.as_view(), name='tutor-assessments'),
    path('assessments/admin/', AdminAssessmentListCreateView.as_view(), name='admin-assessments'),
    path('assessments/mine/', StudentAssessmentsView.as_view(), name='student-assessments'),
    path('assessments/<int:assessment_id>/respond/', AssessmentRespondView.as_view(), name='assessment-respond'),
    path('assessments/student/<int:student_id>/', AdminOrTutorStudentAssessmentsView.as_view(), name='student-assessments-detail'),
    path('tutor/students/', TutorStudentsListView.as_view(), name='tutor-students-list'),
]