from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from oauth2client.django_orm import CredentialsField




class Log(models.Model):
    employee = models.ForeignKey(User)
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
