from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer
from .utils import handle_chat_image_upload  # make sure this exists!
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        messages = room.messages.all().order_by('-created_at')[:100]
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        methods=['post'],
        url_path='upload_image',
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request):
        """Upload an image for a chat message"""
        room_id = request.data.get('room')
        image_file = request.FILES.get('image')

        if not room_id:
            return Response({'error': "'room' field is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file:
            return Response({'error': "'image' file is required"}, status=status.HTTP_400_BAD_REQUEST)

        # verify room exists
        room = get_object_or_404(ChatRoom, pk=room_id)

        # delegate saving & message creation to utils
        try:
            message = handle_chat_image_upload(
                room_id=int(room_id),
                user=request.user,
                image_file=image_file
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # broadcast over WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room.name}',
            {
                'type': 'chat_message',
                'message': message.content or '',
                'username': request.user.username,
                'image_url': request.build_absolute_uri(message.image.url) if message.image else None,
                'created_at': message.created_at.isoformat(),
            }
        )

        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
