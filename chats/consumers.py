import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        self.room_group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        attachment_url = data.get('attachment_url')
        attachment_name = data.get('attachment_name', '')

        # a message needs either text or an attachment — not neither
        if not content and not attachment_url:
            return

        message = await self.save_message(content, message_type, attachment_url, attachment_name)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender_id': self.user.id,
                'sender_name': self.user.get_full_name() or self.user.get_username(),
                'content': message.content,
                'message_type': message.message_type,
                'attachment_url': message.attachment_url,
                'attachment_name': message.attachment_name,
                'created_at': message.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['message_id'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'message_type': event['message_type'],
            'attachment_url': event['attachment_url'],
            'attachment_name': event['attachment_name'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def check_participant(self):
        from .models import ConversationParticipant
        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id, user_id=self.user.id
        ).exists()

    @database_sync_to_async
    def save_message(self, content, message_type='text', attachment_url=None, attachment_name=''):
        from .models import Conversation, Message
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender_id=self.user.id,
            sender_name=self.user.get_full_name() or self.user.get_username(),
            content=content,
            message_type=message_type,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
        )
        Conversation.objects.filter(id=self.conversation_id).update(updated_at=timezone.now())
        return message