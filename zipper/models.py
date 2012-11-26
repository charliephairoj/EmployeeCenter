from django.db import models
from supplies.models import Supply

# Create your models here.


class Zipper(Supply):
    
    
    
    #methods
    
    #get data
    def getData(self):
        
        data = {
                
                
                
                
                }
        
        
        return data
    
    
    #set data
    def setData(self, data):
        
        #set the parent data
        self.setParentData(data)
        
        #save model
        self.save()
        
        
        
        
        
        