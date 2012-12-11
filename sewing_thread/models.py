from django.db import models
from supplies.models import Supply
# Create your models here.

class SewingThread(Supply):
    
    color = models.TextField()
    
    #methods
    def get_data(self):
        
        data = {'color':self.color}
        #merge with parent data
        data.update(self.get_parent_data())
        return data
    
    def set_data(self, data):
        
        self.set_parent_data(data)
        self.type = "sewing thread"
        if "color" in data: self.color = data["color"]
        self.description = "%s Sewing Thread" %self.color