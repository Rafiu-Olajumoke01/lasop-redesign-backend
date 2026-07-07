from django.contrib import admin
from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'score', 'status', 'is_late', 'submitted_at']
    list_filter = ['status', 'exam__cohort', 'exam__course']
    search_fields = ['student__email', 'student__first_name', 'student__last_name', 'exam__title']
    autocomplete_fields = ['exam', 'student']
    readonly_fields = ['status', 'created_at', 'updated_at']