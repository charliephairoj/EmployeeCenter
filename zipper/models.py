from django.db import models
from supplies.models import Supply

# Create your models here.


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
        
        
        
        
        
        