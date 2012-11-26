from supplies.models import Supply
from contacts.models import Supplier
from django.db import models
import json
import logging

logger = logging.getLogger('EmployeeCenter');


# Create your models here.
#Creates the lumber class
class Fabric(Supply):
    pattern = models.TextField()
    color = models.TextField()
    
    #Methods
    def setData(self, data):
        #set the type to lumber
        self.type = "fabric"
        
       
        #set parent properties
        self.setParentData(data)
        
        #set the model data
        if "pattern" in data: self.pattern = data["pattern"]
        if "color" in data: self.color = data["color"]
        
        #set the supplier
        if "supplierID" in data: self.supplier = Supplier.objects.get(id = data["supplierID"])
        
        self.save()
        
    def getData(self):
        
        #sets the data for this supply
        data = {
                'pattern':self.pattern,
                'color':self.color
        }
        #merges with parent data
        data.update(self.getParentData())
        
        #returns the data
        return data
    