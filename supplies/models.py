from django.db import models
from contacts.models import Contact, Supplier
from decimal import Decimal
from django.contrib.auth.models import User

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
    
        
    #methods
    def get_parent_data(self, **kwargs):
        data = {
            'type':self.type,
            'supplier':self.supplier.get_data(),
            'width':str(self.width),
            'width_units':self.width_units,
            'depth_units':self.depth_units,
            'height_units':self.height_units,
            'depth':str(self.depth),
            'height':str(self.height),
            'description':self.description,
            'id':self.id,
            'cost':'%s' %self.cost,
            'reference':self.reference,
            'currency':self.currency
        }
        
        if self.image_url != None:
            
            data.update({"image":{"url":self.image_url, "key":self.image_key, "bucket":self.image_bucket}})
        
        return data
    
    def set_parent_data(self, data, **kwargs):
        if "reference" in data: self.reference = data["reference"]
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "width_units" in data: self.width_units = data['width_units']
        if "height" in data: self.height = data["height"]
        if "height_units" in data: self.height_units = data['height_units']
        if "depth" in data: self.depth = data["depth"]
        if "depth_units" in data: self.depth_units = data['depth_units']
        if "currency" in data: self.currency = data["currency"]
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]["id"])
        if "supplier_id" in data: self.supplier = Supplier.objects.get(id=data["supplier_id"])
        if "image" in data:
            if "url" in data["image"]: self.image_url = data["image"]["url"]
            if "key" in data["image"]: self.image_key = data["image"]["key"]
            if "bucket" in data["image"]: self.image_bucket = data["image"]["bucket"]
        
    def get_data(self, **kwargs):
        data = {
                'type':self.type,
                'supplier':self.supplier.get_data(),
                'width':str(self.width),
                'depth':str(self.depth),
                'height':str(self.height),
                'width_units':self.width_units,
                'depth_units':self.depth_units,
                'height_units':self.height_units,
                'description':self.description,
                'id':self.id,
                'cost':'%s' % self.cost,
                'currency':self.currency,
                'image_url':self.image_url,
                'image':{'url':self.image_url}
        }
        return data
        
    def set_data(self, data, **kwargs):
        #Set the supplier
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]["id"])
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "height" in data: self.height = data["height"]
        if "depth" in data: self.depth = data["depth"]
        if "image" in data:
            if "url" in data["image"]: self.image_url = data["image"]["url"]
            if "key" in data["image"]: self.image_key = data["image"]["key"]
            if "bucket" in data["image"]: self.image_bucket = data["image"]["bucket"]
"""This Location class is used to track and location and in the future
The access times of and movements of supplies, starting with fabrics"""
class Location(models.Model):
    
    description = models.TextField()
    row = models.CharField(max_length=10)
    shelf = models.CharField(max_length=10)
     
     

#Fabric Section
class Fabric(Supply):
    pattern = models.TextField()
    color = models.TextField()
    content = models.TextField()
    
    #Methods
    
    #Reserves fabric
    def reserve(self, length, employee=None, remark=None):
        
        log_item = FabricLog()
        log_item.employee = employee
        log_item.fabric = self
        log_item.action = "Reserve"
        log_item.length = length
        log_item.current_length = self.depth
        log_item.remarks = "Ack#: %s" % remark
        log_item.save()
    
    #Add Length
    def add(self, length, employee=None, remark=None):
        
        #Add to current Length
        self.depth = self.depth + Decimal(length)
        self.save()
        
        #Create log of addition
        log_item = FabricLog()
        log_item.employee = employee
        log_item.fabric = self
        log_item.action = "Add"
        log_item.length = length
        log_item.current_length = self.depth
        log_item.remarks = remark
        log_item.save()
    
    #Subtract Length
    def subtract(self, length, employee=None, remark=None):
        
        #check if length to subtract is more than total length
        if self.depth > Decimal(length):
            
            #Subtract from current length
            self.depth = self.depth - Decimal(length)
            self.save()
            
            #Destroy Reservation log
            try:
                old_log_item = FabricLog.objects.get(fabric_id=self.id, action='Reserve', remarks="Ack#: %s" % remark)
                old_log_item.delete()
            except:
                
                pass
            
            
            #Create log
            log_item = FabricLog()
            log_item.employee = employee
            log_item.fabric = self
            log_item.action = "Subtract"
            log_item.length = length
            log_item.current_length = self.depth
            log_item.remarks = "Ack#: %s" % remark
            log_item.save()
            
    def reset(self, length, employee=None, remark=None):
        
        self.depth = length
        self.save()
        
        #Create log
        log_item = FabricLog()
        log_item.employee = employee
        log_item.fabric = self
        log_item.action = "Reset"
        log_item.length = length
        log_item.current_length = self.depth
        log_item.remarks = remark
        log_item.save()
        
    #Set fabric data for REST
    def set_data(self, data, **kwargs):
        #extract args
        if "user" in kwargs: user = kwargs["user"]
        #set parent data
        super(Fabric, self).set_data(data, user=user)
        #set the type to fabric
        self.type = "Fabric"
        #set purchasing units
        self.purchasing_units = "yard"
        #set the model data
        if "pattern" in data: self.pattern = data["pattern"]
        if "color" in data: self.color = data["color"]
        if "content" in data: self.content = data["content"]
        self.description = "%s Col:%s" % (self.pattern, self.color)
        
        #Set the current length of fabric
        if "current_length" in data: self.reset(data["current_length"], user, "Initial Current Length")
        
        self.save()
    
    #Get Data for REST
    def get_data(self, **kwargs):
        
        from django.db.models import Sum
        #Get the Reserve Length
        sum_obj = FabricLog.objects.filter(action="Reserve", fabric_id=self.id).aggregate(Sum('length'))
        
        #sets the data for this supply
        data = {
                'pattern':self.pattern,
                'color':self.color,
                'content':self.content,
                'reserved_length':str(sum_obj["length__sum"])
        }
        #merges with parent data
        data.update(super(Fabric, self).get_data())
        #returns the data
        return data


#Fabric Log

class FabricLog(models.Model):
    fabric = models.ForeignKey(Fabric)
    action = models.CharField(max_length=15, null=False)
    length = models.DecimalField(max_digits=15, decimal_places=2)
    current_length = models.DecimalField(max_digits=15, decimal_places=2)
    remarks = models.TextField()
    employee = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)



#Foam

class Foam(Supply):
    foamType = models.TextField(db_column="foam_type")
    color = models.CharField(max_length=20)
    
    #methods 
    
    #get data
    def get_data(self, **kwargs):
        #get data for foam
        data = {
                'color':self.color,
                'type':self.foamType
                }
        
        #merge with data from parent
        data.update(super(Foam, self).get_data())
        
        #return the data
        return data
    
    #set data
    def set_data(self,data, **kwargs):
        #extract data
        if "user" in kwargs: user = kwargs["user"]
        #set the parent data
        super(Foam, self).set_data(data, user=user)
        #set foam data
        self.purchasing_units = "pc"
        
        self.type = "foam"
        if "type" in data: self.foamType = data["type"]
        if "color" in data: self.color = data["color"]
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

        
