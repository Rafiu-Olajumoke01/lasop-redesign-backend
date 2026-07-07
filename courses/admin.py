from django.contrib import admin
from .models import Course, Location

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    search_fields = ['title']

admin.site.register(Location)