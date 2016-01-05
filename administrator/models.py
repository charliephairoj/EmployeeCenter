from django.db import models
from django.contrib.auth.models import User as AuthUser, UserManager

User = AuthUser

class AWSUser(models.Model):
    user = models.OneToOneField(User, 
                                on_delete=models.CASCADE, 
                                related_name="aws_credentials")
    access_key_id = models.TextField(default="")
    secret_access_key = models.TextField(default="")
    iam_id = models.TextField(default="")
    


class Log(models.Model):
    type = models.TextField()
    message = models.TextField()
    user = models.ForeignKey(User, related_name="UserLog")
    