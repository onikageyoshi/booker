from rest_framework import serializers

from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password

from apps.base.choices import StatusChoices, UserTypeChoices
from apps.base.account_utils import complete_password_reset, email_validator, get_tokens_for_user, hash_otp, initiate_password_reset, send_otp_email, set_user_otp

from django.utils import timezone

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    
    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "full_name", "is_active", "status", "user_type"
        )
        read_only_fields = ("id", "is_active", "status", "user_type")
        
class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields
        
        
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input": "password"})
    
    class Meta:
        model = User
        fields = (
            "email", "first_name", "last_name", "password", "confirm_password"
        )
        extra_kwargs = {
            "user_type": {"default": UserTypeChoices.USER},
            "is_active": False
        }

    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format.")
        
        return value.lower()
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(data['password'])
        return data
        
    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        validated_data['is_active'] = False

        user = User.objects.create_user(
            email=validated_data.pop('email'),
            password=validated_data.pop('password'),
            **validated_data
        )
        otp = set_user_otp(user)
        send_otp_email(user.id, otp, "email verification")
        return user
    
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "user_type")
        read_only_fields = ("email", "user_type")
        
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input": "password"})
    new_password = serializers.CharField(write_only=True, style={"input": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input": "password"})
    
    def validate(self, data):
        if not self.context.get('request') or not self.context['request'].user:
            raise serializers.ValidationError({"old_password": "Authentication context required."})
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Current password is incorrect."})
        if data['new_password'] == data['old_password']:
            raise serializers.ValidationError({"new_password": "New password must differ from current password."})
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        validate_password(data['new_password'])
        return data
    
    def save(self, user):
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input": "password"})
    
    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format.")
        return value.lower()
    
    def validate(self, data):
        """Authenticate first, then check account status.
        
        Always returns a generic error on authentication failure to prevent
        user enumeration. Account status checks run only after successful
        authentication.
        """
        email = data.get('email', "")
        password = data.get('password', "")
        
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        if user is None:
            raise serializers.ValidationError({"detail": "Invalid credentials."})
        
        # Post-auth status checks — safe because authenticate() already proved identity
        if not user.otp_verified:
            raise serializers.ValidationError({"detail": "Email not verified. Please verify your email before logging in."})
        if user.status == StatusChoices.PENDING:
            raise serializers.ValidationError({"detail": "User account is pending approval."})
        if user.status == StatusChoices.DELETED:
            raise serializers.ValidationError({"detail": "User account has been deleted."})
        if user.status in [StatusChoices.BLOCKED, StatusChoices.SUSPENDED]:
            raise serializers.ValidationError({"detail": "User account is blocked or suspended."})
        
        tokens = get_tokens_for_user(user)
        return {
            "user": user,
            "tokens": tokens
        }


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)  # Added email field
    otp = serializers.CharField(write_only=True, max_length=6)
    
    def validate_otp(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value
    
    def validate(self, data):
        import hmac as _hmac
        otp = data.get('otp')
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid or expired OTP."})
        
        if not user.otp:
            raise serializers.ValidationError({"detail": "Invalid or expired OTP."})
        
        hashed_input = hash_otp(otp)
        if not _hmac.compare_digest(user.otp, hashed_input):
            raise serializers.ValidationError({"detail": "Invalid or expired OTP."})
        
        if user.otp_verified:
            raise serializers.ValidationError({"detail": "OTP already verified."})
        
        if user.otp_created_at:
            expiry_time = user.otp_created_at + timezone.timedelta(minutes=15)
            if timezone.now() > expiry_time:
                raise serializers.ValidationError({"detail": "OTP has expired. Please request a new one."})
        
        data['user'] = user
        return data
    

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format.")
        return value.lower()
    
    def save(self):
        email = self.validated_data['email']
        initiate_password_reset(email)
        return {
            "message": "If an account with this email exists, a password reset link has been sent."
        }
        

class PasswordResetCompleteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(write_only=True, max_length=6)
    new_password = serializers.CharField(write_only=True, style={"input": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input": "password"})
    
    def validate_email(self, value):
        if not email_validator(value):
            raise serializers.ValidationError("Invalid email format.")
        return value.lower()
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        email = data.get('email', '')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "User not found."})
        validate_password(data['new_password'], user=user)
        return data
    
    def save(self):
        email = self.validated_data['email']
        otp = self.validated_data['otp']
        new_password = self.validated_data['new_password']
        
        sucesss = complete_password_reset(email, otp, new_password)
        
        if not sucesss:
            raise serializers.ValidationError(
                {"detail": "Password reset failed. Invalid OTP or user not found."}
                )
        
        return {
            "message": "Password reset successful. You can now log in with your new password."
        }
        