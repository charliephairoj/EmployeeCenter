import os
import time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django_hstore import hstore
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from contacts.models import Contact, Supplier
from auth.models import Log

# Create your models here.

#Creates the main supplies class
class Supply(models.Model):
    supplier = models.ForeignKey(Supplier)
    description = models.TextField(null=True)
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
    currency = models.CharField(max_length=10, default="THB")
    image_url = models.TextField(null=True)
    image_bucket = models.TextField(null=True)
    image_key = models.TextField(null=True)
    quantity = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    quantity_units = models.TextField(default="mm")
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    #data = hstore.DictionaryField()
    #objects = hstore.HStoreManager()

    class Meta:
        permissions = (('view_supplier', 'Can view the Supplier'),
                       ('view_props', 'Can view props'))

    def get_data(self, **kwargs):
        data = {
                'quantity': str(self.quantity),
                'reference': self.reference,
                'type': self.type,
                'supplier': self.supplier.get_data(),
                'width': str(self.width),
                'depth': str(self.depth),
                'height': str(self.height),
                'width_units': self.width_units,
                'depth_units': self.depth_units,
                'height_units': self.height_units,
                'description': self.description,
                'id': self.id,
                'cost': '%s' % self.cost,
                'currency': self.currency,
                'image_url': self.image_url,
                'image': {'url': self.image_url}
        }

        try:
            user = kwargs["user"]
            if user.has_perm('supplies.view_supplier'):
                data.update({'supplier': self.supplier.get_date()})
        except:
            pass
        return data

    def set_data(self, data, **kwargs):
        if "reference" in data:
            self.reference = data["reference"]
            del data["reference"]
        if "supplier" in data:
            self.supplier = Supplier.objects.get(id=data["supplier"]["id"])
            del data["supplier"]
        if "type" in data:
            self.type = data["type"]
            del data["type"]
        if "cost" in data:
            self.cost = Decimal(data["cost"])
            del data["cost"]
        if "width" in data:
            self.width = data['width']
            del data["width"]
        if "height" in data:
            self.height = data["height"]
            del data["height"]
        if "depth" in data:
            self.depth = data["depth"]
            del data["depth"]
        if "height_units" in data:
            self.height_units = data["height_units"]
            del data["height_units"]
        if "width_units" in data:
            self.width_units = data["width_units"]
            del data["width_units"]
        if "depth_units" in data:
            self.depth_units = data["depth_units"]
            del data["depth_units"]
        if "image" in data:
            if "url" in data["image"]:
                self.image_url = data["image"]["url"]
            if "key" in data["image"]:
                self.image_key = data["image"]["key"]
            if "bucket" in data["image"]:
                self.image_bucket = data["image"]["bucket"]
            del data["image"]

    
    def reserve(self, quantity, employee, remarks=None, acknowledgement_id=None):
        message = "Reserve {0} {1}".format(quantity, self.quantity_units)
        if acknowledgement_id:
            message += " for Acknowledgement# {0}".format(acknowledgement_id)
            try:
                log = SupplyLog.objects.get(acknowledgement_id=acknowledgement_id, event__icontains='Reserve')
                log.event = message
                log.save()
            except:
                SupplyLog.create(event=message, employee=employee, quantity=self.quantity,
                                 supply=self, acknowledgement_id=acknowledgement_id)
        else:
            SupplyLog.create(event=message, employee=employee, quantity=self.quantity,
                             supply=self, acknowledgement_id=acknowledgement_id)

    def add(self, quantity, employee=None, remarks=None):
        self.quantity = self.quantity + Decimal(quantity)
        self.save()
        message = "Added {0} to {1}. {2} remaining".format(quantity, self.description, self.quantity)
        SupplyLog.create(event=message, employee=employee, quantity=self.quantity, supply=self)

    def subtract(self, quantity, employee=None, remarks=None, acknowledgement_id=None):
        #check if length to subtract is more than total length
        if self.quantity > Decimal(quantity):
            #Subtract from current length
            self.quantity = self.quantity - Decimal(quantity)
            self.save()

            message = "Subtract {0} from {1}. {2} remaining".format(quantity, self.description, self.quantity)
            print acknowledgement_id
            if acknowledgement_id:
                try:
                    SupplyLog.objects.get(acknowledgement_id=acknowledgement_id, event__icontains='Reserve').delete()
                except:
                    pass
                message = "Acknowledgement# {0}".format(acknowledgement_id) + message

            SupplyLog.create(event=message, employee=employee, quantity=self.quantity,
                             supply=self, acknowledgement_id=acknowledgement_id)
        else:
            raise Exception("Nothing left to subtract")

    def reset(self, quantity, employee=None, remarks=None):
        self.quantity = quantity
        self.save()

        message = "Reset {0} to {1}".format(self.description, quantity)
        SupplyLog.create(event=message, employee=employee, quantity=self.quantity, supply=self)

    def upload_image(self, image, key="supplies/images/{0}.jpg".format(time.time())):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = "supplies/images/{0}.jpg".format(time.time())
        #upload file
        k.set_contents_from_filename(image)
        #set the Acl
        k.set_canned_acl('public-read')
        k.make_public()
        #set Url, key and bucket
        data = {
                'url': 'http://media.dellarobbiathailand.com.s3.amazonaws.com/'+k.key,
                'key': k.key,
                'bucket': 'media.dellarobbiathailand.com'
        }
        return data


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

    
    #Set fabric data for REST
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs:
            user = kwargs["user"]
        #set parent data
        super(Fabric, self).set_data(data, user=user)
        #set the type to fabric
        self.type = "fabric"
        #set purchasing units
        self.purchasing_units = "yard"
        #set the model data
        if "pattern" in data:
            self.pattern = data["pattern"]
        if "color" in data:
            self.color = data["color"]
        if "content" in data:
            self.content = data["content"]
        self.description = "%s Col:%s" % (self.pattern, self.color)
       
        self.save()

    #Get Data for REST
    def get_data(self, **kwargs):

        #sets the data for this supply
        data = {
                'pattern': self.pattern,
                'color': self.color,
                'content': self.content,
        }
        #merges with parent data
        data.update(super(Fabric, self).get_data())
        #returns the data
        return data


class Foam(Supply):

    foam_type = models.TextField(db_column="foam_type")
    color = models.CharField(max_length=20)

    def get_data(self, **kwargs):
        #get data for foam
        data = {
                'color': self.color,
                'type': self.foam_type
                }

        #merge with data from parent
        data.update(super(Foam, self).get_data())

        #return the data
        return data

    #set data
    def set_data(self, data, **kwargs):
        #extract data
        if "user" in kwargs:
            user = kwargs["user"]
        #set the parent data
        super(Foam, self).set_data(data, user=user)
        #set foam data
        self.purchasing_units = "pc"

        self.type = "foam"
        if "type" in data:
            self.foam_type = data["type"]
        if "color" in data:
            self.color = data["color"]
        self.description = "%s Foam (%sX%sX%s)" % (self.color, self.width, self.depth, self.height)

        #save the foam
        self.save()

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

        
