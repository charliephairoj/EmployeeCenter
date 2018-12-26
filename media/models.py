import os
import datetime
import dateutil.parser
import logging

from django.db import models
from django.contrib import admin
from administrator.models import User, CredentialsModel, OAuth2TokenFromCredentials, Storage
from django.conf import settings
from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
import boto
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from httplib2 import Http


logger = logging.getLogger(__name__)


class Log(models.Model):
    employee = models.ForeignKey(User)
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class S3Object(models.Model):
    access_key = ''
    secret_key = ''
    version_id = models.TextField(default=None)
    last_modified = models.DateTimeField(auto_now=True)
    bucket = models.TextField()
    key = models.TextField() 
    _size = models.IntegerField(db_column='size', max_length=30, null=True, default=None) 
    _bucket_obj = None

    def __init__(self, *args, **kwargs):

        super(S3Object, self).__init__(*args, **kwargs)

        self._key_obj = None

    @classmethod
    def create(cls, filename, key, bucket, access_key='', secret='', delete_original=True, encrypt_key=False, upload=True):
        """
        Creates S3object for a file
        """
        obj = cls(key=key, bucket=bucket)
        
        
        obj.access_key = access_key
        obj.secret_key = secret
        
        obj.key = key
        assert obj.key is not None
        assert obj.key != ''
        assert obj.key
        
        obj.bucket = bucket
        assert obj.bucket is not None
        assert obj.bucket != ''
        assert obj.bucket
        
        obj.save()
        
        if upload:
            obj.upload(filename, delete_original, encrypt_key=encrypt_key)
            
        obj.save()
        return obj

    @property
    def data(self):
        """
        Return the objects attributes
        as a dictionary
        """

        return {'id': self.id,
                'url': self.generate_url(),
                'last_modified': self.last_modified}

    @property
    def bucket_obj(self):

        if self._bucket_obj is None:
            self._bucket_obj = self._get_bucket()
        elif self._bucket_obj.name != self.bucket:
            self._bucket_obj = self._get_bucket()

        return self._bucket_obj

    @property
    def key_name(self):
        return self.key

    @key_name.setter
    def key_name(self, value):
        self.key = value

    @property
    def key_obj(self):

        if self._key_obj is None:
            self._key_obj = self.bucket_obj.get_key(self.key_name,
                                                    version_id=self.version_id)
            
            if self._size is None or self.version_id is None:
                self._size = self._key_obj.size
                self.version_id = self._key_obj.version_id
                self.save()

        return self._key_obj

    @property
    def size(self):
        if self._size is None:
            self._size = self.key_obj.size

        return self._size

    def upload(self, filename, delete_original=True, encrypt_key=True):
        """
        Uploads a file for this key
        """
        self._upload(filename, delete_original, encrypt_key)
        self.save()

    def download(self, filename=None):
        if filename is None:
            filename = self.key_name.split('/')[-1]

        self.key_obj.get_contents_to_filename(filename)
       
        return filename

    def generate_url(self, key=None, secret=None, time=86400, force_http=False):
        """
        Generates a url for the object
        """
        conn = self._get_connection(key, secret)
        return conn.generate_url(time,
                                 'GET',
                                 bucket=self.bucket,
                                 key=self.key_name,
                                 force_http=force_http)

    def dict(self):
        """
        Return the objects attributes
        as a dictionary
        """

        return {'id': self.id,
                'url': self.generate_url(),
                'last_modified': self.last_modified.isoformat()}

    def to_dict(self):
        """
        Wrapper for dict

        Deprecate in future
        """
        return self.dict()

    def delete(self, **kwargs):
        try:
            bucket = self._get_bucket()
            bucket.delete_key(self.key, version_id=self.version_id)
        except Exception as e:
            logger.warn(e)
            
        super(S3Object, self).delete(**kwargs)

    def _get_connection(self, key, secret):
        """
        Returns the S3 Connection of the object
        """
        return boto.s3.connect_to_region('ap-southeast-1')

    def _get_bucket(self):
        """
        Returns the S3 Bucket of the object
        """
        if self.bucket:
            conn = self._get_connection(self.access_key, self.secret_key)
            bucket = conn.get_bucket(self.bucket, True)
            bucket.configure_versioning(True)
            return bucket
        else:
            raise AttributeError("Missing bucket name.")

    def _get_key(self):
        """
        Returns the S3 Key of the object
        """
        bucket = self._get_bucket()
        return bucket.get_key(self.key, version_id=self.version_id)

    def _upload(self, filename, delete_original=True, encrypt_key=False):
        """
        Uploads the file to the to our S3 service

        Requies the filename, the file type. if an Appendix is provided
        then the file is appended with that before the filetype.
        """
        bucket = self._get_bucket()
        k = Key(bucket)
        k.key = self.key_name
        k.set_contents_from_filename(filename, encrypt_key=encrypt_key)
        k.set_acl('private')
        
        try:
            self.last_modified = dateutil.parser.parse(k.last_modified)
        except:
            self.last_modified = k.last_modified
        
        self.version_id = k.version_id
        if delete_original:
            os.remove(filename)


class Employee(models.Model):
    user = models.OneToOneField(User)
    telephone = models.TextField(null=True)
    #image = models.ForeignKey(S3Object, null=True)


class DriveObject(models.Model):
    service = None
    file_id = models.TextField()
    filename = models.TextField()
    url = models.TextField()

    def upload(self, filename, user=None):
        service = self.get_service(user)
        file_metadata = {
            'name': filename,
        }
        media = MediaFileUpload(filename)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        logger.debug(file)
        self.file_id = file.get('id')
        self.url = file.get('webViewLink')
        self.filename = filename
        self.save()

    def get_service(self, user=None):
        return self.service or self._build_service(user)
    
    def _build_service(self, user=None):
        storage = Storage(CredentialsModel, 'id', user, 'credential')
        cred = storage.get()
        self.service = build('drive', 'v3', credentials=cred)

        return self.service
    
