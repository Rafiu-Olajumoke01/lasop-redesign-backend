from django.contrib import admin
from .models import Cohort


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'student_count']
    list_filter = ['status']
    search_fields = ['name']