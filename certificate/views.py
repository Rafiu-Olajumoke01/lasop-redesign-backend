from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, parsers
from rest_framework.permissions import IsAdminUser
from users.models import User
from .models import Certificate
from .serializers import CertificateSerializer


class CertificateUploadView(APIView):
    """Admin-only: upload or replace a certificate file for a given student."""
    permission_classes = [IsAdminUser]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request, user_id):
        try:
            student = User.objects.get(id=user_id, is_tutor=False, is_staff=False)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        file = request.data.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        certificate, created = Certificate.objects.get_or_create(student=student)
        certificate.file = file

        issued_date = request.data.get('issued_date')
        if issued_date:
            certificate.issued_date = issued_date

        certificate.save()

        serializer = CertificateSerializer(certificate, context={'request': request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )