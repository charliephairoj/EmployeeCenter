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

    @classmethod
    def create(cls, filename, key, bucket):
        obj = cls()
        if key:
            obj.key = key
        else:
            raise AttributeError("Missing object key")
        if bucket:
            obj.bucket = bucket
        else:
            raise AttributeError("Missing object bucket")
        obj._upload(filename)
        obj.save()
        return obj

    def generate_url(self, time=1800):
        """generate a url for the object"""
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        url = conn.generate_url(time, 'GET', bucket=self.bucket, key=self.key, force_http=True)
        return url

    def _upload(self, filename):
        """Uploads the file to the to our S3 service

        Requies the filename, the file type. if an Appendix is provided
        then the file is appended with that before the filetype.
        """
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket(self.bucket, True)
        k = Key(bucket)
        k.key = self.key
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        os.remove(filename)

