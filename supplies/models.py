from django.db import models
from contacts.models import Contact, Supplier
from decimal import Decimal


# Create your models here.

#Creates the main supplies class
class Supply(models.Model):
    supplier = models.ForeignKey(Supplier)
    description = models.TextField(null=True)
    type = models.CharField(max_length=20, null=True)
    cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    width = models.IntegerField(db_column='width', default=0)
    width_units = models.CharField(max_length=4, default="mm")
    depth = models.IntegerField(db_column='depth', default=0)
    depth_units = models.CharField(max_length=4, default="mm")
    height = models.IntegerField(db_column='height', default=0)
    height_units = models.CharField(max_length=4, default="mm")
    units = models.CharField(max_length=20, default='mm')
    discount = models.IntegerField(default=0)
    reference = models.TextField()
    currency = models.CharField(max_length=10, default="THB")
    
        
    #methods
    def get_parent_data(self):
        data = {
            #'type':self.type,
            'supplier':self.supplier.get_data(),
            'width':self.width,
            'widthUnits':self.width_units,
            'depthUnits':self.depth_units,
            'heightUnits':self.height_units,
            'depth':self.depth,
            'height':self.height,
            'description':self.description,
            'id':self.id,
            'cost':'%s' %self.cost,
            'reference':self.reference,
            'currency':self.currency
        }
        
        return data
    
    def set_parent_data(self, data):
        if "reference" in data: self.reference = data["reference"]
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "widthUnits" in data: self.width_units = data['widthUnits']
        if "height" in data: self.height = data["height"]
        if "heightUnits" in data: self.height_units = data['heightUnits']
        if "depth" in data: self.depth = data["depth"]
        if "depthUnits" in data: self.depth_units = data['depthUnits']
        if "currency" in data: self.currency = data["currency"]
        if "supplier" in data: self.supplier = Supplier.objects.get(id=data["supplier"]["id"])
        if "supplierID" in data: self.supplier = Supplier.objects.get(id=data["supplierID"])
        
    def get_data(self):
        data = {
                'type':self.type,
                'supplier':self.supplier.get_data(),
                'width':self.width,
                'depth':self.depth,
                'height':self.height,
                'widthUnits':self.width_units,
                'depthUnits':self.depth_units,
                'heightUnits':self.height_units,
                'description':self.description,
                'id':self.id,
                'cost':'%s' % self.cost,
                'currency':self.currency
        }
        
        return data
        
    def set_data(self, data):
        if "cost" in data: self.cost = Decimal(data["cost"])
        if "width" in data: self.width = data['width']
        if "height" in data: self.height = data["height"]
        if "depth" in data: self.depth = data["depth"]
        
