from django.db import models

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from apps.base.choices import UserTypeChoices
from apps.base.models import BaseModel

from .managers import UserManager

class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    user_type = models.CharField(max_length=20, choices=UserTypeChoices.choices, default=UserTypeChoices.USER)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at  = models.DateTimeField(blank=True, null=True)
    is_student = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name",]

    objects = UserManager() 
    
    def __str__(self):
        return self.first_name


    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name    
