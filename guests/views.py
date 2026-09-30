import logging

from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework import generics, permissions
from .models import Guest, GuestMessage
from .serializers import GuestSerializer


logger = logging.getLogger(__name__)


class GuestListCreateView(generics.ListCreateAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        guest = serializer.save()
        body = (
            f"Dear {guest.name},\n\n"
            f"Thank you for visiting us. Your Guest ID is {guest.guest_id}.\n"
            f"Purpose of visit: {guest.purpose}\n\n"
            "Please keep this ID for any future correspondence with us. "
            "You can reply directly to this email.\n\n"
            "Kind regards,\nLASOP"
        )
        GuestMessage.objects.create(guest=guest, sender=GuestMessage.ADMIN, body=body)

        if not guest.email:
            return
        try:
            reply_local = guest.guest_id.replace('-', '').lower()
            email = EmailMessage(
                subject="Welcome to LASOP",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[guest.email],
                reply_to=[f"reply+{reply_local}@lasop.net"],
            )
            email.send(fail_silently=False)
        except Exception as exc:
            logger.error("Guest email failed for %s: %s", guest.guest_id, exc)


class GuestDetailView(generics.DestroyAPIView):
    queryset = Guest.objects.all()
    serializer_class = GuestSerializer
    permission_classes = [permissions.IsAdminUser]