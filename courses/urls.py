from django.urls import path
from .views import CourseListCreateView, CourseDetailView, LocationListCreateView, LocationDetailView

urlpatterns = [
    path('', CourseListCreateView.as_view(), name='course-list-create'),
    path('locations/', LocationListCreateView.as_view(), name='location-list-create'),
    path('locations/<int:pk>/', LocationDetailView.as_view(), name='location-detail'),
    path('<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),
]