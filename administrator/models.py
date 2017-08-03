import httplib2

from django.db import models
from django.contrib.auth.models import User as AuthUser, UserManager
from django.contrib import admin
from oauth2client.contrib.django_orm import FlowField
from oauth2client.contrib.django_orm import CredentialsField
from gdata.gauth import OAuth2Token


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
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, related_name='UserLogs')
    
    
class CredentialsModel(models.Model):
    id = models.ForeignKey(User, primary_key=True)
    credential = CredentialsField()


class CredentialsAdmin(admin.ModelAdmin):
    pass


class OAuth2TokenFromCredentials(OAuth2Token):
    def __init__(self, credentials):
        self.credentials = credentials
        super(OAuth2TokenFromCredentials, self).__init__(None, None, None, None)
        self.UpdateFromCredentials()
    
    def UpdateFromCredentials(self):
        self.client_id = self.credentials.client_id
        self.client_secret = self.credentials.client_secret
        self.user_agent = self.credentials.user_agent
        self.token_uri = self.credentials.token_uri
        self.access_token = self.credentials.access_token
        self.refresh_token = self.credentials.refresh_token
        self.token_expiry = self.credentials.token_expiry
        self._invalid = self.credentials.invalid
    
    def generate_authorize_url(self, *args, **kwargs): raise NotImplementedError
    def get_access_token(self, *args, **kwargs): raise NotImplementedError
    def revoke(self, *args, **kwargs): raise NotImplementedError
    def _extract_tokens(self, *args, **kwargs): raise NotImplementedError
    
    def _refresh(self, unused_request):
        self.credentials._refresh(httplib2.Http().request)
        self.UpdateFromCredentials()
        
admin.site.register(CredentialsModel, CredentialsAdmin)