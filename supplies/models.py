import os
import time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django_hstore import hstore
from django.shortcuts import get_object_or_404

from contacts.models import Contact, Supplier
from auth.models import Log, S3Object


#Creates the main supplies class
class Supply(models.Model):
    supplier = models.ForeignKey(Supplier)
    description = models.TextField(null=True)
    description_th = models.TextField(null=True)
    type = models.CharField(max_length=20, null=True)
    cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    width = models.DecimalField(db_column='width', decimal_places=2, max_digits=12, default=0)
    width_units = models.CharField(max_length=4, default="mm")
    depth = models.DecimalField(db_column='depth', decimal_places=2, max_digits=12, default=0)
    depth_units = models.CharField(max_length=4, default="mm")
    height = models.DecimalField(db_column='height', decimal_places=2, max_digits=12, default=0)
    height_units = models.CharField(max_length=4, default="mm")
    units = models.CharField(max_length=20, default='mm')
    purchasing_units = models.CharField(max_length=10, default="pc")
    discount = models.IntegerField(default=0)
    reference = models.TextField()
    notes = models.TextField(null=True)
    quantity = models.FloatField(default=0)
    quantity_units = models.TextField(default="mm")
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    image = models.ForeignKey(S3Object, null=True)
    deleted = models.BooleanField(default=False)
    admin_only = models.BooleanField(default=False)

    class Meta:
        permissions = (('view_supplier', 'Can view the Supplier'),
                       ('view_cost', 'Can view the cost per unit'),
                       ('view_props', 'Can view props'))

    @classmethod
    def create(cls, user=None, commit=True, **kwargs):
        """
        Creates and returns a new supply
        """
        supply = cls()
        if "width" in kwargs:
            supply.width = kwargs["width"]
        if "depth" in kwargs:
            supply.depth = kwargs["depth"]
        if "height" in kwargs:
            supply.height = kwargs["height"]

        if "reference" in kwargs:
            supply.reference = kwargs["reference"]
      
        try:
            supply.quantity = Decimal(str(kwargs["quantity"]))
        except KeyError:
            supply.quantity = 0

        try:
            supply.cost = kwargs["cost"]
        except KeyError:
            try:
                supply.cost = kwargs["unit_cost"]
            except:
                raise AttributeError("Missing supply's cost.")

        try:
            supply.supplier = Supplier.objects.get(pk=kwargs["supplier"]["id"])
        except KeyError:
            raise AttributeError("Missing supplier")
        except Supplier.DoesNotExist:
            raise AttributeError("Supplier not found.")

        if "description" in kwargs:
            try:
                supply.description = kwargs["description"]["en"]
                if "th" in kwargs["description"]:
                    supply.description_th = kwargs["description"]["th"]
            except (KeyError, TypeError):
                supply.description = kwargs["description"]

        if "image" in kwargs:
                try:
                    supply.image = S3Object.objects.get(pk=kwargs["image"]["id"])
                except KeyError:
                    raise IntegrityError("Missing image's ID")
                except S3Object.DoesNotExist:
                    raise TypeError("Image does not exist")

        if "width_units" in kwargs:
            supply.width_units = kwargs["width_units"]
        if "depth_units" in kwargs:
            supply.depth_units = kwargs["depth_units"]
        if "height_units" in kwargs:
            supply.height_units = kwargs["height_units"]
        if "quantity_units" in kwargs:
            supply.quantity_units = kwargs["quantity_units"]
        if "units" in kwargs:
            supply.purchasing_units = kwargs["units"]
        elif "purchasing_units" in kwargs:
            supply.purchasing_units = kwargs["purchasing_units"]
            
        if "notes" in kwargs:
            supply.notes = kwargs["notes"]

        if commit:
            supply.save()

        return supply

    


class Location(models.Model):
    """This Location class is used to track and location and in the future
    The access times of and movements of supplies, starting with fabrics
    """
    description = models.TextField()
    row = models.CharField(max_length=10)
    shelf = models.CharField(max_length=10)


class SupplyLog(Log):
    """The general log class for supplies will keep track of actions,
    such as adding, subtracting, resetting items from the inventory
    count.

    quantity = the quantity associate with the action
    current_quantity = the quantity remaining after the action
    """
    supply = models.ForeignKey(Supply)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    acknowledgement_id = models.TextField(null=True)
    remarks = models.TextField(null=True)

    @classmethod
    def create(cls, supply, event, quantity, employee, acknowledgement_id=None):
        supplyObj = cls()
        supplyObj.quantity = quantity
        supplyObj.supply = supply
        supplyObj.employee = employee
        supplyObj.event = event
        supplyObj.acknowledgement_id = acknowledgement_id
        supplyObj.save()


class Fabric(Supply):
    pattern = models.TextField()
    color = models.TextField()
    content = models.TextField()

    @classmethod
    def create(cls, **kwargs):
        """
        Creates a new fabric object and returns it
        """
        obj = super(Fabric, cls).create(commit=False, **kwargs)
        try:
            obj.pattern = kwargs["pattern"]
        except KeyError:
            raise AttributeError("Missing fabric pattern.")
        try:
            obj.color = kwargs["color"]
        except KeyError:
            raise AttributeError("Missing fabric color")
        
        obj.description = "Pattern: {0}, Col: {1}".format(obj.pattern, obj.color)
        obj.units = 'm'
        obj.purchasing_units = 'm'

        obj.save()
        return obj
    

class Foam(Supply):

    foam_type = models.TextField(db_column="foam_type")
    color = models.CharField(max_length=20)

    @classmethod
    def create(cls, user=None, **kwargs):
        """
        Creates a new foam object and returns it
        """
        obj = super(Fabric, cls).create(commit=False, **kwargs)
        try:
            obj.foam_type = kwargs["type"]
        except KeyError:
            try:
                obj.foam_type = kwargs["foam_type"]
            except KeyError:
                raise AttributeError("Missing fabric pattern.")
        try:
            obj.color = kwargs["color"]
        except KeyError:
            raise AttributeError("Missing fabric color")

        obj.purchasing_units = "pc"

        obj.save()
        return obj

    def update(self, user=None, **kwargs):
        """
        Updates the foam
        """
        super(Foam, self).update(user=user, **kwargs)
        #set foam data
        self.purchasing_units = "pc"

        self.type = "foam"
        if "type" in kwargs:
            self.foam_type = kwargs["type"]
        if "color" in kwargs:
            self.color = kwargs["color"]
        self.description = "%s Foam (%sX%sX%s)" % (self.color, self.width, self.depth, self.height)

        self.save()

    def to_dict(self, **kwargs):
        """
        Returns foam attributes as a dictionary
        """
        data = {'color': self.color,
                'type': self.foam_type}

        data.update(super(Foam, self).to_dict())

        return data


class Glue(Supply):

    def set_data(self, data, **kwargs):
        self.type = "glue"
        super(Glue, self).set_data(data, **kwargs)

#Lumber section

class Lumber(Supply):
    wood_type = models.TextField(db_column  = "wood_type")

    #Methods
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set parent data
        super(Lumber, self).set_data(data, user=user)
        #set the type to lumber
        self.type = "lumber"
        #set the wood type
        if "type" in data:self.wood_type = data["type"]


        self.set_parent_data(data)
        #set parent properties
        if "width_units" in data: self.width_units = data["width_units"]
        if "depth_units" in data: self.depth_units = data["depth_units"]
        if "height_units" in data: self.height_units = data["height_units"]
        self.purchasing_units = "pc"
        #set the description
        if "description" in data: 
            self.description = data["description"]
        else:
            self.description = "%s %s%sx%s%sx%s%s" % (self.wood_type, self.width, self.width_units, self.depth, self.depth_units, self.height, self.height_units)
            
        #set the supplier
        if "supplier_id" in data: self.supplier = Supplier.objects.get(id = data["supplier_id"])
        
        self.save()
        
    def get_data(self, **kwargs):
        
        #sets the data for this supply
        data = {
                'type':self.wood_type,
        }
        #merges with parent data
        data.update(super(Lumber, self).get_data())
       
        #returns the data
        return data


#screw
class Screw(Supply):
    
    
    box_quantity = models.IntegerField(db_column='box_quantity')

    
    
    #method 
    
    #get data
    def get_data(self, **kwargs):
        
        
        #get data
        data = {
                'boxQuantity':self.box_quantity
                }
        #merge with parent data
        data.update(super(Screw, self).get_data())
        #return the data
        return data
    
    #set data
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set the parent data
        super(Screw, self).set_data(data, user=user)
        #set screw data
        self.purchasing_units = "box"
        self.type = "screw"
        
        if "boxQuantity" in data: self.box_quantity = data['boxQuantity']
        #description
        self.description = "%sx%s Screw" % (self.width, self.height)
        
        

#Sewing Thread
class SewingThread(Supply):
    
    color = models.TextField()
    
    #methods
    def get_data(self, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        data = {'color':self.color}
        #merge with parent data
        data.update(super(SewingThread, self).get_data())
        return data
    
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        super(SewingThread, self).set_data(SewingThread, user=user)
        
        self.purchasing_units = "spool"
        self.type = "sewing thread"
        if "color" in data: self.color = data["color"]
        self.description = "%s Sewing Thread" %self.color
        
        
#staples

class Staple(Supply):
    
    box_quantity = models.IntegerField()
    
    #methods
    
    def get_data(self, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        data = {'boxQuantity':self.box_quantity}
        #merge with parent data
        data.update(super(Staple, self).get_data())
        return data
    
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set parent data
        super(Staple, self).set_data(data, self)
        
        if "boxQuantity" in data: self.box_quantity = data['boxQuantity']
        self.purchasing_units = "box"
        self.type = "staple"
        #set description
        self.description = "%sx%s Staple" % (self.width, self.height)
        

#Webbings

class Webbing(Supply):
    
    #methods
    
    #get pdata
    def get_data(self, **kwargs):
        data = {}
        
        data.update(super(Webbing, self).get_data())
        
    #set data
    
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set parent data
        super(Webbing, self).set_data(data, user=user)
        
        self.purchasing_units = "roll"
        self.type = "webbing"
        

#wool
class Wool(Supply):
    tex = models.IntegerField()
    
    #methods
    
    #get data
    def get_data(self, **kwargs):
        #get's this supply's data
        data = {
            'tex':self.tex,
        }
        
        #merges with parent data
        data.update(super(Wool, self).get_data())
        #return the data
        return data
    
    #set data
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set parent data
        super(Wool, self).set_data(data, user=user)
        #set wool specific data
        self.purchasing_units = "kg"
        
        self.width = 0
        self.height = 0
        self.depth = 0
        self.units = 'kg'
        self.type = 'wool'
        if "tex" in data: self.tex = data['tex']
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]['id'])
        if "description" in data:
            self.description = data['description']
        else:
            self.description = "%s Tex" % self.tex
        
        self.save()
        
        
#Zipper
class Zipper(Supply):
    
    
    
    #methods
    
    #get data
    def get_data(self, **kwargs):
        
        data = {
                
                
                
                
                }
        
        data.update(super(Zipper, self).get_data())
        
        return data
    
    
    #set data
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set the parent data
        super(Zipper, self).set_data(data, user=user)
        
        self.purchasing_units = "roll"
        self.type = "zipper"
        #set the description
        self.description = "%s%sx%s%s Zipper" %(self.width, self.width_units, self.depth, self.depth_units)
        
        #save model
        self.save()    

        
