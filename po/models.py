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


logger = logging.getLogger(__name__)


# Create your models here.
class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier)
    order_date = models.DateTimeField(default=datetime.datetime.today())
    created = models.DateTimeField(auto_now_add=True)
    receive_date = models.DateTimeField(null=True)
    terms = models.IntegerField(default=0)
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
    status = models.TextField(default="Ordered")
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
        pdf = PurchaseOrderPDF(po=order, items=order.items.all(),
                               supplier=order.supplier)
        filename = pdf.create()
        key = "purchase_order/PO-{0}.pdf".format(order.id)
        order.pdf = S3Object.create(filename, key, 'document.dellarobbiathailand.com')
        order.save()
        print order.pdf
        
        return order
    
    def calculate_total(self):
        """
        Calculate the subtotal, total, and grand total
        """
        return self._calculate_grand_total()
        
    def create_pdf(self):
        """
        Creates a pdf and returns the filename
        """
        #Create and upload pdf 
        pdf = PurchaseOrderPDF(po=self, items=self.items.all(),
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
    
    def _calculate_subtotal(self):
        """
        Calculate the subtotal
        """
        if self.items.count() > 0:
            self.subtotal = sum([item.total for item in self.items.all()])
        else:
            raise ValueError('Missing items')
        
        logging.debug("The subtotal is {0:.2f}".format(self.subtotal))
        return self.subtotal
    
    def _calculate_total(self):
        """
        Calculate the total
        """
        subtotal = self._calculate_subtotal()
        if self.discount > 0:
            self.total = subtotal - ((Decimal(self.discount) / Decimal('100')) * subtotal)
        else:
            self.total = subtotal

        logging.debug("The total is {0:.2f}".format(self.total))
        return self.total
    
    def _calculate_grand_total(self):
        """
        Calcualte the grand total
        """
        total = self._calculate_total()
        if self.vat > 0:
            self.grand_total = total + (total * (Decimal(self.vat) / Decimal('100')))
        else:
            self.grand_total = total
        
        logging.debug("The grand total is {0:.2f}".format(self.grand_total))
        return self.grand_total
        
class Item(models.Model):
    
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items')
    supply = models.ForeignKey(Supply, db_column="supply_id", related_name="+")
    description = models.TextField()
    quantity = models.IntegerField()
    status = models.TextField(default="Ordered")
    discount = models.IntegerField(default=0)
    unit_cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
        
    @classmethod
    def create(cls, **kwargs):
        print kwargs
        item = cls()
        try:
            item.supply = Supply.objects.get(id=kwargs['supply']["id"])
        except KeyError:
            item.supply = Supply.objects.get(id=kwargs['id'])
            
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
    
    
