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
        await self.set_online_status(True)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, 'user') and self.user and self.user.is_authenticated:
            await self.set_online_status(False)

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
        await self.notify_offline_participants(message)

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
    def set_online_status(self, is_online):
        from .models import ConversationParticipant
        ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id, user_id=self.user.id
        ).update(is_online=is_online)

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

    @database_sync_to_async
    def notify_offline_participants(self, message):
        import logging
        from django.conf import settings
        from .models import ConversationParticipant

        logger = logging.getLogger(__name__)

        offline_participants = ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            is_online=False,
        ).exclude(user_id=self.user.id)

        from django.core.mail import EmailMultiAlternatives

        for participant in offline_participants:
            if not participant.email:
                continue
            try:
                subject = f'{message.sender_name} sent you a message on LASOP'
                text_body = (
                    f'{message.sender_name} sent you a message:\n\n'
                    f'{message.content}\n\n'
                    f'Log in to LASOP to reply: {settings.FRONTEND_URL}'
                )
                html_body = f'''
                <div style="background:#f0f2f5; padding:32px 16px; font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;">
                  <div style="max-width:480px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <div style="background:#2563eb; padding:24px 28px;">
                      <span style="color:#ffffff; font-size:18px; font-weight:700; letter-spacing:0.3px;">LASOP</span>
                    </div>
                    <div style="padding:28px;">
                      <p style="margin:0 0 4px; color:#6b7280; font-size:13px; text-transform:uppercase; letter-spacing:0.5px;">New message</p>
                      <h2 style="margin:0 0 16px; color:#111827; font-size:20px;">{message.sender_name}</h2>
                      <div style="background:#f9fafb; border-left:3px solid #2563eb; padding:14px 16px; border-radius:8px; color:#374151; font-size:15px; line-height:1.5;">
                        {message.content}
                      </div>
                      <a href="{settings.FRONTEND_URL}" style="display:inline-block; margin-top:24px; background:#2563eb; color:#ffffff; padding:12px 24px; border-radius:8px; text-decoration:none; font-size:14px; font-weight:600;">
                        Log in to reply
                      </a>
                    </div>
                    <div style="padding:16px 28px; background:#f9fafb; border-top:1px solid #f0f0f0;">
                      <p style="margin:0; color:#9ca3af; font-size:12px;">You're receiving this because you're offline on LASOP. Log in to keep the conversation going.</p>
                    </div>
                  </div>
                </div>
                '''
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[participant.email],
                )
                email.attach_alternative(html_body, "text/html")
                email.send(fail_silently=False)
            except Exception:
                logger.exception(f'Failed to send chat notification email to {participant.email}')