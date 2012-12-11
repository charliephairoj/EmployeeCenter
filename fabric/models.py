from supplies.models import Supply
from contacts.models import Supplier
from django.db import models


# Create your models here.
#Creates the lumber class
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
    