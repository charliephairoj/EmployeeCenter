from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from oauth2client.django_orm import CredentialsField


class UserProfile(models.Model):
    #required field
    user = models.ForeignKey(User)
    google_validated = models.BooleanField(default=False)
    identity_validated = models.BooleanField(default=False)

    class Meta:
        app_label = 'auth'


class CredentialsModel(models.Model):
    id = models.ForeignKey(User, primary_key=True)
    credential = CredentialsField()


class Log(models.Model):
    employee = models.ForeignKey(User)
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
