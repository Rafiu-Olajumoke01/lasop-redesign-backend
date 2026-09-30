from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import BlogPost, BlogSection, PostImage, SectionImage
from .serializers import BlogPostListSerializer, BlogPostDetailSerializer


class BlogPostListView(generics.ListAPIView):
    """Public: list published posts. Admin: pass ?all=1 to see drafts too."""
    serializer_class = BlogPostListSerializer

    def get_queryset(self):
        qs = BlogPost.objects.all()
        if self.request.query_params.get('all') and self.request.user.is_staff:
            return qs
        return qs.filter(status=BlogPost.PUBLISHED)


class BlogPostDetailView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostDetailSerializer
    permission_classes = [permissions.AllowAny]


class BlogPostCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        data = request.data

        post = BlogPost.objects.create(
            main_heading=data.get('main_heading', ''),
            intro_text=data.get('intro_text', ''),
            date_published=data.get('date_published'),
            status=data.get('status', BlogPost.DRAFT),
        )

        intro_images = request.FILES.getlist('intro_images')
        for i, img in enumerate(intro_images):
            PostImage.objects.create(post=post, image=img, order=i)

        section_count = int(data.get('section_count', 0))
        for i in range(section_count):
            subheading = data.get(f'sections[{i}][subheading]', '')
            text = data.get(f'sections[{i}][text]', '')
            section = BlogSection.objects.create(post=post, subheading=subheading, text=text, order=i)

            section_images = request.FILES.getlist(f'sections[{i}][images]')
            for j, img in enumerate(section_images):
                SectionImage.objects.create(section=section, image=img, order=j)

        serializer = BlogPostDetailSerializer(post, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlogPostDeleteView(generics.DestroyAPIView):
    queryset = BlogPost.objects.all()
    permission_classes = [permissions.IsAdminUser]