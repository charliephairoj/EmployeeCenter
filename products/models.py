import os
import logging
import time
from decimal import Decimal

from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
from django.db import models


logger = logging.getLogger('django.request')


#Primary Product class
#where all the other product
#types will inherit from including
# upholstery, tables, cabinets
class Product(models.Model):
    description = models.TextField()
    type = models.CharField(max_length=100)
    wholesale_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    manufacture_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    retail_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    export_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    internalUnits = 'mm',
    externalUnits = 'mm',
    bucket = models.TextField(null=True)
    image_key = models.TextField(null=True)
    image_url = models.TextField(null=True)
    schematic_key = models.TextField(null=True)
    last_modified = models.DateTimeField(auto_now=True)
    collection = models.TextField(default="Dellarobbia Thailand")

    #Meta
    class Meta:
        #permision
        permissions = (('view_manufacture_price', 'Can view the manufacture price'),
                       ('edit_manufacture_price', 'Can edit the manufacture price'),
                       ('view_wholesale_price', 'Can view the wholsale price'),
                       ('edit_wholesale_price', 'Can edit the wholsale price'),
                       ('view_retail_price', 'Can view the retail price'),
                       ('edit_retail_price', 'Can edit the retail price'),
                       ('view_export_price', 'Can view the export price'),
                       ('edit_export_price', 'Can edit the export price'))

    @classmethod
    def create(cls, user=None, **kwargs):
        obj = cls()
        #extract args
        if "user" in kwargs:
            user = kwargs["user"]

        try:
            obj.width = kwargs["width"]
            obj.depth = kwargs["depth"]
            obj.height = kwargs["height"]
        except KeyError:
            raise AttributeError("Product is missing dimensions")

        if user.has_perm('products.edit_manufacture_price'):
            if "manufacture_price" in kwargs:
                obj.manufacture_price = Decimal(str(kwargs["manufacture_price"]))
        if user.has_perm('products.edit_retail_price'):
            if "retail_price" in kwargs:
                obj.retail_price = Decimal(str(kwargs["retail_price"]))
        if user.has_perm('products.edit_wholesale_price'):
            if "wholesale_price" in data:
                obj.wholesale_price = Decimal(str(data["wholesale_price"]))
        if user.has_perm('products.edit_export_price'):
            if "export_price" in data:
                obj.export_price = Decimal(str(data["export_price"]))
        #Set Image
        if "image" in data:
            if 'key' in data['image']:
                key = data['image']['key']
            else:
                key = None
            obj.set_image(key=key, url=data['image']['url'])

        if "back_pillow" in data and data["back_pillow"] != '':
            obj._add_pillow('back', data["back_pillow"])
        if "accent_pillow" in data and data["accent_pillow"] != '':
            obj._add_pillow('accent', data["accent_pillow"])
        if "lumbar_pillow" in data and data["lumbar_pillow"] != '':
            obj._add_pillow('lumbar', data["lumbar_pillow"])
        if "corner_pillow" in data and data["corner_pillow"] != '':
            obj._add_pillow('corner', data["corner_pillow"])
        obj.save()
        return obj

    def update(self, user=None, **kwargs):

        if 'width' in kwargs:
            self.width = kwargs["width"]
        if 'depth' in kwargs:
            self.depth = kwargs["depth"]
        if 'height' in kwargs:
            self.height = kwargs["height"]

        if user:
            if user.has_perm('products.edit_manufacture_price'):
                if "manufacture_price" in kwargs:
                    self.manufacture_price = Decimal(str(kwargs["manufacture_price"]))
            if user.has_perm('products.edit_retail_price'):
                if "retail_price" in kwargs:
                    self.retail_price = Decimal(str(kwargs["retail_price"]))
            if user.has_perm('products.edit_wholesale_price'):
                if "wholesale_price" in kwargs:
                    self.wholesale_price = Decimal(str(kwargs["wholesale_price"]))
            if user.has_perm('products.edit_export_price'):
                if "export_price" in kwargs:
                    self.export_price = Decimal(str(kwargs["export_price"]))

        if "image" in kwargs:
            if 'key' in kwargs['image']:
                key = kwargs['image']['key']
            else:
                key = None
            self.set_image(key=key, url=kwargs['image']['url'])

        if "back_pillow" in kwargs and kwargs["back_pillow"] != '':
            self._add_pillow('back', kwargs["back_pillow"])
        if "accent_pillow" in kwargs and kwargs["accent_pillow"] != '':
            self._add_pillow('accent', kwargs["accent_pillow"])
        if "lumbar_pillow" in kwargs and kwargs["lumbar_pillow"] != '':
            self._add_pillow('lumbar', kwargs["lumbar_pillow"])
        if "corner_pillow" in kwargs and kwargs["corner_pillow"] != '':
            self._add_pillow('corner', kwargs["corner_pillow"])
        self.save()

    def to_dict(self, user=None,):
        data = {'id': self.id,
                'type': self.type,
                'width': self.width,
                'depth': self.depth,
                'height': self.height,
                'units': self.units,
                'type': self.type,
                'description': self.description,
                'url': self.image_url,
                'image': {'url': self.image_url}}
        #Checks to see if there are pillows to add
        pillows = self.pillow_set.all()
        if len(pillows) > 0:
            #Create pillow array in data
            data["pillows"] = []
            #loop through pillow types
            for pillow in pillows:
                #loop through invidual pillows
                for p in range(pillow.quantity):
                    data["pillows"].append({'type': pillow.type})
        #Checks permission
        if user != None:
            if user.has_perm('products.view_manufacture_price'):
                data.update({'manufacture_price': str(self.manufacture_price)})
            if user.has_perm('products.view_wholesale_price'):
                data.update({'wholesale_price': str(self.wholesale_price)})
            if user.has_perm('products.view_retail_price'):
                data.update({'retail_price': str(self.retail_price)})
            if user.has_perm('products.view_export_price'):
                data.update({'export_price': str(self.export_price)})

        return data

    def _add_pillow(self, type, quantity):
        pillow = Pillow()
        pillow.type = type
        pillow.quantity = int(quantity)
        pillow.product = self
        pillow.save()

    #Add Image
    def set_image(self, filename=None, key=None, url=None):
        #If there is no filename
        if filename == None:
            #set data
            self.image_key = key
            self.image_url = url
            self.bucket = 'media.dellarobbiathailand.com'
        #if there is a file name
        else:
            #upload image
            self.upload_image(filename)

    #upload image to s3
    def upload_image(self, filename, key="products/%f.jpg" % time.time()):

        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = key
        #upload file
        k.set_contents_from_filename(filename)
        #remove file from the system
        os.remove(filename)
        #set the Acl
        k.set_canned_acl('public-read')

        #set Url, key and bucket
        self.image_key = k.key
        self.bucket = bucket
        self.image_url = 'http://media.dellarobbiathailand.com.s3.amazonaws.com/%s' % k.key,


class Model(models.Model):
    model = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)
    collection = models.CharField(max_length=100, null=True)
    isActive = models.BooleanField(default=True, db_column='is_active')
    date_created = models.DateField(auto_now=True, auto_now_add=True)
    bucket = models.TextField()
    image_key = models.TextField()
    image_url = models.TextField()
    last_modified = models.DateTimeField(auto_now=True)
    
    @classmethod
    def create(cls, user=None, **kwargs):
        obj = cls()
        try:
            self.model = data["model"]
        except KeyError:
            raise AttributeError("Missing Model")
        try:
            self.model = data["name"]
        except KeyError:
            raise AttributeError("Missing Name")
        try:
            self.model = data["collection"]
        except KeyError:
            raise AttributeError("Missing Collection")

        if "image" in data:
            if "key" in data["image"]:
                self.image_key = data["image"]["key"]
            if "url" in data["image"]:
                self.image_url = data["image"]["url"]
            if "bucket" in data["image"]:
                self.bucket = data["image"]["bucket"]
        obj.save()
        return obj

    def update(self, user=None, **kwargs):
        if "model" in kwargs:
            self.model = kwargs["model"]
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "collection" in kwargs:
            self.collection = kwargs["collection"]
        self.save()
        
    def to_dict(self, **kwargs):
        #prepares array for configs
        configs = []
        #loop through the products to get config
        for product in self.upholstery_set.all():
            configs.append({'configuration': product.configuration.configuration,
                            'id': product.configuration.id})
        #Prepares array to hold image
        images = []
        #iterates over images and adds url to array
        for image in self.modelimage_set.all():
            images.append(image.url)
        #Sets the data object
        data = {"id":self.id,
                "model":self.model,
                "name":self.name,
                "collection":self.collection,
                #"year":model.date_created.year,
                "images":images,
                "configurations":configs,
                'image':{'url':self.image_url}}
        #returns the data object
        return data


class ModelImage(models.Model):
    model = models.ForeignKey(Model)
    url = models.TextField()
    bucket = models.TextField()
    key = models.TextField()

    def upload_image(self, image, **kwargs):

        if image.content_type == "image/jpeg":
            #Get Filename and set extension
            extension = 'jpg'

            #Save self to get id
            self.save()
            #start connection
            conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                                settings.AWS_SECRET_ACCESS_KEY)
            #get the bucket
            bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
            #Create a key and assign it
            k = Key(bucket)

            #Set file name
            k.key = 'products/model_images/' + str(self.id) + '.' + extension
            #upload file
            k.set_contents_from_file(image)
            #set the Acl
            k.set_acl('public-read')
            #set Url, key and bucket
            self.url = "http://media.dellarobbiathailand.com.s3.amazonaws.com/" + k.key
            self.key = k.key
            self.bucket = 'media.dellarobbiathailand.com'
            self.save()


#Creates the Configurations
class Configuration(models.Model):
    configuration = models.CharField(max_length=200)

    def __unicode__(self):
        return self.configuration

    @classmethod
    def create(cls):
        obj = cls()
        try:
            obj.configuration = kwargs["configuration"]
        except KeyError:
            raise AttributeError("Missing configuration")
        obj.save()
        return obj

    def update(self, **kwargs):
        try:
            self.configuration = kwargs["configuration"]
        except KeyError:
            raise AttributeError("Missing configuration")

    def to_dict(self):
        data = {
            "id": self.id,
            "configuration": self.configuration
        }
        return data


#Creates the Upholster class
#that inherits from Products
class Upholstery(Product):
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    category = models.CharField(max_length=50)

    @classmethod
    def create(cls, user=None, **kwargs):
        try:
            model = Model.objects.get(id=kwargs["model"]["id"])
        except KeyError:
            raise AttributeError("Missing the Model ID")
        try:
            configuration = Configuration.objects.get(id=kwargs["configuration"]["id"])
        except KeyError:
            raise AttributeError("Missing the Configuration ID")

        obj = super(Upholstery, cls).create(user, **kwargs)
        obj.model = model
        obj.configuration = configuration
        obj.save()

    def update(self, user=None, **kwargs):
        """
        Updates the upholstery.

        This method with update the parent attributes, and then the objects
        attributes. The user object is required to update certain attributes
        """
        super(Upholstery, self).update(user, **kwargs)

    def to_dict(self, user=None):
        """
        Returns the objects attributes as a dictionary
        """
        data = {"model": {"id": self.model.id,
                          "model": self.model.model,
                          "name": self.model.name},
                "configuration": {"id": self.configuration.id,
                                  "configuration": self.configuration.configuration}}

        data.update(super(Upholstery, self).to_dict(user))
        return data


class Pillow(models.Model):
    product = models.ForeignKey(Product)
    type = models.CharField(max_length=50)
    quantity = models.IntegerField()

    def get_data(self):
        return {'type': self.type,
                'quantity': self.quantity}


class Table(Product):
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    finish = models.TextField()
    color = models.TextField()

    @classmethod
    def create(cls, user=None, **kwargs):
        obj = cls.create(user, **kwargs)
        obj.type = 'table'

        try:
            model = Model.objects.get(id=kwargs["model"]["id"])
            obj.model = model
        except KeyError:
            raise AttributeError("An existing model must be specified")

        try:
            config = Configuration.objects.get(id=kwargs["configuration"]["id"])
            obj.configuration = config
        except KeyError:
            raise AttributeError("An existing model must be specified")

        obj.description = "{0} {1}".format(obj.model.model,
                                            obj.configuration.configuration)
        obj.save()
        return obj

    def update(self, user=None, **kwargs):
        super(Table, self).update(user, **kwargs)
        if 'finish' in kwargs:
            self.finish = kwargs["finish"]
        if 'color' in kwargs:
            self.color = kwargs["color"]
        self.save()

    def to_dict(self, user=None):
        data = {"model": {"id": self.model.id,
                          "model": self.model.model,
                          "name": self.model.name},
                "configuration": {"id": self.configuration.id,
                                  "configuration": self.configuration.configuration},
                'finish': self.finish,
                'color': self.color}
        data.update(super(Table, self).to_dict(user))
        return data


