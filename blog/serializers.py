from rest_framework import serializers
from .models import BlogPost, BlogSection, PostImage, SectionImage


class SectionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionImage
        fields = ['id', 'image', 'order']


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'order']


class BlogSectionSerializer(serializers.ModelSerializer):
    images = SectionImageSerializer(many=True, read_only=True)

    class Meta:
        model = BlogSection
        fields = ['id', 'subheading', 'text', 'order', 'images']


class BlogPostListSerializer(serializers.ModelSerializer):
    """Lightweight version for the post list — no nested sections."""
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = ['id', 'main_heading', 'date_published', 'status', 'cover_image', 'created_at']

    def get_cover_image(self, obj):
        first = obj.intro_images.first()
        if not first:
            return None
        request = self.context.get('request')
        url = first.image.url
        return request.build_absolute_uri(url) if request else url


class BlogPostDetailSerializer(serializers.ModelSerializer):
    """Full version for viewing/editing one post."""
    intro_images = PostImageSerializer(many=True, read_only=True)
    sections = BlogSectionSerializer(many=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'main_heading', 'intro_text', 'date_published', 'status',
            'intro_images', 'sections', 'created_at', 'updated_at',
        ]