from django.db import models


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