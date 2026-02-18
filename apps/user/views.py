from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    UserCreateSerializer,
    UserDetailSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    OTPVerificationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetCompleteSerializer,
)
from apps.base.account_utils import set_user_otp, send_otp_email, get_tokens_for_user

User = get_user_model()

# -------------------------
# User ViewSet
# -------------------------
@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.exclude(status='DELETED')
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            permission_classes = [IsAdminUser]
        return [perm() for perm in permission_classes]

    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def admin_users(self, request):
        admin_users = self.get_queryset().filter(is_staff=True)
        page = self.paginate_queryset(admin_users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(admin_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# -------------------------
# Authentication Views
# -------------------------
@extend_schema(tags=["Authentication"])
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = serializer.validated_data['tokens']
        return Response({
            "user": UserDetailSerializer(user).data,
            "tokens": tokens
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class LogoutView(generics.GenericAPIView):
    serializer_class = None
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

# -------------------------
# OTP / Email Verification
# -------------------------
@extend_schema(tags=["Verification"])
class EmailVerificationView(generics.GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]

    def get(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email verification")
        return Response({"detail": "OTP sent to your email."}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.otp = None
        user.otp_verified = True
        user.is_active = True
        user.save(update_fields=['otp', 'otp_verified', 'is_active'])
        return Response({"detail": "OTP verified successfully."}, status=status.HTTP_200_OK)

# -------------------------
# Password Reset Views
# -------------------------
@extend_schema(tags=["Password Reset"])
class PasswordRequestResetView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)


@extend_schema(tags=["Password Reset"])
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetCompleteSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save(), status=status.HTTP_200_OK)
