from supplies.models import Supply
from contacts.models import Supplier
from django.db import models
import json
import logging

logger = logging.getLogger('EmployeeCenter');


# Create your models here.
#Creates the lumber class
class Lumber(Supply):
    woodType = models.TextField(db_column  = "wood_type")
    
    #Methods
    def setData(self, data):
        #set the type to lumber
        self.type = "lumber"
        #set the wood type
        if "type" in data:self.woodType = data["type"]
       
        #set parent properties
        self.setParentData(data)
        #set the description
        if "description" in data: 
            self.description = data["description"]
        else:
            self.description = self.woodType+' '+self.width+'x'+self.depth+'x'+self.height

        #set the supplier
        if "supplierID" in data: self.supplier = Supplier.objects.get(id = data["supplierID"])
        
        self.save()
        
    def getData(self):
        
        #sets the data for this supply
        data = {
                'type':self.woodType,
        }
        #merges with parent data
        data.update(self.getParentData())
        logger.debug(self.getParentData())
        logger.debug(data)
        #returns the data
        return data
    