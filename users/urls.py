from django.urls import path
from .views import RegisterView, LoginView, ProfileView, StudentListView, StudentDetailView, AssignTutorView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('students/', StudentListView.as_view(), name='student-list'),
    path('students/<int:user_id>/', StudentDetailView.as_view(), name='student-detail'),
    path('students/<int:user_id>/assign-tutor/', AssignTutorView.as_view(), name='assign-tutor'),
]