from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.user.views import (
    UserViewSet,
    LoginView,
    LogoutView,
    ChangePasswordView,
    EmailVerificationView,
    PasswordRequestResetView,
    PasswordResetConfirmView
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/verify-otp/', EmailVerificationView.as_view(), name='verify-otp'),
    path('auth/password-reset-request/', PasswordRequestResetView.as_view(), name='password-reset-request'),
    path('auth/password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
