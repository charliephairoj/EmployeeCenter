from django.db import models
from django.contrib.auth.models import User
from contacts.models import Contacts
from products.models import Products

# Create your models here.

#Create the initial Acknowledgement category
class Acknowledgements(models.Model):
    acknowledgementID = models.AutoField(primary_key=True, unique=True, db_column='acknowledgement_id')
    #Customer's PO ID
    #We keep for customer
    #courtesy
    poID = models.TextField(db_column='po_id')
    discount = models.IntegerField()
    customer = models.ForeignKey(Contacts, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    timeCreated = models.DateTimeField(db_column='time_created', auto_now_add=True)
    
#Create the Acknowledgement Items
class AcknowledgementItems(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgements)
    product = models.ForeignKey(Products)
    #Price not including discount
    quantity = models.IntegerField(not_null=True)
    price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    internalWidth = models.IntegerField(db_column='width', default=0)
    internalDepth = models.IntegerField(db_column='depth', default=0)
    internalHeight = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    internalUnits = 'mm',
    externalUnits = 'mm',
    fabric = models.TextField()
    description = models.TextField()
    isCustomSize = models.BooleanField(db_column='is_custom_size', default=False)
    status = models.CharField(max_length=50)
   
    
    #Declare the custom properties
    def getWidth(self):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                return self.internalWidth
            elif self.externalUnits == 'cm':
                return (self.internalWidth/10)
            elif self.externalUnits == 'm':
                return (self.internalWidth/1000)
    def setWidth(self, value):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                self.internalWidth = value
            elif self.externalUnits == 'cm':
                self.internalWidth = value*10
            elif self.externalUnits == 'm':
                self.internalWidth = value*1000
    width = property(getWidth, setWidth)
    
    def getDepth(self):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                return self.internalDepth
            elif self.externalUnits == 'cm':
                return (self.internalDepth/10)
            elif self.externalUnits == 'm':
                return (self.internalDepth/1000)
    def setDepth(self, value):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                self.internalDepth = value
            elif self.externalUnits == 'cm':
                self.internalDepth = value*10
            elif self.externalUnits == 'm':
                self.internalDepth = value*1000
    depth = property(getDepth, setDepth)
    
    def getHeight(self):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                return self.internalHeight
            elif self.externalUnits == 'cm':
                return (self.internalHeight/10)
            elif self.externalUnits == 'm':
                return (self.internalHeight/1000)
    def setHeight(self, value):
        if self.internalUnits == 'mm':
            if self.externalUnits == 'mm':
                self.internalHeight = value
            elif self.externalUnits == 'cm':
                self.internalHeight = value*10
            elif self.externalUnits == 'm':
                self.internalHeight = value*1000
    height = property(getHeight, setHeight)
        
    #methods
    def changeUnitsTo(self,value):
        self.externalUnits = value