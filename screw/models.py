from django.db import models
from supplies.models import Supply


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
        
        
        
        