from django.db import models
from django.conf import settings


class Certificate(models.Model):
    """One certificate per student. Re-uploading replaces the existing file."""
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificate'
    )
    file = models.FileField(upload_to='certificates/')
    issued_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Certificate for {self.student}"