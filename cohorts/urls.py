from django.urls import path
from .views import (
    CohortListCreateView, CohortDetailView, CohortStatsView, DashboardStatsView,
    TutorClassSessionListCreateView, SessionRosterView, BulkAttendanceView,
)

urlpatterns = [
    path('', CohortListCreateView.as_view(), name='cohort-list-create'),
    path('<int:pk>/', CohortDetailView.as_view(), name='cohort-detail'),
    path('stats/', CohortStatsView.as_view(), name='cohort-stats'),
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('sessions/', TutorClassSessionListCreateView.as_view(), name='tutor-sessions'),
    path('sessions/<int:session_id>/roster/', SessionRosterView.as_view(), name='session-roster'),
    path('sessions/<int:session_id>/attendance/', BulkAttendanceView.as_view(), name='session-attendance'),
]