from django.urls import path
from .views import CertificateUploadView

urlpatterns = [
    path('upload/<int:user_id>/', CertificateUploadView.as_view(), name='certificate-upload'),
]