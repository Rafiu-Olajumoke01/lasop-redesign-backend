from django.db import models


class Location(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    CATEGORY_CHOICES = [
        ('technology', 'Technology'),
        ('business', 'Business'),
        ('vocational', 'Vocational'),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50)
    image = models.ImageField(upload_to='courses/', blank=True, null=True)
    description = models.TextField()
    overview = models.TextField()
    featured = models.BooleanField(default=False)
    skills = models.JSONField(default=list)
    outcomes = models.JSONField(default=list)
    requirements = models.JSONField(default=list)
    modules = models.JSONField(default=list)
    locations = models.ManyToManyField(Location, blank=True, related_name='courses')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title