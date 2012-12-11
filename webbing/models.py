from django.db import models
from supplies.models import Supply
# Create your models here.



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