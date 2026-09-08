from django.contrib.auth import get_user_model
from rest_framework import serializers
from tutors.models import Tutor

from .models import Conversation, ConversationParticipant, Message

User = get_user_model()

ROLE_ADMIN = 'admin'
ROLE_TUTOR = 'tutor'
ROLE_STUDENT = 'student'


def get_user_role(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
    if user.is_staff:
        return ROLE_ADMIN
    if Tutor.objects.filter(user_id=user_id).exists():
        return ROLE_TUTOR
    return ROLE_STUDENT


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender_id', 'sender_name', 'content', 'created_at', 'edited_at']
        read_only_fields = ['id', 'sender_id', 'sender_name', 'created_at', 'edited_at']


class ConversationParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user_id', 'username', 'full_name', 'joined_at', 'last_read_at']


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'cohort_id', 'created_at',
            'updated_at', 'participants', 'last_message', 'unread_count',
        ]

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if not last:
            return None
        return MessageSerializer(last).data

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        participant = obj.participants.filter(user_id=request.user.id).first()
        if not participant:
            return 0
        qs = obj.messages.exclude(sender_id=request.user.id)
        if participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()


class ParticipantInputSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField(required=False, allow_blank=True)


class ConversationCreateSerializer(serializers.Serializer):
    conversation_type = serializers.ChoiceField(choices=Conversation.TYPE_CHOICES, default=Conversation.DIRECT)
    name = serializers.CharField(required=False, allow_blank=True)
    cohort_id = serializers.IntegerField(required=False)
    participants = ParticipantInputSerializer(many=True)

    def validate(self, data):
        request = self.context['request']
        conversation_type = data.get('conversation_type', Conversation.DIRECT)

        if conversation_type != Conversation.DIRECT:
            return data

        participant_ids = {p['id'] for p in data['participants']}
        participant_ids.add(request.user.id)

        if len(participant_ids) != 2:
            return data

        roles = {uid: get_user_role(uid) for uid in participant_ids}
        if set(roles.values()) == {ROLE_STUDENT}:
            raise serializers.ValidationError('Students cannot message other students.')

        return data

    def create(self, validated_data):
        request = self.context['request']
        participants_data = {p['id']: p for p in validated_data['participants']}

        participants_data[request.user.id] = {
            'id': request.user.id,
            'username': request.user.username,
            'full_name': getattr(request.user, 'full_name', request.user.username),
        }

        conversation_type = validated_data.get('conversation_type', Conversation.DIRECT)
        participant_ids = set(participants_data.keys())

        if conversation_type == Conversation.DIRECT and len(participant_ids) == 2:
            existing = (
                Conversation.objects
                .filter(conversation_type=Conversation.DIRECT, participants__user_id__in=participant_ids)
                .distinct()
            )
            for conv in existing:
                conv_user_ids = set(conv.participants.values_list('user_id', flat=True))
                if conv_user_ids == participant_ids:
                    return conv

        conversation = Conversation.objects.create(
            conversation_type=conversation_type,
            name=validated_data.get('name', ''),
            cohort_id=validated_data.get('cohort_id'),
        )
        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(
                conversation=conversation,
                user_id=p['id'],
                username=p['username'],
                full_name=p.get('full_name', ''),
            )
            for p in participants_data.values()
        ])
        return conversation