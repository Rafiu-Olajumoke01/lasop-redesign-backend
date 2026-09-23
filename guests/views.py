from rest_framework import generics, permissions
from .models import Guest
from .serializers import GuestSerializer


class GuestListCreateView(generics.ListCreateAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]


class GuestDetailView(generics.DestroyAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]