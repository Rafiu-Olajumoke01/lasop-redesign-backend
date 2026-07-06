from django.urls import path
from .views import CohortListCreateView, CohortDetailView, CohortStatsView


urlpatterns = [
    path('', CohortListCreateView.as_view(), name='cohort-list-create'),
    path('<int:pk>/', CohortDetailView.as_view(), name='cohort-detail'),
    path('stats/', CohortStatsView.as_view(), name='cohort-stats'),
]