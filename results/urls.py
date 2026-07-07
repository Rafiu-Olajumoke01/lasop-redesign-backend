from django.urls import path
from .views import ResultListCreateView, ResultDetailView

urlpatterns = [
    path('', ResultListCreateView.as_view(), name='result-list-create'),
    path('<int:pk>/', ResultDetailView.as_view(), name='result-detail'),
]