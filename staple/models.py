from django.db import models
from supplies.models import Supply
# Create your models here.

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
        
        