# greenleaf/asgi.py

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greenleaf.settings')
django.setup()

from dotenv import load_dotenv
load_dotenv()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import community_chat.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                community_chat.routing.websocket_urlpatterns
            )
        )
    ),
})
