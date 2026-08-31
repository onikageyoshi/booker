import logging

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.base.account_utils import send_otp_email, set_user_otp
from apps.user.serializers import ChangePasswordSerializer, LoginSerializer, OTPVerificationSerializer, PasswordResetCompleteSerializer, PasswordResetRequestSerializer, UserCreateSerializer, UserDetailSerializer, UserSerializer, UserUpdateSerializer


User = get_user_model()
logger = logging.getLogger(__name__)

OTP_FAIL_LIMIT = 5
OTP_FAIL_WINDOW = 900  # 15 minutes in seconds
LOGIN_FAIL_LIMIT = 10
LOGIN_FAIL_WINDOW = 900  # 15 minutes in seconds


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.exclude(status='DELETED')
    permission_classes = [IsAuthenticated, permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'admin_users':
            return UserSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [perm() for perm in permission_classes]


    @extend_schema(
        request=UserCreateSerializer,
        responses={
            201: UserDetailSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Create a new user",
        description="Create a new user with email, first name, last name, and password."
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


    @extend_schema(
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="List Users",
        description="Retrieve a list of all users. only admin users can access this endpoint."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @extend_schema(
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Retrieve a user",
        description="Retrieve details of a specific user by ID."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    

    @extend_schema(
        request=UserUpdateSerializer,
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Update a user",
        description="Update details of a specific user by ID."
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Partially Update a user",
        description="Partially Update details of a specific user by ID."
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        responses={
            200: UserSerializer(many=True),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),   
        },
        summary="Lists of Admin Users",
        description="Retrieve a list of all admin users."
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def admin_users(self, request, *args, **kwargs):
        admin_users = self.get_queryset().filter(is_staff=True)
        page = self.paginate_queryset(admin_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(admin_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def _check_login_bruteforce(self, email):
        """Return True if the account is locked due to too many failed login attempts."""
        fail_key = f"login_fail:{email}"
        attempts = cache.get(fail_key, 0)
        return attempts >= LOGIN_FAIL_LIMIT

    def _record_login_failure(self, email):
        """Increment the failed login attempt counter for an email."""
        fail_key = f"login_fail:{email}"
        attempts = cache.get(fail_key, 0)
        cache.set(fail_key, attempts + 1, timeout=LOGIN_FAIL_WINDOW)

    def _clear_login_failures(self, email):
        """Clear the failed login attempt counter on success."""
        cache.delete(f"login_fail:{email}")

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="User Login",
        description="Authenticate a user with email and password."
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()

        if email and self._check_login_bruteforce(email):
            return Response(
                {"detail": "Too many failed login attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            if email:
                self._record_login_failure(email)
            raise

        if email:
            self._clear_login_failures(email)

        user = serializer.validated_data['user']
        tokens = serializer.validated_data['tokens']
        return Response({
            "user": UserDetailSerializer(user).data,
            "tokens": {
                "access": tokens['access'],
                "refresh": tokens['refresh'],
            }
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses={
            200: OpenApiResponse(description="Logout successful"),
            401: OpenApiResponse(description="Unauthorized"),
        },
        summary="User Logout",
        description="Logout a user by invalidating their refresh token."
    )
    def post(self, request, *args, **kwargs):
        refresh = request.data.get('refresh')
        if refresh:
            RefreshToken(refresh).blacklist()

        if hasattr(request, 'auth') and request.auth:
            try:
                jti = request.auth.get('jti')
                if jti:
                    lifetime = int(request.auth.lifetime.total_seconds())
                    cache.set(f"access_token_blocklist:{jti}", "blacklisted", timeout=lifetime)
            except Exception as e:
                logger.warning("Failed to blacklist access token in cache: %s", e)

        return Response(
            {"detail": "Logout successful."},
            status=status.HTTP_200_OK
        )


@extend_schema(tags=["Authentication"])
class ChangePasswordView(generics.GenericAPIView):
    serializer_class =ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Bad Request"),
            401: OpenApiResponse(description="Unauthorized"),
        },
        summary="Change User Password",
        description="Change the password of the authenticated user."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        serializer.save(user=user)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

@extend_schema(tags=["Verfication"])
class EmailVerificationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = OTPVerificationSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def _check_otp_bruteforce(self, email):
        """Return True if the account is locked due to too many failed OTP attempts."""
        fail_key = f"otp_fail:{email}"
        attempts = cache.get(fail_key, 0)
        return attempts >= OTP_FAIL_LIMIT

    def _record_otp_failure(self, email):
        """Increment the failed OTP attempt counter for an email."""
        fail_key = f"otp_fail:{email}"
        attempts = cache.get(fail_key, 0)
        cache.set(fail_key, attempts + 1, timeout=OTP_FAIL_WINDOW)

    def _clear_otp_failures(self, email):
        """Clear the failed OTP attempt counter on success."""
        cache.delete(f"otp_fail:{email}")

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="OTP Sent successfully"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Send OTP",
        description="Send an OTP to the user's email for verification purposes."
    )
    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email', '').strip().lower()
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        generic_msg = {"detail": "If an account with that email exists, an OTP has been sent."}

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(generic_msg, status=status.HTTP_200_OK)

        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email verification")
        return Response(generic_msg, status=status.HTTP_200_OK)

    @extend_schema(
        request=OTPVerificationSerializer,
        responses={
            200: OpenApiResponse(description="OTP Verified successfully"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Verify OTP",
        description="Verify the OTP sent to the user's email."
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()

        if self._check_otp_bruteforce(email):
            return Response(
                {"detail": "Too many failed attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            self._record_otp_failure(email)
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(serializer.errors)

        self._clear_otp_failures(email)

        user = serializer.validated_data['user']
        user.otp = None
        user.otp_created_at = None
        user.otp_verified = True
        user.is_active = True
        user.save(update_fields=['otp', 'otp_created_at', 'otp_verified', 'is_active'])

        return Response({"detail": "OTP verified successfully."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Password Reset"])
class PasswordRequestResetView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"
    
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(response=None),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Initiate Password Reset",
        description="Send an OTP to the user's email for password reset."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetCompleteSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def _check_otp_bruteforce(self, email):
        """Return True if the account is locked due to too many failed OTP attempts."""
        fail_key = f"password_reset_fail:{email}"
        attempts = cache.get(fail_key, 0)
        return attempts >= OTP_FAIL_LIMIT

    def _record_otp_failure(self, email):
        """Increment the failed OTP attempt counter for an email."""
        fail_key = f"password_reset_fail:{email}"
        attempts = cache.get(fail_key, 0)
        cache.set(fail_key, attempts + 1, timeout=OTP_FAIL_WINDOW)

    def _clear_otp_failures(self, email):
        """Clear the failed OTP attempt counter on success."""
        cache.delete(f"password_reset_fail:{email}")
    
    @extend_schema(
        request=PasswordResetCompleteSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Bad Request"),
        },
        summary="Complete Password Reset",
        description="Complete the password reset process by verifying OTP and setting a new password."
    )
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()

        if email and self._check_otp_bruteforce(email):
            return Response(
                {"detail": "Too many failed attempts. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            if email:
                self._record_otp_failure(email)
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError(serializer.errors)

        if email:
            self._clear_otp_failures(email)

        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)