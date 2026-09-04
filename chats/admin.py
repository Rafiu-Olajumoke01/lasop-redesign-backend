from django.contrib import admin

from .models import Conversation, ConversationParticipant, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_type', 'name', 'cohort', 'created_at']
    list_filter = ['conversation_type']


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'user', 'joined_at', 'last_read_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'created_at']
    search_fields = ['content']