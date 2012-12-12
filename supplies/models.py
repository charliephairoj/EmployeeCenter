from django.db import models
from contacts.models import Contact, Supplier
from decimal import Decimal


# Create your models here.

#Creates the main supplies class
class Supply(models.Model):
    supplier = models.ForeignKey(Supplier)
    description = models.TextField(null=True)
    type = models.CharField(max_length=20, null=True)
    cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    width = models.IntegerField(db_column='width', default=0)
    width_units = models.CharField(max_length=4, default="mm")
    depth = models.IntegerField(db_column='depth', default=0)
    depth_units = models.CharField(max_length=4, default="mm")
    height = models.IntegerField(db_column='height', default=0)
    height_units = models.CharField(max_length=4, default="mm")
    units = models.CharField(max_length=20, default='mm')
    discount = models.IntegerField(default=0)
    reference = models.TextField()
    currency = models.CharField(max_length=10, default="THB")
    
        
    #methods
    def get_parent_data(self):
        data = {
            #'type':self.type,
            'supplier':self.supplier.get_data(),
            'width':self.width,
            'widthUnits':self.width_units,
            'depthUnits':self.depth_units,
            'heightUnits':self.height_units,
            'depth':self.depth,
            'height':self.height,
            'description':self.description,
            'id':self.id,
            'cost':'%s' %self.cost,
            'reference':self.reference,
            'currency':self.currency
        }
        
        return data
    
    def set_parent_data(self, data):
        if "reference" in data: self.reference = data["reference"]
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "widthUnits" in data: self.width_units = data['widthUnits']
        if "height" in data: self.height = data["height"]
        if "heightUnits" in data: self.height_units = data['heightUnits']
        if "depth" in data: self.depth = data["depth"]
        if "depthUnits" in data: self.depth_units = data['depthUnits']
        if "currency" in data: self.currency = data["currency"]
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]["id"])
        if "supplierID" in data: self.supplier = Supplier.objects.get(id=data["supplierID"])
        
    def get_data(self):
        data = {
                'type':self.type,
                'supplier':self.supplier.get_data(),
                'width':self.width,
                'depth':self.depth,
                'height':self.height,
                'widthUnits':self.width_units,
                'depthUnits':self.depth_units,
                'heightUnits':self.height_units,
                'description':self.description,
                'id':self.id,
                'cost':'%s' % self.cost,
                'currency':self.currency
        }
        
        return data
        
    def set_data(self, data):
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "height" in data: self.height = data["height"]
        if "depth" in data: self.depth = data["depth"]
     
     

#Fabric Section
class Fabric(Supply):
    pattern = models.TextField()
    color = models.TextField()
    
    #Methods
    def set_data(self, data):
        #set the type to lumber
        self.type = "fabric"
        
       
        #set parent properties
        self.set_parent_data(data)
        
        #set the model data
        if "pattern" in data: self.pattern = data["pattern"]
        if "color" in data: self.color = data["color"]
        
        if "description" in data: 
            self.description = data["description"]
        else:
            self.description = "%s %s" % (self.pattern, self.color)
        #set the supplier
        if "supplierID" in data: self.supplier = Supplier.objects.get(id = data["supplierID"])
        
        self.save()
        
    def get_data(self):
        
        #sets the data for this supply
        data = {
                'pattern':self.pattern,
                'color':self.color
        }
        #merges with parent data
        data.update(self.get_parent_data())
        
        #returns the data
        return data


#Foam

class Foam(Supply):
    foamType = models.TextField(db_column="foam_type")
    color = models.CharField(max_length=20)
    
    #methods 
    
    #get data
    def get_data(self):
        #get data for foam
        data = {
                'color':self.color,
                'type':self.foamType
                }
        
        #merge with data from parent
        data.update(self.get_parent_data())
        
        #return the data
        return data
    
    #set data
    def set_data(self,data):
        
        #set the parent data
        self.set_parent_data(data)
        
        #set foam data
        self.type = "foam"
        if "type" in data: self.foamType = data["type"]
        if "color" in data: self.color = data["color"]
        self.description = "%s %s Foam (%sX%sX%s)" % (self.color, self.type, self.width, self.depth, self.height)
        
        #save the foam
        self.save()   
        
        
#Lumber section

class Lumber(Supply):
    wood_type = models.TextField(db_column  = "wood_type")
    
    #Methods
    def set_data(self, data):
        #set the type to lumber
        self.type = "lumber"
        #set the wood type
        if "type" in data:self.wood_type = data["type"]
       
        #set parent properties
        self.set_parent_data(data)
        if "widthUnits" in data: self.width_units = data["widthUnits"]
        if "depthUnits" in data: self.depth_units = data["depthUnits"]
        if "heightUnits" in data: self.height_units = data["heightUnits"]
        #set the description
        if "description" in data: 
            self.description = data["description"]
        else:
            self.description = "%s %s%sx%s%sx%s%s" % (self.wood_type, self.width, self.width_units, self.depth, self.depth_units, self.height, self.height_units)
            
        #set the supplier
        if "supplierID" in data: self.supplier = Supplier.objects.get(id = data["supplierID"])
        
        self.save()
        
    def get_data(self):
        
        #sets the data for this supply
        data = {
                'type':self.wood_type,
        }
        #merges with parent data
        data.update(self.get_parent_data())
       
        #returns the data
        return data


#screw
class Screw(Supply):
    
    
    box_quantity = models.IntegerField(db_column='box_quantity')

    
    
    #method 
    
    #get data
    def get_data(self):
        
        
        #get data
        data = {
                'boxQuantity':self.box_quantity
                }
        #merge with parent data
        data.update(self.get_parent_data())
        #return the data
        return data
    
    #set data
    def set_data(self, data):
        
        #set the parent data
        self.set_parent_data(data)
        self.type = "screw"
        #set screw data
        if "boxQuantity" in data: self.box_quantity = data['boxQuantity']
        #description
        self.description = "%sx%s Screw" % (self.width, self.height)
        
        

#Sewing Thread
class SewingThread(Supply):
    
    color = models.TextField()
    
    #methods
    def get_data(self):
        
        data = {'color':self.color}
        #merge with parent data
        data.update(self.get_parent_data())
        return data
    
    def set_data(self, data):
        
        self.set_parent_data(data)
        self.type = "sewing thread"
        if "color" in data: self.color = data["color"]
        self.description = "%s Sewing Thread" %self.color
        
        
#staples

class Staple(Supply):
    
    box_quantity = models.IntegerField()
    
    #methods
    
    def get_data(self):
        
        data = {'boxQuantity':self.box_quantity}
        #merge with parent data
        data.update(self.get_parent_data())
        return data
    
    def set_data(self, data):
        
        if "boxQuantity" in data: self.box_quantity = data['boxQuantity']
        self.set_parent_data(data)
        self.type = "staple"
        #set description
        self.description = "%sx%s Staple" % (self.width, self.height)
        

#Webbings

class Webbing(Supply):
    
    #methods
    
    #get pdata
    def get_data(self):
        data = {}
        
        data.update(self.get_parent_data())
        
    #set data
    
    def set_data(self, data):
        
        #set parent data
        self.set_parent_data(data)
        self.type = "webbing"
        

#wool
class Wool(Supply):
    tex = models.IntegerField()
    
    #methods
    
    #get data
    def get_data(self):
        #get's this supply's data
        data = {
            'tex':self.tex,
        }
        
        #merges with parent data
        data.update(self.get_parent_data())
        #return the data
        return data
    
    #set data
    def set_data(self, data):
        
        #set parent data
        self.set_parent_data(data)
        #set wool specific data
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
    def get_data(self):
        
        data = {
                
                
                
                
                }
        
        data.update(self.get_parent_data())
        
        return data
    
    
    #set data
    def set_data(self, data):
        
        #set the parent data
        self.set_parent_data(data)
        self.type = "zipper"
        #set the description
        self.description = "%s%sx%s%s Zipper" %(self.width, self.width_units, self.depth, self.depth_units)
        
        #save model
        self.save()    

        
