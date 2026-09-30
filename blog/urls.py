from django.urls import path
from .views import (
    BlogPostListView,
    BlogPostDetailView,
    BlogPostCreateView,
    BlogPostDeleteView,
)

urlpatterns = [
    path('', BlogPostListView.as_view(), name='blog-list'),
    path('create/', BlogPostCreateView.as_view(), name='blog-create'),
    path('<int:pk>/', BlogPostDetailView.as_view(), name='blog-detail'),
    path('<int:pk>/delete/', BlogPostDeleteView.as_view(), name='blog-delete'),
]