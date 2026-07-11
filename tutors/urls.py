# tutors/urls.py
from django.urls import path
from .views import (
    TutorListCreateView,
    TutorDetailView,
    TutorMeView,
    TutorDashboardStatsView,
    TutorMyCohortsView,
)

urlpatterns = [
    # Admin: list all tutors (GET) / create a tutor account (POST)
    path('', TutorListCreateView.as_view(), name='tutor-list-create'),

    # Admin: view / edit / delete a specific tutor by ID
    path('<int:pk>/', TutorDetailView.as_view(), name='tutor-detail'),

    # Tutor: view / edit own profile
    path('me/', TutorMeView.as_view(), name='tutor-me'),

    # Tutor: own dashboard stats
    path('me/stats/', TutorDashboardStatsView.as_view(), name='tutor-dashboard-stats'),

    # Tutor: cohorts assigned to them
    path('me/cohorts/', TutorMyCohortsView.as_view(), name='tutor-my-cohorts'),
]