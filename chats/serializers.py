from rest_framework import serializers

from .models import Conversation, ConversationParticipant, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'content', 'created_at', 'edited_at']
        read_only_fields = ['id', 'sender', 'sender_name', 'created_at', 'edited_at']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.get_username()


class ConversationParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = ConversationParticipant
        fields = ['id', 'user', 'username', 'full_name', 'joined_at', 'last_read_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'cohort', 'created_at',
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
        participant = obj.participants.filter(user=request.user).first()
        if not participant:
            return 0
        qs = obj.messages.exclude(sender=request.user)
        if participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()


class ConversationCreateSerializer(serializers.Serializer):
    conversation_type = serializers.ChoiceField(choices=Conversation.TYPE_CHOICES, default=Conversation.DIRECT)
    name = serializers.CharField(required=False, allow_blank=True)
    cohort_id = serializers.IntegerField(required=False)
    participant_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def create(self, validated_data):
        request = self.context['request']
        participant_ids = set(validated_data['participant_ids'])
        participant_ids.add(request.user.id)

        conversation_type = validated_data.get('conversation_type', Conversation.DIRECT)

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
            ConversationParticipant(conversation=conversation, user_id=uid) for uid in participant_ids
        ])
        return conversation