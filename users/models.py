from django.contrib.auth.models import AbstractUser
from django.db import models


class DjangoUser(AbstractUser):
    """
    Django User model for authentication with Django's auth system.
    This is separate from our MongoDB User model used for data storage.
    """
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_users'
        
    def __str__(self):
        return self.email
