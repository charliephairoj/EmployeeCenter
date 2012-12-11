from django.db import models
from supplies.models import Supply
from contacts.models import Supplier

# Create your models here.



class Wool(Supply):
    tex = models.IntegerField()
    
    #methods
    
    #get data
    def get_data(self):
        #get's this supply's data
        data = {
            'tex':self.tex,
        }
        
        #merges with parent data
        data.update(self.get_parent_data())
        #return the data
        return data
    
    #set data
    def set_data(self, data):
        
        #set parent data
        self.set_parent_data(data)
        #set wool specific data
        self.width = 0
        self.height = 0
        self.depth = 0
        self.units = 'kg'
        self.type = 'wool'
        if "tex" in data: self.tex = data['tex']
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]['id'])
        if "description" in data:
            self.description = data['description']
        else:
            self.description = "%s Tex" % self.tex
        
        self.save()