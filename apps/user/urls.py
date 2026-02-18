from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.user import views

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="users")

urlpatterns = [
    # ViewSet routes (list, retrieve, create, update, partial_update, destroy)
    path("", include(router.urls)),

    # Authentication
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change-password"),

    # OTP Verification
    path("auth/email-verification/", views.EmailVerificationView.as_view(), name="email-verification"),

    # Password Reset
    path("auth/password-reset/request/", views.PasswordRequestResetView.as_view(), name="password-reset-request"),
    path("auth/password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]
