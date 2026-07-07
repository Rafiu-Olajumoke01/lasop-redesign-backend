from django.db import models
from django.utils import timezone


class Cohort(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('current', 'Current'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=150, unique=True)  # e.g. "January 2026 Set"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        # Counts applications assigned to this cohort.
        # Assumes Application model has a nullable FK to Cohort (added separately).
        return self.applications.count()

    @property
    def current_stage(self):
        """
        stage_1 = Morning Class (0–59 days in)
        stage_2 = Afternoon Class (60–119 days in)
        stage_3 = Projects Class (120–179 days in)
        completed = 180+ days in
        """
        days_in = (timezone.now().date() - self.start_date).days
        if days_in < 0:
            return 'not_started'
        elif days_in < 60:
            return 'stage_1'
        elif days_in < 120:
            return 'stage_2'
        elif days_in < 180:
            return 'stage_3'
        return 'completed'

    @property
    def current_stage_label(self):
        labels = {
            'not_started': 'Not Started',
            'stage_1': 'Morning Class',
            'stage_2': 'Afternoon Class',
            'stage_3': 'Projects Class',
            'completed': 'Completed',
        }
        return labels.get(self.current_stage)

    @property
    def stage_countdown_days(self):
        """Days remaining until next promotion (or completion once in stage_3)."""
        days_in = (timezone.now().date() - self.start_date).days
        if days_in < 0:
            return None
        elif days_in < 60:
            return 60 - days_in
        elif days_in < 120:
            return 120 - days_in
        elif days_in < 180:
            return 180 - days_in
        return 0