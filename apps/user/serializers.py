from rest_framework import serializers

from django.contrib.auth import get_user_model, authenticate

from apps.base.choices import StatusChoices, UserTypeChoices
from apps.base.account_utils import complete_password_reset, email_validator, get_tokens_for_user, initiate_password_reset, send_otp_email, set_user_otp

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
    meta = serializers.JSONField(read_only=True)  # If meta is a JSONField on User model

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("meta",)
        
        
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
        if len(data['password']) < 8:
            raise serializers.ValidationError("Passwords must be atleast 8 characters.")        
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
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if len(data['new_password']) < 8:
            raise serializers.ValidationError("Passwords must be at least 8 characters.")
        
        if not data['new_password'].isalnum():
            raise serializers.ValidationError("Password must contain both letters and numbers.")
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
        """Main validation method that handles authentication and user status checks"""
        email = data.get('email', "")
        password = data.get('password', "")
        
        # Try to authenticate the user
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        # If authentication failed, check if user exists and their status
        if user is None:
            try:
                user_obj = User.objects.get(email=email)
                # Check user status even if authentication failed
                self.check_user_status(user_obj)
                # If we reach here, the password was wrong but account exists and is active
                raise serializers.ValidationError({"detail": "Invalid credentials."})
            except User.DoesNotExist:
                raise serializers.ValidationError({"detail": "Invalid credentials."})
        
        # If authentication succeeded, check user status
        self.check_user_status(user)
        
        # Generate tokens for the user
        tokens = get_tokens_for_user(user)
        return {
            "user": user,
            "tokens": tokens
        }
    
    def check_user_status(self, user):
        """Helper method to check user status and raise appropriate errors"""
        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is inactive."})
        
        if user.status == StatusChoices.PENDING:
            raise serializers.ValidationError({"detail": "User account is pending approval."})
        
        if user.status == StatusChoices.DELETED:
            raise serializers.ValidationError({"detail": "User account has been deleted."})
        
        if user.status in [StatusChoices.BLOCKED, StatusChoices.SUSPENDED]:
            raise serializers.ValidationError({"detail": "User account is blocked or suspended."})


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)  # Added email field
    otp = serializers.CharField(write_only=True, max_length=6)
    
    def validate_otp(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value
    
    def validate(self, data):
        otp = data.get('otp')
        email = data.get('email')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "User not found."})
        
        if not user.otp or user.otp != otp:
            raise serializers.ValidationError({"detail": "Invalid or expired OTP."})
        
        if user.otp_verified:
            raise serializers.ValidationError({"detail": "OTP already verified."})
        
        # Add user to validated data so it can be accessed in the view
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
        if len(data['new_password']) < 8:
            raise serializers.ValidationError("Passwords must be at least 8 characters.")
        
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
        