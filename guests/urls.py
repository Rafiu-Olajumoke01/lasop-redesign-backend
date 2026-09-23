from django.urls import path
from .views import GuestListCreateView, GuestDetailView

urlpatterns = [
    path('', GuestListCreateView.as_view()),
    path('<int:pk>/', GuestDetailView.as_view()),
]