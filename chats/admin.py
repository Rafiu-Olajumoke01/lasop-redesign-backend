from django.contrib import admin

from .models import Conversation, ConversationParticipant, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_type', 'name', 'cohort_id', 'created_at']
    list_filter = ['conversation_type']


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'user_id', 'username', 'joined_at', 'last_read_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender_id', 'sender_name', 'created_at']
    search_fields = ['content', 'sender_name']