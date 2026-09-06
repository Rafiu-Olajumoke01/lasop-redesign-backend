from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken


class SimpleUser:
    """A lightweight stand-in for a Django User object, built directly
    from JWT token claims. Used because this service has no access to
    the real Users table (it lives in a different database)."""

    def __init__(self, user_id, username, full_name, is_tutor, is_staff):
        self.id = user_id
        self.username = username
        self.full_name = full_name
        self.is_tutor = is_tutor
        self.is_staff = is_staff
        self.is_authenticated = True

    def get_full_name(self):
        return self.full_name or self.username

    def get_username(self):
        return self.username


class TokenClaimsAuthentication(BaseAuthentication):
    """Authenticates requests using a JWT's claims directly, without
    querying a Users table (since this service's database doesn't have one)."""

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        raw_token = auth_header.split(' ', 1)[1]

        try:
            access_token = AccessToken(raw_token)
        except Exception:
            raise AuthenticationFailed('Invalid or expired token')

        user = SimpleUser(
            user_id=access_token['user_id'],
            username=access_token.get('username', ''),
            full_name=access_token.get('full_name', ''),
            is_tutor=access_token.get('is_tutor', False),
            is_staff=access_token.get('is_staff', False),
        )
        return (user, None)