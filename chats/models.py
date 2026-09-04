from django.conf import settings
from django.db import models


class Conversation(models.Model):
    DIRECT = 'direct'
    GROUP = 'group'
    TYPE_CHOICES = [
        (DIRECT, 'Direct'),
        (GROUP, 'Group'),
    ]

    conversation_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DIRECT)
    name = models.CharField(max_length=255, blank=True)
    cohort = models.ForeignKey(
        'cohorts.Cohort',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.conversation_type == self.GROUP:
            return self.name or f'Group {self.id}'
        usernames = ', '.join(p.user.get_username() for p in self.participants.all())
        return f'Direct: {usernames}'


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('conversation', 'user')

    def __str__(self):
        return f'{self.user} in {self.conversation_id}'


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} @ {self.created_at}: {self.content[:30]}'