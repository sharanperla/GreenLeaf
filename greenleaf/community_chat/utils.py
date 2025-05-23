import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def handle_chat_image_upload(room_id: int, user, image_file):
    from .models import ChatMessage, ChatRoom

    try:
        room = ChatRoom.objects.get(pk=room_id)
    except ChatRoom.DoesNotExist:
        raise ValueError(f"No ChatRoom with id={room_id}")

    ext = image_file.name.split('.')[-1]
    filename = f"chat_attachments/{room.id}/{uuid.uuid4().hex}.{ext}"

    path = default_storage.save(filename, ContentFile(image_file.read()))

    message = ChatMessage.objects.create(
        room=room,
        user=user,
        image=path,
        content=""  # optional content
    )

    return message
