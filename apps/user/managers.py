from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    
    
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email field is required.")
        
        # olamide@GMAIL.COM => olamide@gmail.com
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
    

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff boolean set to True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff boolean set to True")
        
        self.create_user(email, password, **extra_fields)