# community_chat/management/commands/create_default_chatroom.py
from django.core.management.base import BaseCommand
from community_chat.models import ChatRoom

class Command(BaseCommand):
    help = 'Creates a default community chat room if none exists'

    def handle(self, *args, **kwargs):
        if not ChatRoom.objects.exists():
            ChatRoom.objects.create(
                name='community',
                description='GreenLeaf Community Chat - Ask questions and share plant health tips!'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created default community chat room'))
        else:
            self.stdout.write(self.style.SUCCESS('Chat rooms already exist. No action taken.'))