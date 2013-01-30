from django.db import models
from django.contrib.auth.models import User
from contacts.models import Contact
from products.models import Product

# Create your models here.

#Create the initial Acknowledgement category
class Acknowledgement(models.Model):
    #Customer's PO ID
    #We keep for customer
    #courtesy
    po_id = models.TextField()
    discount = models.IntegerField()
    customer = models.ForeignKey(Contact, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    time_created = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateField()
    status = models.TextField()
    production_key = models.TextField()
    acknowledgement_key = models.TextField()
    bucket = models.TextField()
    remarks = models.TextField()
    fob = models.TextField()
    shipping = models.TextField()
    
    #Get Data
    def get_data(self):
        
        data = {
                'id':self.id,
                'delivery_date':self.delivery_date.strftime('%B %d, %Y'),
                'time_created':self.time_created.strftime('%B %d, %Y %H:%M:%S'), 
                'status':self.status, 
                'remarks':self.remarks,
                'fob':self.fob,
                'shipping':self.shipping, 
                'customer':self.customer.name,
                'employee':'%s %s' %(self.employee.first_name, self.employee.last_name)}
        
        return data
    
#Create the Acknowledgement Items
class AcknowledgementItem(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement)
    product = models.ForeignKey(Product)
    #Price not including discount
    quantity = models.IntegerField(null=False)
    price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    internalUnits = 'mm',
    externalUnits = 'mm',
    fabric = models.TextField()
    description = models.TextField()
    isCustomSize = models.BooleanField(db_column='is_custom_size', default=False)
    status = models.CharField(max_length=50)
   
    





