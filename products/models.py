import os
import logging
import time
import re
import math
from decimal import Decimal

from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
from django.db import models

from supplies.models import Supply as S, Lumber
from media.models import S3Object


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
    last_modified = models.DateTimeField(auto_now=True)
    collection = models.TextField(default="Dellarobbia Thailand")
    deleted = models.BooleanField(default=False)
    supplies = models.ManyToManyField(S, through='Supply')
    
    # Constants
    _overhead_percent = 40
    _profit_percent = 20
    
    class Meta:
        permissions = (('view_manufacture_price', 'Can view the manufacture price'),
                       ('edit_manufacture_price', 'Can edit the manufacture price'),
                       ('view_wholesale_price', 'Can view the wholsale price'),
                       ('edit_wholesale_price', 'Can edit the wholsale price'),
                       ('view_retail_price', 'Can view the retail price'),
                       ('edit_retail_price', 'Can edit the retail price'),
                       ('view_export_price', 'Can view the export price'),
                       ('edit_export_price', 'Can edit the export price'),
                       ('edit_dimensions', 'Can edit dimensions'))

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
        
    def get_prices(self):
        #Calculate supply quantities before calculating cost
        try:
            pass#self.calculate_supply_quantities()
        except AttributeError:
            pass
            
        grades = {'A1': 15, 
                  'A2': 20, 
                  'A3': 25,
                  'A4': 30,
                  'A5': 35,
                  'A6': 40}
        
        prices = {}
        
        # Calculate the direct cost here, so that it doens't have to be recalculated
        # for each grade
        if self.prices.all().count() < len(grades):
            direct_cost = self._calculate_costs_excluding_fabric()
        
        for grade in grades:
            # Retrieve the stored grade, or calculate if no grade is stored
            try:
                logger.info("Retrieving price for grade {0}".format(grade))
                prices[grade] = self.get_price(grade.upper()).price
            except Price.DoesNotExist:
                logger.info('Price for grade {0} does not exist'.format(grade))
                prices[grade] = self.calculate_price(grades[grade], direct_cost=direct_cost)

        return prices
        
    def calculate_prices(self, apply_prices=False):
        #Calculate supply quantities before calculating cost
        try:
            pass#self.calculate_supply_quantities()
        except AttributeError:
            pass
            
        grades = {'A1': 15, 
                  'A2': 20, 
                  'A3': 25,
                  'A4': 30,
                  'A5': 35,
                  'A6': 40}
        
        prices = {}
        
        # Calculate the direct cost here, so that it doens't have to be recalculated
        # for each grade
        direct_cost = self._calculate_costs_excluding_fabric()
        
        for grade in grades:
            # Calculate if no grade is stored
            logger.info("Calculating price for grade {0}".format(grade))
            prices[grade] = self.calculate_price(grades[grade], direct_cost=direct_cost)
            
        if apply_prices:
            
            Price.objects.filter(product=self).delete()
            
            for grade in prices:
                
                Price.objects.create(grade=grade.upper(), product=self, price=prices[grade])
                    
                logger.info("{0} price for {1} created at {2}".format(grade, self.description, prices[grade]))
                
        return prices
        
    def get_price(self, grade):
        return self.prices.get(grade=grade)
        
    def calculate_price(self, grade, direct_cost=None):
        """
        Calculate the price of the product at the specified grade
        """
        logger.debug("\nCalculating prices for grade {0}".format(grade))
        
        # Calculate all the costs excluding fabric cost
        if not direct_cost:
            direct_cost = self._calculate_costs_excluding_fabric()
        
        # Add fabric cost based on quantity of fabric used
        try:
            direct_cost += self._calculate_fabric_costs(Supply.objects.get(product=self, description='fabric').quantity, grade)
        except Supply.DoesNotExist as e:
            raise ValueError('Missing fabric quantity for {0}'.format(self.description))

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
        except Exception as e:
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
        logger.info('Calculating costs excluding fabric for {0}'.format(self.description))
        
        cost = 0
        
        for ps in Supply.objects.filter(product=self).exclude(description='fabric').exclude(cost__isnull=True, quantity__isnull=True):
            if ps.supply and ps.quantity:
                #Set supplier in order to retrieve cost
                product = ps.supply.products.all().order_by('cost')[0]
                ps.supply.supplier = product.supplier
                
                if product.supplier.currency.lower() == 'usd':
                    currency_modifier = 36
                elif product.supplier.currency.lower() == 'eur':
                    currency_modifier = 39
                elif product.supplier.currency.lower() == 'rmb':
                    currency_modifier = 5.7
                else:
                    currency_modifier = 1
                    
                #Add the cost of the supply to the total
                try:
                    cost += ps.quantity * ((ps.supply.cost * currency_modifier)/ product.quantity_per_purchasing_unit)
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
        elif re.search('^ac-\s+', self.description):
            pp = self._profit_percent + 15
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
    type = models.TextField(default="upholstery")
    model = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=100, null=True)
    collection = models.CharField(max_length=100, null=True)
    is_active = models.BooleanField(default=True, db_column='is_active')
    web_active = models.BooleanField(default=False)
    date_created = models.DateField(auto_now_add=True)
    bucket = models.TextField()
    #images = models.ManyToManyField(S3Object, through='ModelImage')
    image_key = models.TextField()
    image_url = models.TextField()
    last_modified = models.DateTimeField(auto_now=True)
    has_back_pillows = models.BooleanField(default=True)
    has_arms = models.BooleanField(default=True)
    arm_width = models.DecimalField(max_digits=15, decimal_places=2, default=200)
    arm_height = models.DecimalField(max_digits=15, decimal_places=2, default=300)
    base_height = models.DecimalField(max_digits=15, decimal_places=2, default=200)
    back_depth = models.DecimalField(max_digits=15, decimal_places=2, default=200)
    
    #Descriptions
    frame = models.TextField()
    suspension = models.TextField()
    cushions = models.TextField()
    upholstery = models.TextField()
    legs = models.TextField()

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
    

class Image(S3Object):
    model = models.ForeignKey(Model, related_name='images')
    primary = models.BooleanField(default=False, db_column='primary_image')
    configuration = models.BooleanField(default=False)
    web_active = models.BooleanField(default=False)

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


class Upholstery(Product):
    """
    Upholstery Class
    
    This class inherits from the product class and extends it. This class
    is for all upholstered furniture, which means furniture that one can 
    sit on.
    """
    model = models.ForeignKey(Model, on_delete=models.PROTECT, related_name="upholsteries")
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
        
    def calculate_supply_quantities(self):
        """
        Calculate the quantities of supplies used by this furniture 
        """
        # Calculate pillow quantites
        self.validate_pillows()
        
        # Caculate the quantity of lumber
        #self.calculate_lumber_quantity()
        
        # Calculate the quantity of plywood
        self.calculate_plywood_quantity()
        
        # Calculate the quantity of webbing
        # from dimensions
        try:
            self.calculate_webbing_quantity()
        except TypeError as e:
            logger.debug("{0} \n {1}: Width: {2} // Depth: {3}".format(e, self.description, self.width, self.depth))
        
        # Calculate fiber ball quantities by 
        # using the quantities of pillows
        self.calculate_fiber_ball_quantity()
        
        #Calculate fiber padding quantity used by the frame
        self.calculate_100g_fiber_padding_quantity()
        
        # Calculate the 200g fiber ball quantity used by the cushions
        self.calculate_200g_fiber_padding_quantity()
        
    def validate_pillows(self):
        """
        Validate that pillows exists and that the quantities
        are correct based on these rules:
        
        -Sofa: 3 back pillows, 3 accent pillows
        -Loveseat: 2 back pillows, 2 accent pillows
        -chair: 1 back pillow, 1 accent pillow
        """
        config = self.configuration.configuration.lower()
        modifier = 1 if self.model.has_back_pillows else 0
        
        if "sofa" in config:
            pillows = {'back': 3 * modifier, 'accent': 3}
        elif "loveseat" in config:
            pillows = {'back': 2 * modifier, 'accent': 2}
        elif "chair" in config:
            pillows = {'back': 1 * modifier, 'accent': 1}
        elif "corner" in config:
            pillows = {'back': 2 * modifier, 'accent': 1}
        elif "chaise" in config:
            pillows = {'back': 1 * modifier, 'accent': 1}
        else:
            pillows = None
           
        if not self.pillows.all().exists():
             logger.debug('Creating pillows for {0}'.format(self.description))
             if pillows:
                 for pillow_type in pillows:
                     # Creates a pillow if the quantity is more than 0
                     if pillows[pillow_type]:
                         Pillow.objects.create(product=self, type=pillow_type, quantity=pillows[pillow_type])
                         
    def create_pillows(self):
        """
        Validate that pillows exists and that the quantities
        are correct based on these rules:
        
        -Sofa: 3 back pillows, 3 accent pillows
        -Loveseat: 2 back pillows, 2 accent pillows
        -chair: 1 back pillow, 1 accent pillow
        """
        config = self.configuration.configuration.lower()
        modifier = 1 if self.model.has_back_pillows else 0
        
        if "sofa" in config:
            pillows = {'back': 3 * modifier, 'accent': 3}
        elif "loveseat" in config:
            pillows = {'back': 2 * modifier, 'accent': 2}
        elif "chair" in config:
            pillows = {'back': 1 * modifier, 'accent': 1}
        elif "corner" in config:
            pillows = {'back': 2 * modifier, 'accent': 1}
        elif "chaise" in config:
            pillows = {'back': 1 * modifier, 'accent': 1}
        else:
            pillows = None
            
        if "return" in config:
            try:
                pillows['back'] += (1 * modifier)
            except KeyError:
                pillows['back'] = (1 * modifier)
            
           
        self.pillows.all().delete()
        
        logger.debug('Creating pillows for {0}'.format(self.description))
        if pillows:
            for pillow_type in pillows:
             
                # Creates a pillow if the quantity is more than 0
                if pillows[pillow_type]:
                    Pillow.objects.create(product=self, type=pillow_type, quantity=pillows[pillow_type])
    
    def calculate_plywood_quantity(self):
        """
        Calculate the quantity of plywood boards used for this upholstery.
        
        Firstly calculates back then calculates the arms. Calculated by multiplying depth or width by height. 
        
        Rules:
        -Chaise, only half of side arm is calculates: (depth x height) / 2
        -No arms for ottomans or bumpers
        -20645 mm squared per board
        """  
        
        # Calculate surface area back
        surface_area = self.width * self.height
        
        # Calculate surface area of 1 arm
        if 'one-arm' in self.description.lower():
            
            # If Chaise lounge calculate half 
            if "chaise" in self.description:
                surface_area += (self.depth * self.height) / 2
                
            # Else calculate full arm
            else:
                surface_area += self.depth * self.height
        
        
        # Calculate surface area of dual arm
        elif "armless" not in self.description and "one-arm" not in self.description:
            
            surface_area += (self.depth * self.height) * 2
            
        # Raise error for unknown configuration
        else:
            raise ValueError('No calculation mechanism for {0}'.format(self.description))
            
        # Calculate front surface area:
        if 'ottoman' or 'bumper' in self.description:
            
            surface_area += self.width * self.height
            
        else:
            surface_area += (self.width * self.height) / 2
        
        # Calculate sheets of plywood based on 20645 mm squared per sheet
        quantity = math.ceil(surface_area / Decimal('20645'))
        
        # Update or create supply association    
        try:
            supply = Supply.objects.get(product=self, supply_id=2573)
        except Supply.DoesNotExist:
            supply = Supply(product=self, supply=S.objects.get(pk=2573), description='Plywood')
        
        supply.quantity = quantity
        supply.save()
        
        logger.info('{0}pcs of plywood used for {0}'.format(quantity, self.description))
        
        return supply.quantity
            
            
            
    def calculate_fiber_ball_quantity(self):
        """
        Calculate the quantity of fiber ball in kg need for this upholstery.
        Calculated based on these rules:
        
        -Back pillows = 2kg
        -Accent pillows = 0.7kg
        """
        total_qty = 0
        
        for pillow in self.pillows.all():
            
            if pillow.type == 'back':
                total_qty += pillow.quantity * Decimal('2')
            elif pillow.type == 'accent':
                total_qty += pillow.quantity * Decimal('0.7')
        
        try:
            supply = Supply.objects.get(product=self, supply_id=2584)
        except Supply.DoesNotExist:
            supply = Supply(product=self, supply=S.objects.get(pk=2584), description='fiber ball')
        
        supply.quantity = total_qty
        supply.save()
        
        logger.debug("{0:.2f}kg used for {1}".format(total_qty, self.description))
        return supply.quantity
        
    def calculate_webbing_quantity(self):
        """
        Calculate"""
        if self.width > self.height:
            width, depth = Decimal(str(self.width)), Decimal(str(self.depth))
        else:
            width, depth = Decimal(str(self.depth)), Decimal(str(self.width))
            
        # Caculate number of strands to use horizontally   
        number_of_width_strands = Decimal(str(math.ceil((width / Decimal('76')) / 2)))
        if number_of_width_strands > 2:
            number_of_width_strands -= 1
            
        # Calculate total length in mm of horizontal strands
        w_length = (number_of_width_strands) * depth
        
        # Caculate number of strands to use verticall   
        number_of_depth_strands = Decimal(str(math.ceil((depth / Decimal('76')) / 2)))
        if number_of_depth_strands > 2:
            number_of_depth_strands -= 1
                
        # Calculate total length in mm of veritcal strands
        d_length = (number_of_depth_strands) * width
        
        
        length = (w_length + d_length) / 1000
        
        logger.debug("Width: {0:.0f}mm | Depth: {1:.0f}mm".format(width, depth))
        logger.debug("Used {0} strands horizontally".format(number_of_width_strands))
        logger.debug('Used {0:.2f}mm horizontally'.format(w_length))
        logger.debug("Used {0} strands vertically".format(number_of_depth_strands))
        logger.debug('Used {0:.2f}mm veritically'.format(d_length))
        logger.debug("{0:.2f}m for {1}".format(length, self.description))
        
        print '\n'
        
        try:
            supply = Supply.objects.get(product=self, supply_id=4874)
        except Supply.DoesNotExist:
            supply = Supply(product=self, supply=S.objects.get(pk=4874), description='Webbing')
        
        supply.quantity = length
        supply.save()
        
        return supply.quantity
            
    def calculate_100g_fiber_padding_quantity(self):
        config = self.configuration.configuration.lower()
        
        if "sofa" in config:
            qty = 6
        elif "loveseat" in config:
            qty = 5
        elif "chair" in config:
            qty = 4
        elif "corner" in config:
            qty = 3
        elif "chaise" in config:
            qty = 3
        elif "ottoman" in config:
            qty = 1
        elif "bumper" in config:
            qty = 1
        elif "day bed" in config:
            qty = 3
        else:
            raise ValueError("configuration not found for {0}".format(self.description))
            
        if "armless" in config and 'chaise' not in config:
            qty -= 2
        elif "one-arm" in config and 'chaise' not in config:
            qty -= 1
        elif 'armless' in config and 'chaise' in config:
            qty -= 1
        
        try:
            supply = Supply.objects.get(product=self, supply_id=2509)
        except Supply.DoesNotExist:
            supply = Supply(product=self, supply=S.objects.get(pk=2509), description='fiber padding (100g)')
            
        supply.quantity = qty
        supply.save()
        
        return supply.quantity
        
    def calculate_200g_fiber_padding_quantity(self):
        config = self.configuration.configuration.lower()
        if "sofa" in config:
            qty = 3
        elif "loveseat" in config:
            qty = 2
        elif "chair" in config:
            qty = 1
        elif "corner" in config:
            qty = 1
        elif "chaise" in config:
            qty = 2
        elif "ottoman" in config:
            qty = 1
        elif "bumper" in config:
            qty = 1.25
        elif "day bed" in config:
            qty = 2
        else:
            raise ValueError("configuration not found for {0}".format(self.description))
            
        if "bumper" in config:
            qty += 0.5
        
        try:
            supply = Supply.objects.get(product=self, supply_id=2697)
        except Supply.DoesNotExist:
            supply = Supply(product=self, supply=S.objects.get(pk=2697), description='fiber padding (200g)')
            
        supply.quantity = qty
        supply.save()
        
        return supply.quantity
    
    def calculate_lumber_quantity(self):
        """
        Calculates the total quantity of lumber used to manufacture 
        this upholstery
        """
        base = []
        back = []
        arms = []
        
        # Calculate the base of the furniture. 
        # The short sides of the piece is calculated
        base.append(Lumber(width=4, length=self.depth, thickness=2, metric='length', quantity=4))
        base.append(Lumber(width=4, length=(self.height / 4) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
        logger.info("{0}: Lumber for short side of base: {1:.2f} BF\n".format(self.description, sum([l.board_feet for l in base])))
        
        # The long sides of the piece is caluclated
        base.append(Lumber(width=4, length=self.width - (4 * Decimal('0.3937') * 2), thickness=2, metric='length', quantity=4))
        base.append(Lumber(width=4, length=(self.height / 4) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
        logger.info("{0}: Lumber for long side of base: {1:.2f} BF\n".format(self.description, sum([l.board_feet for l in base[-3:-1]])))
        
        # Calculate the back
        # The short sides of the back is calculated
        back.append(Lumber(width=4, length=30, thickness=2, metric='length', quantity=4))
        back.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
        logger.info("{0}: Lumber for short side of back: {1:.2f} BF\n".format(self.description, sum([l.board_feet for l in back])))
        
        
        if "bumper" in self.description:
            # The long sides of the back is caluclated
            back.append(Lumber(width=4, length=self.width - (4 * Decimal('0.3937') * 2) - 50, thickness=2, metric='length', quantity=4))
            back.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
            logger.info("{0}: Lumber for long side of back: {1:.2f} BF\n".format(self.description, sum([l.board_feet for l in back[-3:-1]])))
        else:
            # The long sides of the back is caluclated
            back.append(Lumber(width=4, length=self.width - (4 * Decimal('0.3937') * 2), thickness=2, metric='length', quantity=4))
            back.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
            logger.info("{0}: Lumber for long side of back: {1:.2f} BF\n".format(self.description, sum([l.board_feet for l in back[-3:-1]])))   
            
        # Calculate the arms
        if 'armless' in self.description:
            pass
        
        elif 'one-arm' in self.description:
            # The short sides of the piece is calculated
            arms.append(Lumber(width=4, length=30, thickness=2, metric='length', quantity=2))
            arms.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=2))
        
            # The long sides of the piece is caluclated
            arms.append(Lumber(width=4, length=self.depth - (4 * Decimal('0.3937') * 2), thickness=2, metric='length', quantity=2))
            arms.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=2))
            
        else: 
            # The short sides of the piece is calculated
            arms.append(Lumber(width=4, length=30, thickness=2, metric='length', quantity=4))
            arms.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
        
            # The long sides of the piece is caluclated
            arms.append(Lumber(width=4, length=self.depth - (4 * Decimal('0.3937') * 2), thickness=2, metric='length', quantity=4))
            arms.append(Lumber(width=4, length=(self.height / 2) - (4 * Decimal('0.3937')), thickness=2, metric='length', quantity=4))
            
        bf_total = sum([float(lumber.board_feet) for lumber in (arms + back + base)])
        
        logger.info('Total board feet for {0}: {1:.2f} BF'.format(self.description, bf_total))
        
        # Retrieve the lumber supply for this upholstery and set the cost based
        # on total board feet of wood used. 
        try:
            supply = Supply.objects.get(product=self, description__icontains='lumber')
        except Supply.DoesNotExist:
            supply = Supply(product=self, description='lumber')
        supply.cost = bf_total * 37.5
        supply.save()
        
        return bf_total
            

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
    
