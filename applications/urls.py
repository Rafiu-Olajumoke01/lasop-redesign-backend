from django.urls import path
from .views import ApplicationListCreateView, ApplicationDeleteView

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list-create'),
    path('<int:pk>/', ApplicationDeleteView.as_view(), name='application-delete'),
]