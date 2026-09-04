from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, ConversationParticipant
from .serializers import ConversationCreateSerializer, ConversationSerializer, MessageSerializer


class ConversationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Conversation.objects
            .filter(participants__user=self.request.user)
            .order_by('-updated_at')
            .distinct()
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ConversationCreateSerializer
        return ConversationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        output = ConversationSerializer(conversation, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class MessageHistoryView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = None

    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id, participants__user=self.request.user)
        queryset = conversation.messages.select_related('sender').order_by('-created_at')

        before = self.request.query_params.get('before')
        if before:
            queryset = queryset.filter(created_at__lt=before)

        limit = int(self.request.query_params.get('limit', 30))
        return list(reversed(list(queryset[:limit])))


class MarkConversationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        participant = get_object_or_404(ConversationParticipant, conversation_id=conversation_id, user=request.user)
        participant.last_read_at = timezone.now()
        participant.save(update_fields=['last_read_at'])
        return Response({'status': 'ok'})