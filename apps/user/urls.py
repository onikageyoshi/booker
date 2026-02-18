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
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('otp/', EmailVerificationView.as_view(), name='otp'),
    path('password-reset/', PasswordRequestResetView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
