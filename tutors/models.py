# tutors/models.py
from django.db import models
from django.conf import settings
from cohorts.models import Cohort


class Tutor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tutor_profile',
    )
    bio = models.TextField(blank=True)
    courses_of_instruction = models.JSONField(default=list, blank=True)  # e.g. ["Full-Stack Web Development"]
    date_of_employment = models.DateField(null=True, blank=True)
    performance_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    profile_picture = models.ImageField(upload_to='tutor_pictures/', null=True, blank=True)
    cohorts = models.ManyToManyField(Cohort, related_name='tutors', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.email

    # ── Computed dashboard stats ────────────────────────────────────────

    @property
    def cohorts_total(self):
        return self.cohorts.count()

    @property
    def cohorts_completed(self):
        # Uses current_stage (auto-calculated from dates) instead of the
        # manual `status` field, since nothing in the codebase ever updates
        # `status` after a cohort is created.
        return sum(1 for c in self.cohorts.all() if c.current_stage == 'completed')

    @property
    def cohorts_ongoing(self):
        # Same reasoning as above — any cohort currently in stage_1, stage_2,
        # or stage_3 counts as "ongoing".
        return sum(
            1 for c in self.cohorts.all()
            if c.current_stage in ['stage_1', 'stage_2', 'stage_3']
        )

    @property
    def courses_count(self):
        return len(self.courses_of_instruction)

    @property
    def total_hours(self):
        # Sums ClassSession durations once that model exists.
        # Placeholder for now — wire this up when ClassSession is built.
        return sum(
            session.duration_hours for session in self.class_sessions.all()
        ) if hasattr(self, 'class_sessions') else 0

    @property
    def days_absent(self):
        return self.attendance_records.filter(status='absent').count() if hasattr(self, 'attendance_records') else 0

    @property
    def queries_pending(self):
        return self.queries.filter(status='pending').count() if hasattr(self, 'queries') else 0