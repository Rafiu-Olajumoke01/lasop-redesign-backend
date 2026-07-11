# tutors/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Tutor
from .permissions import IsAdmin, IsTutor
from .serializers import (
    TutorSerializer,
    TutorCreateSerializer,
    TutorSelfUpdateSerializer,
    TutorDashboardStatsSerializer,
)


# ── Admin: list all tutors / create a tutor account ─────────────────────
class TutorListCreateView(generics.ListCreateAPIView):
    queryset = Tutor.objects.select_related('user').all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        # POST (creating a tutor) needs to create the User + Tutor together,
        # so it uses TutorCreateSerializer. GET (listing tutors) just reads
        # existing records, so it uses the regular TutorSerializer.
        if self.request.method == 'POST':
            return TutorCreateSerializer
        return TutorSerializer


# ── Admin: view / edit / delete one tutor ────────────────────────────────
class TutorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tutor.objects.select_related('user').all()
    serializer_class = TutorSerializer
    permission_classes = [IsAdmin]


# ── Tutor: view / edit their own profile ─────────────────────────────────
class TutorMeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsTutor]

    def get_object(self):
        return get_object_or_404(
            Tutor.objects.select_related('user'),
            user=self.request.user
        )

    def get_serializer_class(self):
        # Viewing own profile returns everything (read-only view).
        # Updating own profile is restricted to bio, profile_picture,
        # and courses_of_instruction only.
        if self.request.method in ('PUT', 'PATCH'):
            return TutorSelfUpdateSerializer
        return TutorSerializer


# ── Tutor: dashboard stats ────────────────────────────────────────────────
class TutorDashboardStatsView(APIView):
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_object_or_404(Tutor, user=request.user)
        data = {
            'courses': tutor.courses_count,
            'cohorts_total': tutor.cohorts_total,
            'cohorts_completed': tutor.cohorts_completed,
            'cohorts_ongoing': tutor.cohorts_ongoing,
            'total_hours': tutor.total_hours,
            'days_absent': tutor.days_absent,
            'queries_pending': tutor.queries_pending,
        }
        serializer = TutorDashboardStatsSerializer(data)
        return Response(serializer.data)


# ── Tutor: list cohorts assigned to them ──────────────────────────────────
class TutorMyCohortsView(generics.ListAPIView):
    permission_classes = [IsTutor]

    def get_queryset(self):
        tutor = get_object_or_404(Tutor, user=self.request.user)
        return tutor.cohorts.all()

    def get_serializer_class(self):
        # Reuses the existing CohortSerializer from the cohorts app —
        # avoids duplicating cohort fields here.
        from cohorts.serializers import CohortSerializer
        return CohortSerializer