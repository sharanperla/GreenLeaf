# community_chat/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        room = self.get_object()
        messages = room.messages.all().order_by('-created_at')[:100]  # Get last 100 messages
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        """Upload an image for a chat message"""
        from .utils import handle_chat_image_upload
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        import json
        
        room_id = request.data.get('room')
        if not room_id:
            return Response({'error': 'Room ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Check if image is in request
        if 'image' not in request.FILES:
            return Response({'error': 'No image found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process and save the image
        image_path = handle_chat_image_upload(request.FILES['image'])
        
        # Create message with image
        message = ChatMessage.objects.create(
            room=room,
            user=request.user,
            content=request.data.get('content', ''),
            image=image_path
        )
        
        # Send via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room.name}',
            {
                'type': 'chat_message',
                'message': message.content,
                'username': request.user.username,
                'image_url': request.build_absolute_uri(message.image.url) if message.image else None,
                'created_at': message.created_at.isoformat()
            }
        )
        
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)