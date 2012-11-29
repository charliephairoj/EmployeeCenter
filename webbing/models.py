from django.db import models
from supplies.models import Supply
# Create your models here.



class Webbing(Supply):
    
    #methods
    
    #get pdata
    def getData(self):
        data = {}
        
        data.update(self.getParentData())
        
    #set data
    
    def setData(self, data):
        
        #set parent data
        self.setParentData(data)
