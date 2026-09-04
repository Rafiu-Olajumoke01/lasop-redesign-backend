from django.urls import path

from .views import ConversationListCreateView, MarkConversationReadView, MessageHistoryView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='chat-conversations'),
    path('conversations/<int:conversation_id>/messages/', MessageHistoryView.as_view(), name='chat-messages'),
    path('conversations/<int:conversation_id>/read/', MarkConversationReadView.as_view(), name='chat-mark-read'),
]