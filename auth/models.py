from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from oauth2client.django_orm import FlowField, CredentialsField
# Create your models here.
class UserProfile(models.Model):
    #required field
    user = models.ForeignKey(User)
    google_validated = models.BooleanField(default=False)
    identity_validated = models.BooleanField(default=False)
    
    
#Google Flows
class FlowModel(models.Model):
    id = models.ForeignKey(User, primary_key=True)
    flow = FlowField
    
#Google Credentials
class CredentialsModel(models.Model):
    id = models.ForeignKey(User, primary_key=True)
    credential = CredentialsField