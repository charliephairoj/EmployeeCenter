import os
import logging
import time
import re
from decimal import Decimal

from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
from django.db import models

from supplies.models import Supply as S
from media.models import S3Object


logger = logging.getLogger(__name__)


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
    image = models.ForeignKey(S3Object, related_name='+', null=True, blank=True)
    schematic = models.ForeignKey(S3Object, null=True)
    image_key = models.TextField(null=True)
    image_url = models.TextField(null=True)
    schematic_key = models.TextField(null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    collection = models.TextField(default="Dellarobbia Thailand")
    deleted = models.BooleanField(default=False)
    supplies = models.ManyToManyField(S, through='Supply')
    
    # Constants
    _overhead_percent = 40
    _profit_percent = 35
    
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
        
        
    def calculate_prices(self, apply_prices=False):
        grades = {'A1': 15, 
                  'A2': 20, 
                  'A3': 25,
                  'A4': 30,
                  'A5': 35,
                  'A6': 40}
        
        prices = {}
        
        for grade in grades:
            prices[grade] = self.calculate_price(grades[grade])
            
        if apply_prices:
            for grade in prices:
                Price.objects.create(grade=grade.upper(), product=self, price=prices[grade])
                logger.info("{0} price for {1} created at {2}".format(grade, self.description, prices[grade]))
                
        return prices
        
    def calculate_price(self, grade):
        """
        Calculate the price of the product at the specified grade
        """
        logger.debug("\nCalculating prices for grade {0}".format(grade))
        
        # Calculate all the costs excluding fabric cost
        direct_cost = self._calculate_costs_excluding_fabric()
        
        # Add fabric cost based on quantity of fabric used
        direct_cost += self._calculate_fabric_costs(Supply.objects.get(product=self, description='fabric').quantity, grade)
        
        logger.debug("Total direct material cost is {0:.2f}".format(direct_cost))
        
        # Calculate the total manufacture cost. Minimum cost to make this product 
        # without losing money
        total_manufacture_cost = direct_cost + self._calculate_overhead(direct_cost)
        
        logger.debug("Total manufacture cost is {0:.2f}".format(total_manufacture_cost))
        
        #Calculate the wholesale for this product
        wholesale_price = self._calculate_wholesale_price(total_manufacture_cost)
        
        retail_price = wholesale_price * Decimal('2')
        
        return retail_price
        
    def _calculate_fabric_costs(self, quantity, grade):
        try:
            cost = Decimal(str(quantity)) * Decimal(str(grade)) * Decimal(str(36))
        except InvalidOperation as e:
            if not quantity:
                raise ValueError("Quantity cannot be {0}".format(quantity))
            
            if not grade:
                raise ValueError("Quantity cannot be {0}".format(grade))
        
        logger.debug("Fabric cost is {0}".format(cost))
        
        return cost
        
    def _calculate_costs_excluding_fabric(self):
        """
        Calculate the direct material cost of the product
        """
        cost = 0
        
        for ps in Supply.objects.filter(product=self).exclude(description='fabric').exclude(cost__isnull=True, quantity__isnull=True):
            if ps.supply and ps.quantity:
                #Set supplier in order to retrieve cost
                product = ps.supply.products.all().order_by('cost')[0]
                ps.supply.supplier = product.supplier
                
                #Add the cost of the supply to the total
                try:
                    cost += ps.quantity * (ps.supply.cost / product.quantity_per_purchasing_unit)
                except Exception as e:
                    logger.debug(e)
                    print ps.quantity, ps.description, ps.supply.description
            else:
                cost += (ps.cost or 0)
                
        logger.debug("Costs excluding fabric are {0:.2f}".format(cost))
        
        return cost
        
    def _calculate_overhead(self, direct_costs):
        return direct_costs * (Decimal(str(self._overhead_percent)) / Decimal('100'))
    
    def _calculate_wholesale_price(self, tmc):    
        
        if re.search('^fc-\s+', self.description):
            pp = self._profit_percent + 5
        else:
            pp = self._profit_percent
            
        divisor = 1 - (pp / Decimal('100')) 
        
        price = tmc / divisor
        
        logger.debug("Wholesale price is {0:.2f}".format(price))
        
        return price
        
    def _retrieve_price(self, grade):
        try:
            price = self.prices.get(grade=grade.lower())
            
            logger.debug("Price for {0} at grade {1} is {2:.2f}".format(self.description, grade, price))
            
            return price
        except TypeError:
            raise ValueError("Please specify the grade to retrieve the price for {0}".format(self.description))

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
        
        super(Table, self).__init__(*args, **kwargs)
        self.type = 'table'


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


class Supply(models.Model):
    description = models.TextField(null=True)
    supply = models.ForeignKey(S, null=True)
    product = models.ForeignKey(Product)
    quantity = models.DecimalField(decimal_places=5, max_digits=12, null=True)
    cost = models.DecimalField(decimal_places=5, max_digits=12, null=True)


class Price(models.Model):
    price = models.DecimalField(decimal_places=2, max_digits=12)
    grade = models.TextField()
    product = models.ForeignKey(Product, related_name='prices')
    effective_date = models.DateTimeField(auto_now_add=True)
    
