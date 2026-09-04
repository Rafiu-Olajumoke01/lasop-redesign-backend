import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lasop.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter

from chats.middleware import JWTAuthMiddleware
from chats.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})