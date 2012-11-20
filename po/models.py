from django.db import models
from supplies.models import Supply
from contacts.models import Supplier
from boto.s3.connection import S3Connection
from django.conf import settings
from decimal import Decimal
import datetime


# Create your models here.

class PurchaseOrder(models.Model):
    
    supplier = models.ForeignKey(Supplier)
    orderDate = models.DateField(db_column = "order_date", null=True, default = datetime.date.today())
    total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    url = models.TextField(null = True)
    key = models.TextField(null = True)
    bucket = models.TextField(null = True)
    
    def create(self, data):
        #imports
        from poPDF.models import PurchaseOrderPDF
        #We will create the purchase order first
        #and then save it before creating the purchase order items 
        #so that the items have something to link to
        
        #get supplier from data
        if "supplier" in data:
            self.supplier = Supplier.objects.get(id=data["supplier"])
            
        #save the purchase
        self.save()
        
        #array to hold total
        self.total = 0
        #array to hold supplies
        self.supplies = []
        #checks to see if has supplies to order
        if "supplies" in data:
            #iterate to create purchase order items
            for supplyData in data["supplies"]:
                #create item and apply data
                poItem = PurchaseOrderItems()
                poItem.create(supplyData)
                poItem.setPO(self)
                #save the item
                poItem.save()
                #add to array
                self.supplies.append(poItem)
                
                #add supply total to po total
                self.total = self.total + poItem.total
        #creates the PDF and retrieves the returned
        #data concerning location of file
        pdf = PurchaseOrderPDF(supplier=self.supplier, supplies=self.supplies, po=self)
        pdfData = pdf.create()
        #sets the pdf
        self.url = pdfData['url']
        self.key = pdfData['key']
        self.bucket = pdfData['bucket']
        self.save()

    #get data
    def getData(self):
        #get the url
        
       
        data = {
                'url':self.getUrl(),
                'id':self.id,
                'orderDate':self.orderDate.isoformat()
                }
        return data
    
    def getUrl(self):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key = self.key, force_http=True)
        #return the url
        return url
    
    
class PurchaseOrderItems(models.Model):
    
    purchaseOrder = models.ForeignKey(PurchaseOrder, db_column = "purchase_order_id")
    supply = models.ForeignKey(Supply, db_column = "supply_id")
    quantity = models.IntegerField()
    discount = models.IntegerField()
    unitCost = models.DecimalField(decimal_places=2, max_digits=12, default=0, db_column="unit_cost")
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    
    
    #set po
    def setPO(self, po):
        self.purchaseOrder = po
        
    #create
    def create(self, data):
        if "id" in data:
            self.supply = Supply.objects.get(id=data["id"])
            self.description = self.supply.description
            self.cost = self.supply.cost
            self.discount = self.supply.discount
            if self.supply.discount == 0:
                self.unitCost = self.supply.cost
            else:
                discountAmount = self.supply.cost*(Decimal(self.supply.discount)/100)
                self.unitCost = self.supply.cost-discountAmount
            
        if "quantity" in data: 
            self.quantity = data["quantity"]  
            #if there is a discount apply the discount
            self.total = self.unitCost*self.quantity
        


#pdf = PurchaseOrderPDF()
#pdf.create()