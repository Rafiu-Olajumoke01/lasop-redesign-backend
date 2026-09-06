from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken

from .authentication import SimpleUser


class AnonymousSimpleUser:
    is_authenticated = False


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        scope['user'] = self.get_user(token)
        return await super().__call__(scope, receive, send)

    def get_user(self, token):
        if not token:
            return AnonymousSimpleUser()
        try:
            access_token = AccessToken(token)
            return SimpleUser(
                user_id=access_token['user_id'],
                username=access_token.get('username', ''),
                full_name=access_token.get('full_name', ''),
                is_tutor=access_token.get('is_tutor', False),
                is_staff=access_token.get('is_staff', False),
            )
        except Exception:
            return AnonymousSimpleUser()