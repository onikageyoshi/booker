import re
import secrets
import string

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

def email_validator(email: str) -> bool:
    """
    Validate email address format using regular expressions.
    
    Uses a regex pattern to check if the provided email string follows
    standard email format conventions.
    
    Args:
        email (str): The email address string to validate.
        
    Returns:
        bool: True if email format is valid, False otherwise.
        
    Example:
        >>> email_validator("user@example.com")
        True
        >>> email_validator("invalid-email")
        False
        
    Note:
        This performs format validation only, not actual email existence verification.
    """
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically secure random OTP consisting of digits only.
    
    Uses the secrets module to ensure cryptographic security for the generated
    one-time password.
    
    Args:
        length (int, optional): Length of the OTP to generate. Defaults to 6.
        
    Returns:
        str: A random numeric string of the specified length.
        
    Example:
        >>> otp = generate_otp()
        >>> len(otp)
        6
        >>> otp = generate_otp(4)
        >>> len(otp)
        4
        
    Note:
        Uses secrets.choice() for cryptographically secure randomness.
    """
    return "".join(secrets.choice(string.digits) for _ in range(length))

def set_user_otp(user, length: int = 6) -> str:
    """
    Generate and set OTP for a user with timestamp and verification status.
    
    Creates a new OTP for the user, sets the creation timestamp, marks as unverified,
    and saves the user instance with only the necessary field updates.
    
    Args:
        user: Django User model instance to set OTP for.
        length (int, optional): Length of the OTP to generate. Defaults to 6.
        
    Returns:
        str: The generated OTP that was set for the user.
        
    Side Effects:
        - Sets user.otp to the generated OTP
        - Sets user.otp_created_at to current timestamp
        - Sets user.otp_verified to False
        - Saves user instance with updated fields only
        
    Example:
        >>> user = User.objects.get(id=1)
        >>> otp = set_user_otp(user)
        >>> print(f"OTP set: {otp}")
        OTP set: 123456
        
    Note:
        Only updates specific fields to optimize database performance.
    """
    otp = generate_otp(length)
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.otp_verified = False
    user.save(update_fields=["otp", "otp_created_at", "otp_verified"])
    return otp

def clear_user_otp(user):
    """
    Clear OTP data from user instance.
    
    Removes OTP and timestamp data from the user, typically called after
    successful verification or when OTP expires.
    
    Args:
        user: Django User model instance to clear OTP data from.
        
    Returns:
        None
        
    Side Effects:
        - Sets user.otp to None
        - Sets user.otp_created_at to None
        - Saves user instance with updated fields only
        
    Example:
        >>> clear_user_otp(user)
        >>> print(user.otp)
        None
        
    Note:
        Does not clear otp_verified field - only the OTP and timestamp.
    """
    user.otp = None
    user.otp_created_at = None
    user.save(update_fields=["otp", "otp_created_at"])


def verfiy_user_otp(user, otp: str) -> bool:
    """
    Verify user-provided OTP against stored OTP with expiry validation.
    
    Validates that the provided OTP matches the user's stored OTP and that
    the OTP hasn't expired (15-minute window from creation).
    
    Args:
        user: Django User model instance with OTP data.
        otp (str): The OTP string to verify against stored OTP.
        
    Returns:
        bool: True if OTP is valid and not expired, False otherwise.
        
    Validation Process:
        1. Checks if user has an OTP set
        2. Compares provided OTP with stored OTP
        3. Validates OTP creation timestamp exists
        4. Checks if OTP is within 15-minute expiry window
        5. Sets otp_verified to True if validation passes
        
    Side Effects:
        - Sets user.otp_verified to True on successful verification
        - Saves user instance with updated otp_verified field
        
    Example:
        >>> is_valid = verfiy_user_otp(user, "123456")
        >>> if is_valid:
        ...     print("OTP verified successfully")
        ... else:
        ...     print("Invalid or expired OTP")
        
    Note:
        OTP expires 15 minutes after otp_created_at timestamp.
    """
    if not user.otp or user.otp != otp:
        return False
    
    if not user.otp_created_at:
        return False
    
    expiry_time = user.otp_created_at + timezone.timedelta(minutes=15)
    if timezone.now() > expiry_time:
        return False
    
    user.otp_verified = True
    user.save(update_fields=["otp_verified"])
    return True

def send_otp_email(user_id: int, otp: str, purpose: str):
    try:
        if isinstance(user_id, User):
            user = user_id
        else:
            user = User.objects.get(id=user_id)
            
        subject = f"Your OTP for {purpose}"
        context = {
            "user": user,
            "otp": otp,
            "purpose": purpose,
            "expiry": "5 minutes"    
        }
        template_path = "emails/otp_email.html"
        html_message = render_to_string(template_path, context)
        
        # ✅ Correct way: Import and use EmailMessage class
        from django.core.mail import EmailMessage
        
        email_message = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email_message.content_subtype = "html"  # Set content type to HTML
        email_message.send()
        
    except User.DoesNotExist:
        raise ValueError("User with the given ID does not exist.")
    except Exception as e:
        raise RuntimeError(f"Failed to send OTP email: {str(e)}")

def get_tokens_for_user(user):
    """
    Generate JWT access and refresh tokens for user authentication.
    
    Creates both refresh and access tokens using Django REST Framework SimpleJWT
    for the provided user instance.
    
    Args:
        user: Django User model instance to generate tokens for.
        
    Returns:
        dict: Dictionary containing refresh and access token strings.
            Format: {
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
            }
            
    Example:
        >>> tokens = get_tokens_for_user(user)
        >>> access_token = tokens['access']
        >>> refresh_token = tokens['refresh']
        >>> print(f"Access token: {access_token[:20]}...")
        
    Dependencies:
        Requires rest_framework_simplejwt to be installed and configured.
        
    Note:
        Token expiration times are controlled by SimpleJWT settings.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


def initiate_password_reset(email):
    """
    Initiate password reset process by generating and sending OTP.
    
    Finds an active user by email, generates an OTP, and sends it via email
    for password reset verification.
    
    Args:
        email (str): User's email address to initiate password reset for.
        
    Returns:
        str or None: Generated OTP string if successful, None if failed.
        
    Process Flow:
        1. Normalizes email (lowercase, stripped whitespace)
        2. Finds active user (excludes DELETED status, requires is_active=True)
        3. Generates and sets OTP for user
        4. Sends OTP email with "password reset" purpose
        5. Returns OTP on success, None on failure
        
    User Filtering:
        - Excludes users with status='DELETED'
        - Only includes users with is_active=True
        - Case-insensitive email matching
        
    Example:
        >>> otp = initiate_password_reset("user@example.com")
        >>> if otp:
        ...     print("Password reset initiated, OTP sent")
        ... else:
        ...     print("Failed to initiate password reset")
        
    Note:
        Returns None for any failure (user not found, email sending failure)
        to avoid revealing user existence.
    """
    try:
        user = User.objects.exclude(status='DELETED').get(email=email.lower().strip(), is_active=True)
        otp = set_user_otp(user)
        if send_otp_email(user.id, otp, "password reset"):
            return otp
        return None
    except User.DoesNotExist:
        return None
    except Exception as e:
        return None

def complete_password_reset(email, otp, new_password):
    """
    Complete password reset by verifying OTP and updating password.
    
    Verifies the provided OTP for the user and updates their password if
    verification is successful.
    
    Args:
        email (str): User's email address.
        otp (str): OTP for verification.
        new_password (str): New password to set for the user.
        
    Returns:
        bool: True if password reset was successful, False otherwise.
        
    Process Flow:
        1. Finds user by email (same filtering as initiate_password_reset)
        2. Verifies provided OTP using verfiy_user_otp()
        3. Sets new password using Django's set_password() method
        4. Clears OTP data from user
        5. Returns success status
        
    Security Features:
        - Uses Django's built-in password hashing via set_password()
        - Validates OTP expiry (15-minute window)
        - Clears OTP after successful reset
        - Same user filtering as initiation
        
    Example:
        >>> success = complete_password_reset(
        ...     "user@example.com", 
        ...     "123456", 
        ...     "newSecurePassword123"
        ... )
        >>> if success:
        ...     print("Password reset successful")
        ... else:
        ...     print("Password reset failed - invalid OTP or user")
        
    Note:
        Returns False for any failure (user not found, invalid OTP, exceptions)
        to maintain security through consistent response behavior.
    """
    try:
        user = User.objects.exclude(status='DELETED').get(email=email.lower().strip(), is_active=True)
        if not verfiy_user_otp(user, otp):
            return False
        user.set_password(new_password)
        user.save(update_fields=["password"])
        clear_user_otp(user)
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        return False