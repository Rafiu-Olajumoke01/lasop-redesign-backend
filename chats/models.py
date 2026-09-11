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
    cohort_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.conversation_type == self.GROUP:
            return self.name or f'Group {self.id}'
        usernames = ', '.join(p.username for p in self.participants.all())
        return f'Direct: {usernames}'


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user_id = models.IntegerField()
    username = models.CharField(max_length=150)
    full_name = models.CharField(max_length=255, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('conversation', 'user_id')

    def __str__(self):
        return f'{self.username} in {self.conversation_id}'


class Message(models.Model):
    TEXT = 'text'
    IMAGE = 'image'
    DOCUMENT = 'document'
    MESSAGE_TYPE_CHOICES = [
        (TEXT, 'Text'),
        (IMAGE, 'Image'),
        (DOCUMENT, 'Document'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_id = models.IntegerField()
    sender_name = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default=TEXT)
    attachment_url = models.URLField(null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender_name} @ {self.created_at}: {self.content[:30]}'