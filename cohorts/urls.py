from django.urls import path
from .views import (
    CohortListCreateView, CohortDetailView, CohortStatsView, DashboardStatsView,
    TutorClassSessionListCreateView, SessionRosterView, BulkAttendanceView,
    StudentClassSessionsView, AdminCohortsTodayView, AdminCohortAttendanceView,
    AdminCohortDetailView,
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
]