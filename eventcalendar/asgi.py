import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import calendarapp.routing  # vom crea acest fișier

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventcalendar.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            calendarapp.routing.websocket_urlpatterns
        )
    ),
})
