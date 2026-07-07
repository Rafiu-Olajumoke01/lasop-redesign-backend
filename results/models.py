from django.db import models
from django.conf import settings
from exams.models import Exam


class Result(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='results')

    score = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    submitted_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.student} — {self.exam.title} ({self.status})"

    @property
    def is_late(self):
        if not self.submitted_at:
            return False
        return self.submitted_at.date() > self.exam.due_date

    def save(self, *args, **kwargs):
        if self.score is not None:
            self.status = 'passed' if self.score >= self.exam.pass_mark else 'failed'
        super().save(*args, **kwargs)