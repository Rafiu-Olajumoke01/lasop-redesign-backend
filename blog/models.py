from django.db import models


class BlogPost(models.Model):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    STATUS_CHOICES = [(DRAFT, 'Draft'), (PUBLISHED, 'Published')]

    main_heading = models.CharField(max_length=255)
    intro_text = models.TextField(blank=True)
    date_published = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_published', '-created_at']

    def __str__(self):
        return self.main_heading


class PostImage(models.Model):
    post = models.ForeignKey(BlogPost, related_name='intro_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog/intro/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Intro image for {self.post.main_heading}"


class BlogSection(models.Model):
    post = models.ForeignKey(BlogPost, related_name='sections', on_delete=models.CASCADE)
    subheading = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.subheading or f"Section {self.order} of {self.post.main_heading}"


class SectionImage(models.Model):
    section = models.ForeignKey(BlogSection, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog/sections/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Image for {self.section}"