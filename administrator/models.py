import httplib2
import oauth2client
import base64
import pickle
import six
import logging

from django.db import models
from django.contrib.auth.models import User as AuthUser, UserManager, AbstractUser
from django.contrib import admin
from django.utils.encoding import smart_bytes, smart_text
from oauth2client.client import Storage as BaseStorage
#from oauth2client.contrib.django_orm import FlowField
#from oauth2client.contrib.django_orm import CredentialsField
from gdata.gauth import OAuth2Token


logger = logging.getLogger(__name__)


class CredentialsField(models.Field):

    def __init__(self, *args, **kwargs):
        if 'null' not in kwargs:
            kwargs['null'] = True
        super(CredentialsField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, oauth2client.client.Credentials):
            return value
        return pickle.loads(base64.b64decode(smart_bytes(value)))

    def get_prep_value(self, value):
        if value is None:
            return None
        return smart_text(base64.b64encode(pickle.dumps(value)))

    def from_db_value(self, value, expression, connection, context):

        logger.debug(value)

        return self.to_python(value)

    def value_to_string(self, obj):
        """Convert the field value from the provided model to a string.

        Used during model serialization.

        Args:
            obj: db.Model, model object

        Returns:
            string, the serialized field value
        """
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


class FlowField(models.Field):

    def __init__(self, *args, **kwargs):
        if 'null' not in kwargs:
            kwargs['null'] = True
        super(FlowField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, oauth2client.client.Flow):
            return value
        return pickle.loads(base64.b64decode(value))

    def get_prep_value(self, value):
        if value is None:
            return None
        return smart_text(base64.b64encode(pickle.dumps(value)))

    def from_db_value(self, value, expression, connection, context):

        logger.debug(value)

        return self.to_python(value)

    def value_to_string(self, obj):
        """Convert the field value from the provided model to a string.

        Used during model serialization.

        Args:
            obj: db.Model, model object

        Returns:
            string, the serialized field value
        """
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)


class Storage(BaseStorage):
    """Store and retrieve a single credential to and from the Django datastore.

    This Storage helper presumes the Credentials
    have been stored as a CredenialsField
    on a db model class.
    """

    def __init__(self, model_class, key_name, key_value, property_name):
        """Constructor for Storage.

        Args:
            model: db.Model, model class
            key_name: string, key name for the entity that has the credentials
            key_value: string, key value for the entity that has the
                       credentials
            property_name: string, name of the property that is an
                           CredentialsProperty
        """
        super(Storage, self).__init__()
        self.model_class = model_class
        self.key_name = key_name
        self.key_value = key_value
        self.property_name = property_name

    def locked_get(self):
        """Retrieve stored credential.

        Returns:
            oauth2client.Credentials
        """
        credential = None

        query = {self.key_name: self.key_value}
        entities = self.model_class.objects.filter(**query)
        if len(entities) > 0:
            credential = getattr(entities[0], self.property_name)
            if credential and hasattr(credential, 'set_store'):
                credential.set_store(self)
        return credential

    def locked_put(self, credentials, overwrite=False):
        """Write a Credentials to the Django datastore.

        Args:
            credentials: Credentials, the credentials to store.
            overwrite: Boolean, indicates whether you would like these
                       credentials to overwrite any existing stored
                       credentials.
        """
        args = {self.key_name: self.key_value}

        if overwrite:
            (entity,
             unused_is_new) = self.model_class.objects.get_or_create(**args)
        else:
            entity = self.model_class(**args)

        setattr(entity, self.property_name, credentials)
        entity.save()

    def locked_delete(self):
        """Delete Credentials from the datastore."""

        query = {self.key_name: self.key_value}
        entities = self.model_class.objects.filter(**query).delete()

        
class Company(models.Model):
    name = models.TextField()


class User(AbstractUser):
    reset_password = models.BooleanField(default=False)
    #company = model.ForeignKey(Company)
    

class AWSUser(models.Model):
    user = models.OneToOneField(User, 
                                on_delete=models.CASCADE, 
                                related_name="aws_credentials")
    access_key_id = models.TextField(default="")
    secret_access_key = models.TextField(default="")
    iam_id = models.TextField(default="")
    

class Label(models.Model):
    type = models.TextField()
    category = models.TextField(default="")

    en = models.TextField(default="")
    th = models.TextField(default="")


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