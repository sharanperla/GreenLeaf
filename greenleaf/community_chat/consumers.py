# community_chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'message':
            message = text_data_json['message']
            username = text_data_json['username']
            image_url = text_data_json.get('image_url', None)
            
            # Store message in database
            await self.save_message(username, message, image_url)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username,
                    'image_url': image_url
                }
            )
    
    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        image_url = event.get['image_url']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'username': username,
            'image_url': image_url,
            'created_at': event.get('created_at', None) or self._get_timestamp()
        }))
    
    @staticmethod
    def _get_timestamp():
        from datetime import datetime
        return datetime.now().isoformat()
    
    @database_sync_to_async
    def save_message(self, username, message, image_url=None):
        user = User.objects.get(username=username)
        room = ChatRoom.objects.get(name=self.room_name)
        
        chat_message = ChatMessage.objects.create(
            room=room,
            user=user,
            content=message
        )
        
        if image_url:
            # Note: This is a simplified version. In production, you'd handle the image differently
            # This is just saving the URL, not the actual image
            chat_message.image = image_url
            chat_message.save()
        
        return chat_message