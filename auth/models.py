import os

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
    last_modified = models.DateTimeField()

    @classmethod
    def create(cls, filename, key, bucket, delete_original=True, encrypt_key=False):
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
        obj._upload(filename, delete_original, encrypt_key=encrypt_key)
        obj.save()
        return obj

    def upload(self, filename):
        key = self._get_key()
        key.set_contens_from_filename(filename)

    def generate_url(self, time=1800):
        """generate a url for the object"""
        conn = self._get_connection()
        url = conn.generate_url(time, 'GET', bucket=self.bucket, key=self.key, force_http=True)
        return url

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
        if delete_original:
            os.remove(filename)


