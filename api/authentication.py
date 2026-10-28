"""Authenticate Authorization: Token <token> against expiring UserSession rows."""
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import UserSession


class SessionTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            session = UserSession.objects.select_related("user").get(token=key)
        except UserSession.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")
        if session.expires_at <= timezone.now():
            raise AuthenticationFailed("Token has expired. Please log in again.")
        if not session.user.is_active:
            raise AuthenticationFailed("User account is inactive.")
        return session.user, session
