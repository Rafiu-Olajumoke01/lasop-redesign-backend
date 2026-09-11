from django.urls import path
from django.http import JsonResponse
from django.conf import settings
import hashlib

from .views import (
    ConversationListCreateView,
    MarkConversationReadView,
    MessageHistoryView,
    UploadAttachmentView,
)


def debug_secret_hash(request):
    return JsonResponse({'hash': hashlib.md5(settings.SECRET_KEY.encode()).hexdigest()})


urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='chat-conversations'),
    path('conversations/<int:conversation_id>/messages/', MessageHistoryView.as_view(), name='chat-messages'),
    path('conversations/<int:conversation_id>/read/', MarkConversationReadView.as_view(), name='chat-mark-read'),
    path('upload/', UploadAttachmentView.as_view(), name='chat-upload-attachment'),
    path('debug-secret-hash/', debug_secret_hash),
]