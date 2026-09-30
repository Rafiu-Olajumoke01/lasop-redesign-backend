from django.db import models


class Guest(models.Model):
    guest_id = models.CharField(max_length=20, unique=True, null=True, blank=True, editable=False)
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    purpose = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.purpose}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.guest_id:
            self.guest_id = f"GST-{self.pk:05d}"
            super().save(update_fields=['guest_id'])


class GuestMessage(models.Model):
    ADMIN = 'admin'
    GUEST = 'guest'
    SENDER_CHOICES = [(ADMIN, 'Admin'), (GUEST, 'Guest')]

    guest = models.ForeignKey(Guest, related_name='messages', on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.guest.guest_id} - {self.sender} - {self.created_at:%Y-%m-%d %H:%M}"