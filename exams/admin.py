from django.contrib import admin
from .models import Exam


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'cohort', 'exam_type', 'start_date', 'due_date', 'is_open']
    list_filter = ['exam_type', 'cohort', 'course']
    search_fields = ['title', 'course__title', 'cohort__name']
    autocomplete_fields = ['course', 'cohort']