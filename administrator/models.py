from django.db import models
from django.contrib.auth.models import User as AuthUser, UserManager

User = AuthUser


class Log(models.Model):
    
    type = models.TextField()
    message = models.TextField()
    user = models.ForeignKey(User, related_name="UserLog")