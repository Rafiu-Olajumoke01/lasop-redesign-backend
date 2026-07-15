from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Application
from .serializers import ApplicationSerializer


class ApplicationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            applications = Application.objects.all().select_related('student', 'course')
        else:
            applications = Application.objects.filter(student=request.user)
        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(APIView):
    """Handles GET (single application), PATCH (staff-only, e.g. assigning cohort),
    and DELETE (staff or owning student) for a single application."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.is_staff:
                application = Application.objects.get(pk=pk)
            else:
                application = Application.objects.get(pk=pk, student=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        try:
            application = Application.objects.get(pk=pk)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            if request.user.is_staff:
                application = Application.objects.get(pk=pk)
            else:
                application = Application.objects.get(pk=pk, student=request.user)
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
        application.delete()
        return Response({'message': 'Course removed successfully'}, status=status.HTTP_204_NO_CONTENT)