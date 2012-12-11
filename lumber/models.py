from supplies.models import Supply
from contacts.models import Supplier
from django.db import models

# Create your models here.
#Creates the lumber class
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
    