from django.db import models
from django.conf import settings
from courses.models import Course, Location
from cohorts.models import Cohort


class Application(models.Model):
    MODE_CHOICES = [
        ('online', 'Online'),
        ('physical', 'Physical'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='applications')
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, blank=True, null=True, related_name='applications')
    mode_of_learning = models.CharField(max_length=20, choices=MODE_CHOICES)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, blank=True, null=True, related_name='applications')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.course}"