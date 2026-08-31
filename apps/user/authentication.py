from django.core.cache import cache

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CustomJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        jti = token.get("jti")
        if jti and cache.get(f"access_token_blocklist:{jti}"):
            raise InvalidToken("Token is blacklisted.")
        return token

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user and not user.is_active:
            return None
        return user
