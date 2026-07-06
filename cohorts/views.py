from rest_framework import generics, permissions
from .models import Cohort
from .serializers import CohortSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


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