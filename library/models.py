from django.db import models
from django.conf import settings
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from PIL import Image
import os, time

# Create your models here.


class Book(models.Model):
    description = models.TextField(null=True)
    category =  models.TextField(null=True)
    key = models.TextField(null=True)
    bucket = models.TextField(null=True)
    url = models.TextField(null=True)
    
    def create_thumbnail(self, filename):
        
        file, ext = os.path.splitext(filename)
        image = Image.open(filename)
        image.thumbnail((200,200), Image.ANTIALIAS)
        
        thumb_filename = file+'_thumbnail'+ext
        image.save(thumb_filename, 'JPEG')
        
        #create an epoch key
        key = 'library/thumbnails/'+str(time.time())+ext
        
        url = self.upload_thumbnail(thumb_filename, key=key)
        
        return url
        
    def upload_thumbnail(self, filename, key=None):
        
        k = Key(self.bucket_obj)
        
        #create key and upload
        k.key = key
        k.set_contents_from_filename(filename)
        #remove the original file 
        os.remove(filename)
        #make thumbnail public
        k.set_canned_acl('public-read')
        k.make_public()
        #create the url and return it
        url = "http://media.dellarobbiathailand.com.s3.amazonaws.com/"+key
        return url
        
        
    def upload(self, filename):
        
        #Save first to get id
        self.save()
        
        #access bucket and key
        self.conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        self.bucket_obj = self.conn.get_bucket('media.dellarobbiathailand.com', True)
        k = Key(self.bucket_obj)
        
        #create and upload thumbnail
        url = self.create_thumbnail(filename)
        
        #get extension
        file,ext = os.path.splitext(filename)
        #set key name
        k.key = "library/"+str(self.id)+'.'+ext
        #upload
        k.set_contents_from_filename(filename)
        #delete from system
        os.remove(filename)

        k.set_canned_acl('private')
        
        #save file data to model
        self.bucket = 'media.dellarobbiathailand.com'
        self.key = k.key
        self.url = url
        self.save()
        
        data = {'bucket':self.bucket,'key':self.key, 'url':self.url}        
        return data