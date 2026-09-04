from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        scope['user'] = await self.get_user(token)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if not token:
            return AnonymousUser()
        try:
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token['user_id'])
            return user
        except Exception:
            return AnonymousUser()