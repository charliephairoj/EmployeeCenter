from django.db import models
from supplies.models import Supply


class Screw(Supply):
    
    
    boxQuantity = models.IntegerField(db_column='box_quantity')

    
    
    #method 
    
    #get data
    def getData(self):
        
        
        #get data
        data = {
                'boxQuantity':self.boxQuantity
                }
        #merge with parent data
        data.update(self.getParentData())
        #return the data
        return data
    
    #set data
    def setData(self, data):
        
        #set the parent data
        self.setParentData(data)
        
        #set screw data
        if "boxQuantity" in data: self.boxQuantity = data['boxQuantity']
        
        
        
        