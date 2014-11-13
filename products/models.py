import os
import logging
import time
from decimal import Decimal

from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
from django.db import models

from media.models import S3Object


logger = logging.getLogger('django.request')


class Product(models.Model):
    description = models.TextField()
    type = models.CharField(max_length=100)
    
    #New single price for all orders
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    #Will replace all other prices with just 1 "price"
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
    image = models.ForeignKey(S3Object, related_name='+', null=True)
    schematic = models.ForeignKey(S3Object, null=True)
    image_key = models.TextField(null=True)
    image_url = models.TextField(null=True)
    schematic_key = models.TextField(null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    collection = models.TextField(default="Dellarobbia Thailand")
    deleted = models.BooleanField(default=False)

    class Meta:
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

        try:
            obj.width = kwargs["width"]
            obj.depth = kwargs["depth"]
            obj.height = kwargs["height"]
        except KeyError:
            raise AttributeError("Product is missing dimensions")

        if "description" in kwargs:
            obj.description = kwargs["description"]

       
        if "manufacture_price" in kwargs:
            obj.manufacture_price = Decimal(str(kwargs["manufacture_price"]))
        if "retail_price" in kwargs:
            obj.retail_price = Decimal(str(kwargs["retail_price"]))
        if "wholesale_price" in kwargs:
            obj.wholesale_price = Decimal(str(kwargs["wholesale_price"]))
        if "export_price" in kwargs:
            obj.export_price = Decimal(str(kwargs["export_price"]))
        if "price" in kwargs:
            obj.price = Decimal(str(kwargs['price']))
        else:
            raise ValueError("Expecting a price for this product")
        
        obj.save()
        #Post save stuff

        if "image" in kwargs:
            if 'id' in kwargs['image']:
                obj.image = S3Object.objects.get(id=kwargs['image']['id'])

        if "back_pillow" in kwargs and kwargs["back_pillow"] != '':
            obj._add_pillow('back', kwargs["back_pillow"])
        if "accent_pillow" in kwargs and kwargs["accent_pillow"] != '':
            obj._add_pillow('accent', kwargs["accent_pillow"])
        if "lumbar_pillow" in kwargs and kwargs["lumbar_pillow"] != '':
            obj._add_pillow('lumbar', kwargs["lumbar_pillow"])
        if "corner_pillow" in kwargs and kwargs["corner_pillow"] != '':
            obj._add_pillow('corner', kwargs["corner_pillow"])
            
        return obj

    def update(self, user=None, **kwargs):

        if 'width' in kwargs:
            self.width = kwargs["width"]
        if 'depth' in kwargs:
            self.depth = kwargs["depth"]
        if 'height' in kwargs:
            self.height = kwargs["height"]
            
        if user:
            if "manufacture_price" in kwargs:
                if user.has_perm('products.edit_manufacture_price'):
                    self.manufacture_price = Decimal(str(kwargs["manufacture_price"]))
            if "retail_price" in kwargs:
                if user.has_perm('products.edit_retail_price'):
                    self.retail_price = Decimal(str(kwargs["retail_price"]))
            if "wholesale_price" in kwargs:
                if user.has_perm('products.edit_wholesale_price'):
                    self.wholesale_price = Decimal(str(kwargs["wholesale_price"]))
            if "export_price" in kwargs:
                if user.has_perm('products.edit_export_price'):
                    self.export_price = Decimal(str(kwargs["export_price"]))

        if "image" in kwargs:
            if 'id' in kwargs['image']:
                self.image = S3Object.objects.get(id=kwargs['image']['id'])

        if "back_pillow" in kwargs:
            try:
                pillow = self.pillow_set.get(type='back')
                pillow.quantity = kwargs['back_pillow']
                pillow.save()
            except Pillow.DoesNotExist:
                self._add_pillow('back', kwargs['back_pillow'])

        if "accent_pillow" in kwargs:
            try:
                pillow = self.pillow_set.get(type='accent')
                pillow.quantity = kwargs['accent_pillow']
                pillow.save()
            except Pillow.DoesNotExist:
                self._add_pillow('accent', kwargs["accent_pillow"])

        if "lumbar_pillow" in kwargs:
            try:
                pillow = self.pillow_set.get(type='lumbar')
                pillow.quantity = kwargs['lumbar_pillow']
                pillow.save()
            except Pillow.DoesNotExist:
                self._add_pillow('lumbar', kwargs["lumbar_pillow"])

        if "corner_pillow" in kwargs:
            try:
                pillow = self.pillow_set.get(type='corner')
                pillow.quantity = kwargs['corner_pillow']
                pillow.save()
            except Pillow.DoesNotExist:
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
                'deleted': self.deleted}
        if self.image:
                data['image'] = {'url': self.image.generate_url()}
        if self.wholesale_price:
                data["has_price"] = True

        #Checks to see if there are pillows to add
        pillows = self.pillow_set.all()
        if len(pillows) > 0:
            #Create pillow array in data
            data["pillows"] = []
            #loop through pillow types
            for pillow in pillows:
                data['{0}_pillow'.format(pillow.type)] = pillow.quantity
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


class Model(models.Model):
    model = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)
    collection = models.CharField(max_length=100, null=True)
    isActive = models.BooleanField(default=True, db_column='is_active')
    date_created = models.DateField(auto_now=True, auto_now_add=True)
    bucket = models.TextField()
    images = models.ManyToManyField(S3Object, through='ModelImage')
    image_key = models.TextField()
    image_url = models.TextField()
    last_modified = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls, user=None, **kwargs):
        obj = cls()
        try:
            obj.model = kwargs["model"]
        except KeyError:
            raise AttributeError("Missing Model")
        try:
            obj.name = kwargs["name"]
        except KeyError:
            raise AttributeError("Missing Name")
        try:
            obj.collection = kwargs["collection"]
        except KeyError:
            raise AttributeError("Missing Collection")

        if "image" in kwargs:
            if "id" in kwargs["image"]:
                obj.images.add(S3Object.objects.get(id=kwargs["image"]["id"]))
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

    def to_dict(self, *args, **kwargs):
        #prepares array for configs
        configs = []
        #loop through the products to get config
        for product in self.upholstery_set.all():
            configs.append({'configuration': product.configuration.configuration,
                            'id': product.configuration.id})

        data = {"id": self.id,
                "model": self.model,
                "name": self.name,
                "collection": self.collection,
                "configurations": configs,
                'images': [image.generate_url() for image in self.images.all()]}
        try:
            data.update({'image': {'url': self.images.all()[0].generate_url()}})
        except:
            pass
        #returns the data object
        return data


class ModelImage(models.Model):
    model = models.ForeignKey(Model)
    image = models.ForeignKey(S3Object)
    url = models.TextField(null=True)
    bucket = models.TextField(null=True)
    key = models.TextField(null=True)


class Configuration(models.Model):
    configuration = models.CharField(max_length=200)

    def __unicode__(self):
        return self.configuration

    @classmethod
    def create(cls, **kwargs):
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

    def to_dict(self, user=None, **kwargs):
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
    category = models.CharField(max_length=50, null=True)

    def __init__(self, *args, **kwargs):
        
        super(Upholstery, self).__init__(*args, **kwargs)
        
        self.type = 'upholstery'
        
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

        obj = cls()

        try:
            obj.width = kwargs["width"]
            obj.depth = kwargs["depth"]
            obj.height = kwargs["height"]
        except KeyError:
            raise AttributeError("Product is missing dimensions")

        if user:
            if user.has_perm('products.edit_manufacture_price'):
                if "manufacture_price" in kwargs:
                    obj.manufacture_price = Decimal(str(kwargs["manufacture_price"]))
            if user.has_perm('products.edit_retail_price'):
                if "retail_price" in kwargs:
                    obj.retail_price = Decimal(str(kwargs["retail_price"]))
            if user.has_perm('products.edit_wholesale_price'):
                if "wholesale_price" in kwargs:
                    obj.wholesale_price = Decimal(str(kwargs["wholesale_price"]))
            if user.has_perm('products.edit_export_price'):
                if "export_price" in kwargs:
                    obj.export_price = Decimal(str(kwargs["export_price"]))

        obj.model = model
        obj.configuration = configuration
        obj.description = "{0} {1}".format(obj.model.model,
                                            obj.configuration.configuration)
        obj.type = "Upholstery"
        obj.save()
        #Post save stuff

        if "image" in kwargs:
            if 'id' in kwargs['image']:
                obj.image = S3Object.objects.get(id=kwargs['image']['id'])

        if "back_pillow" in kwargs and kwargs["back_pillow"] != '':
            obj._add_pillow('back', kwargs["back_pillow"])
        if "accent_pillow" in kwargs and kwargs["accent_pillow"] != '':
            obj._add_pillow('accent', kwargs["accent_pillow"])
        if "lumbar_pillow" in kwargs and kwargs["lumbar_pillow"] != '':
            obj._add_pillow('lumbar', kwargs["lumbar_pillow"])
        if "corner_pillow" in kwargs and kwargs["corner_pillow"] != '':
            obj._add_pillow('corner', kwargs["corner_pillow"])

        return obj

    def update(self, user=None, **kwargs):
        """
        Updates the upholstery.

        This method with update the parent attributes, and then the objects
        attributes. The user object is required to update certain attributes
        """
        super(Upholstery, self).update(user=user, **kwargs)

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
    product = models.ForeignKey(Product, related_name="pillows")
    type = models.CharField(max_length=50)
    quantity = models.IntegerField()

    def to_dict(self):
        return {'type': self.type,
                'quantity': self.quantity}


class Table(Product):
    model = models.ForeignKey(Model, on_delete=models.PROTECT)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    finish = models.TextField()
    color = models.TextField()
    
    def __init__(self, *args, **kwargs):
        """
        Implements custom __init__ and calls  the
        parent method as well
        """
        self.type = 'table'
        
        super(Table, self).__init__(*args, **kwargs)

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

        obj = cls()

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
            if "wholesale_price" in kwargs:
                obj.wholesale_price = Decimal(str(kwargs["wholesale_price"]))
        if user.has_perm('products.edit_export_price'):
            if "export_price" in kwargs:
                obj.export_price = Decimal(str(kwargs["export_price"]))

        obj.model = model
        obj.configuration = configuration
        obj.description = "{0} {1}".format(obj.model.model,
                                            obj.configuration.configuration)
        obj.type = "table"
        obj.save()
        #Post save stuff

        if "image" in kwargs:
            if 'id' in kwargs['image']:
                obj.image = S3Object.objects.get(id=kwargs['image']['id'])

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


class Rug(Product):

    price_per_sq_meter = models.DecimalField(decimal_places=2, max_digits=9)
    price_per_sq_foot = models.DecimalField(decimal_places=2, max_digits=9)

    @classmethod
    def create(cls, user=None, **kwargs):
        obj = super(Rug,cls).create(user, **kwargs)
        obj.type = 'rug'
        obj.save()
        return obj

    def update(self, user=None, **kwargs):
        super(Table, self).update(user, **kwargs)
        self.save()

    def to_dict(self, user=None):
        data = {}
        data.update(super(Table, self).to_dict(user))
        return data


