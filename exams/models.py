from django.db import models
from cohorts.models import Cohort
from courses.models import Course


class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm'),
        ('final', 'Final Assessment'),
        ('project', 'Project Assessment'),
    ]

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='exams')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200)  # e.g. "Final Project — Build a Portfolio Site"
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='project')

    start_date = models.DateField()   # when the project/exam is given out
    due_date = models.DateField()     # submission deadline (typically 2 months later)

    total_marks = models.PositiveIntegerField(default=100)   # what it's scored out of
    pass_mark = models.PositiveIntegerField(default=50)       # threshold to pass

    instructions = models.TextField(blank=True)  # project brief / requirements shown to students
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        unique_together = ('cohort', 'course', 'title')

    def __str__(self):
        return f"{self.title} — {self.course.title} ({self.cohort.name})"

    @property
    def is_open(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.start_date <= today <= self.due_date