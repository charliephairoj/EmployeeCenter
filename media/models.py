import os
import datetime
import dateutil.parser

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.conf import settings
from boto.s3.connection import S3Connection
from boto.s3.key import Key


class Log(models.Model):
    employee = models.ForeignKey(User)
    event = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class S3Object(models.Model):
    bucket = models.TextField()
    key = models.TextField()   

    @classmethod
    def create(cls, filename, key, bucket, delete_original=True, encrypt_key=False, upload=True):
        """
        Creates S3object for a file
        """
        obj = cls()
        if key:
            obj.key = key
        else:
            raise AttributeError("Missing object key")
        if bucket:
            obj.bucket = bucket
        else:
            raise AttributeError("Missing object bucket")
        if upload:
            obj._upload(filename, delete_original, encrypt_key=encrypt_key)
        obj.save()
        return obj

    def upload(self, filename, delete_original=True, encrypt_key=True):
        """
        Uploads a file for this key
        """
        self._upload(filename, delete_original, encrypt_key)
        self.save()

    def generate_url(self, time=1800):
        """
        Generates a url for the object
        """
        conn = self._get_connection()
        return conn.generate_url(time,
                                 'GET',
                                 bucket=self.bucket,
                                 key=self.key,
                                 force_http=True)

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
        bucket = self._get_bucket()
        bucket.delete_key(self.key)
        super(S3Object, self).delete(**kwargs)

    def _get_connection(self):
        """
        Returns the S3 Connection of the object
        """
        return S3Connection()

    def _get_bucket(self):
        """
        Returns the S3 Bucket of the object
        """
        if self.bucket:
            conn = self._get_connection()
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
        return bucket.get_key(self.key)

    def _upload(self, filename, delete_original=True, encrypt_key=False):
        """
        Uploads the file to the to our S3 service

        Requies the filename, the file type. if an Appendix is provided
        then the file is appended with that before the filetype.
        """
        bucket = self._get_bucket()
        k = Key(bucket)
        k.key = self.key
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
    image = models.ForeignKey(S3Object, null=True)
    
    
