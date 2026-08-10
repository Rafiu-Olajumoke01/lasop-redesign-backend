from django.urls import path
from .views import ApplicationListCreateView, ApplicationDetailView, GroupedApplicantsView, StudentApplicationsView

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list-create'),
    path('grouped/', GroupedApplicantsView.as_view(), name='applications-grouped'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('admin/students/<int:user_id>/applications/', StudentApplicationsView.as_view(), name='student-applications'),
]