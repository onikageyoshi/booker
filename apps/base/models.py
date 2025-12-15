import uuid
from django.db import models

from apps.base.choices import StatusChoices

class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.DEFAULT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        abstract = True
        