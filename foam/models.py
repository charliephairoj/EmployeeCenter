from supplies.models import Supply
from django.db import models
import logging

logger = logging.getLogger('EmployeeCenter');


class Foam(Supply):
    foamType = models.TextField(db_column="foam_type")
    color = models.CharField(max_length=20)
    
    #methods 
    
    #get data
    def getData(self):
        #get data for foam
        data = {
                'color':self.color,
                'type':self.foamType
                }
        
        #merge with data from parent
        data.update(self.getParentData())
        
        #return the data
        return data
    
    #set data
    def setData(self,data):
        
        #set the parent data
        self.setParentData(data)
        
        #set foam data
        self.type = "foam"
        if "type" in data: self.foamType = data["type"]
        if "color" in data: self.color = data["color"]
        self.description = "%s %s Foam (%sX%sX%s)" & (self.color, self.type, self.width, self.depth, self.height)
        
        #save the foam
        self.save()