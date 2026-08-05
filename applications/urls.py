from django.urls import path
from .views import ApplicationListCreateView, ApplicationDetailView, GroupedApplicantsView

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list-create'),
    path('grouped/', GroupedApplicantsView.as_view(), name='applications-grouped'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
]