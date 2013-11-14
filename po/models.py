"""
Models for the Purchase Orders App
"""
import sys, os
import datetime
import logging
from decimal import Decimal
import dateutil.parser

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


from supplies.models import Supply
from contacts.models import Supplier, SupplierContact
from auth.models import S3Object
from po.PDF import PurchaseOrderPDF


# Create your models here.
class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier)
    order_date = models.DateTimeField(default=datetime.datetime.today())
    receive_date = models.DateTimeField(null=True)
    terms = models.IntegerField()
    vat = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
    shipping_type = models.CharField(max_length=10, default="none")
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="THB")
    #refers to the total of all items
    subtotal = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to total after discount
    total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to the todal after vat
    grand_total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    employee = models.ForeignKey(User)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    pdf = models.ForeignKey(S3Object, null=True)
    
    @classmethod
    def create(cls, user=None, **kwargs):
        """
        Creates a purchase order
        
        This method creates the order details first, then 
        creates the supplies. The totals of the supplies are 
        then added and applied to the purchase order. The 
        order and supplies are then saved
        """
        order = cls()
        
        order.employee = user
        try:
            order.supplier = Supplier.objects.get(pk=kwargs["supplier"]["id"])
            order.currency = order.supplier.currency
            order.terms = order.supplier.terms
        except KeyError: 
            raise ValueError("Expecting supplier ID")
        try:
            order.vat = int(kwargs["vat"])
        except KeyError:
            raise ValueError("Expecting a vat")
        
        if 'discount' in kwargs:
            order.discount = int(kwargs['discount'])
        try:
            order.temporary_supplies = []
            for supply_data in kwargs["items"]:
                supply = Item.create(commit=False, **supply_data)
                order.temporary_supplies.append(supply)
                
        except KeyError:
            raise ValueError("Expecting a list of supplies")
        except Supply.DoesNotExist:
            pass
       
        order.subtotal = sum([supply.total for supply in order.temporary_supplies])
        order.total = order.subtotal - ((Decimal(order.discount)/100) * order.subtotal)
        order.grand_total = Decimal(order.total) * (Decimal(1) + Decimal(order.vat)/100)
        
        #Save the order
        order.save()
        
        #Save all the items in the order
        for supply in order.temporary_supplies:
            supply.purchase_order = order
            supply.save()
           
        #Create and upload pdf 
        pdf = PurchaseOrderPDF(po=order, items=order.item_set.all(),
                               supplier=order.supplier)
        filename = pdf.create()
        key = "purchase_order/PO-{0}.pdf".format(order.id)
        order.pdf = S3Object.create(filename, key, 'document.dellarobbiathailand.com')
        order.save()
        print order.pdf
        
        return order
    
    def create_pdf(self):
        """
        Creates a pdf and returns the filename
        """
        #Create and upload pdf 
        print self.item_set.all()
        pdf = PurchaseOrderPDF(po=self, items=self.item_set.all(),
                               supplier=self.supplier)
        filename = pdf.create()
        return filename
        
    def create_and_upload_pdf(self):
        """
        Creates a pdf and uploads it to the S3 service
        """
        filename = self.create_pdf()
        key = "purchase_order/PO-{0}.pdf".format(self.id)
        self.pdf = S3Object.create(filename, key, 'document.dellarobbiathailand.com')
        self.save()
    

class Item(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name="items")
    supply = models.ForeignKey(Supply, db_column="supply_id", related_name="+")
    description = models.TextField()
    quantity = models.IntegerField()
    discount = models.IntegerField(default=0)
    unit_cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    def __init__(self, **kwargs):
        super(Item, self).__init__(**kwargs)
        
        try:
            self.supply = Supply.objects.get(pk=kwargs['supply']['id'])
        except Supply.DoesNotExist:
            raise 
        except KeyError:
            self.supply = Supply.objects.all()[0]#self.supply = Supply.objects.get(pk=kwargs['id'])
            
        self.purchase_order = PurchaseOrder.objects.all()[0]
        self.quantity = 1
        self.description = 'test'
        
    @classmethod
    def create(cls, **kwargs):
        item = cls()
        if "id" in kwargs:
            item.supply = Supply.objects.get(id=kwargs["id"])
            item.description = item.supply.description
            item.unit_cost = item.supply.cost
            item.discount = item.supply.discount
            if item.supply.discount == 0:
                item.unit_cost = item.supply.cost
            else:
                if sys.version_info[:2] == (2, 6):
                    discount_amount = item.supply.cost * (Decimal(str(item.supply.discount) / 100))
                elif sys.version_info[:2] == (2, 7):
                    discount_amount = item.supply.cost * (Decimal(item.supply.discount) / 100)
                item.unit_cost = round(item.supply.cost - discount_amount, 2)

        if "quantity" in kwargs:
            item.quantity = int(Decimal(kwargs["quantity"]))
            #if there is a discount apply the discount
            item.total = Decimal(item.unit_cost * Decimal(item.quantity))
        return item
    
    def dict(self, user=None):
        """
        Returns the Item's attributes as a dictionary
        """
        data = {'supply': {'id': self.supply.id},
                'quantity': self.quantity,
                'unit_cost': round(self.unit_cost, 2),
                'total': round(self.total, 2)}
            
    def save(self, commit=True):
        """
        Saves the item to the database
        
        Method saves the item to the database
        if commit is True
        """
        if commit:
            super(Item, self).save()
