from django.db import models
from django.utils import timezone


class Cohort(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('current', 'Current'),
        ('completed', 'Completed'),
    ]

    DAY_CHOICES = [
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ]

    name = models.CharField(max_length=150, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    tutor = models.ForeignKey('tutors.Tutor', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cohorts')
    class_days = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        return self.applications.count()

    @property
    def is_learning_today(self):
        today_code = timezone.now().strftime('%a').lower()
        return today_code in self.class_days

    @property
    def current_stage(self):
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


class ClassSession(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='class_sessions')
    tutor = models.ForeignKey('tutors.Tutor', on_delete=models.SET_NULL, null=True, related_name='class_sessions')
    topics_covered = models.TextField(blank=True)
    project_note = models.TextField(blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.cohort.name} — {self.date}"

    @property
    def duration_hours(self):
        from datetime import datetime
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return round((end - start).seconds / 3600, 2)

    @property
    def roster(self):
        return self.cohort.applications.select_related('student').all()


class Attendance(models.Model):
    STATUS_CHOICES = [('present', 'Present'), ('absent', 'Absent'), ('late', 'Late')]

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='attendance_records')
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'application')

    def __str__(self):
        return f"{self.application.student} — {self.session.date} — {self.status}"