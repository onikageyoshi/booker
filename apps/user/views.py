from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.base.account_utils import send_otp_email, set_user_otp
from apps.user.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    OTPVerificationSerializer,
    PasswordResetCompleteSerializer,
    PasswordResetRequestSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.exclude(status="DELETED")

    def get_serializer_class(self):
        if self.action == "list":
            return UserSerializer
        if self.action == "retrieve":
            return UserDetailSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "update" or self.action == "partial_update":
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAdminUser()]

    @extend_schema(
        request=UserCreateSerializer,
        responses={201: UserDetailSerializer, 400: OpenApiResponse(description="Bad Request")},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        responses={200: UserSerializer, 401: OpenApiResponse(description="Unauthorized")},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        responses={200: UserDetailSerializer, 401: OpenApiResponse(description="Unauthorized")},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(request=UserUpdateSerializer, responses={200: UserDetailSerializer})
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(request=UserUpdateSerializer, responses={200: UserDetailSerializer})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        responses={200: UserSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def admin_users(self, request, *args, **kwargs):
        admins = self.get_queryset().filter(is_staff=True)
        page = self.paginate_queryset(admins)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------- AUTHENTICATION ---------------------- #


@extend_schema(tags=["Authentication"])
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = serializer.validated_data["tokens"]
        return Response(
            {
                "user": UserDetailSerializer(user).data,
                "tokens": {"access": tokens["access"], "refresh": tokens["refresh"]},
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh = request.data.get("refresh")
        if refresh:
            RefreshToken(refresh).blacklist()
        return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)


# ---------------------- OTP VERIFICATION ---------------------- #


@extend_schema(tags=["Verification"])
class EmailVerificationView(generics.GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        email = request.query_params.get("email")
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email verification")
        return Response({"detail": "OTP sent to your email."}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.otp = None
        user.otp_created_at = None
        user.otp_verified = True
        user.is_active = True
        user.save(update_fields=["otp", "otp_created_at", "otp_verified", "is_active"])
        return Response({"detail": "OTP verified successfully."}, status=status.HTTP_200_OK)


# ---------------------- PASSWORD RESET ---------------------- #


@extend_schema(tags=["Password Reset"])
class PasswordRequestResetView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=["Password Reset"])
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetCompleteSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)
