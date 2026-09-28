import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics, permissions
from .models import Guest
from .serializers import GuestSerializer


logger = logging.getLogger(__name__)


class GuestListCreateView(generics.ListCreateAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        guest = serializer.save()
        if not guest.email:
            return
        try:
            send_mail(
                subject="Welcome to LASOP",
                message=(
                    f"Dear {guest.name},\n\n"
                    f"Thank you for visiting us. Your Guest ID is {guest.guest_id}.\n"
                    f"Purpose of visit: {guest.purpose}\n\n"
                    "Please keep this ID for any future correspondence with us.\n\n"
                    "Kind regards,\nLASOP"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[guest.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.error("Guest email failed for %s: %s", guest.guest_id, exc)

class GuestDetailView(generics.DestroyAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]