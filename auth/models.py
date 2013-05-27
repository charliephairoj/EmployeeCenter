from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from oauth2client.django_orm import CredentialsField
from django.contrib.auth.models import AbstractBaseUser


class User(AbstractBaseUser):
    username = models.CharField(max_length=40, unique=True, db_index=True)


class Log(models.Model):
    employee = models.ForeignKey(User)
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
