import sys, os
import datetime
import logging
from decimal import Decimal
import dateutil.parser

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from reportlab.lib import colors, utils
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from supplies.models import Supply
from contacts.models import Supplier, SupplierContact
from po.PDF import PurchaseOrderPDF


logger = logging.getLogger('tester')


# Create your models here.
class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier)
    order_date = models.DateTimeField(default=datetime.datetime.today())
    delivery_date = models.DateTimeField(null=True)
    vat = models.IntegerField(default=0)
    shipping_type = models.CharField(max_length=10, default="none")
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="THB")
    #refers to the total of all items
    subtotal = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to total after discount
    total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to the todal after vat
    grand_total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    url = models.TextField(null=True)
    key = models.TextField(null=True)
    bucket = models.TextField(null=True)
    employee = models.ForeignKey(User)

    def create(self, data, user=None):

        #We will create the purchase order first
        #and then save it before creating the purchase order items
        #so that the items have something to link to
        #Set the employee that placed the order
        if user != None:
            self.employee = user
        #get supplier from data
        if "supplier" in data:
            self.supplier = Supplier.objects.get(id=data["supplier"]['id'])
        if "attention" in data:
            self.attention = data["attention"]
        #apply vat and currency
        if "vat" in data:
            self.vat = float(data["vat"])
        self.currency = self.supplier.currency
        #set the deliverydate
        if "delivery_date" in data:
            delivery_date = dateutil.parser.parse(data["delivery_date"])
            self.delivery_date = delivery_date
        #save the purchase
        self.save()
        #model to hold subtotal
        self.subtotal = 0
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
                self.subtotal = self.subtotal + poItem.total
        #checks if there was a shipping charge
        if "shipping" in data:
            #checks whether shipping is charged
            if data['shipping'] != False:
                if "type" in data["shipping"]:
                    self.shipping_type = data['shipping']['type']
                if "amount" in data["shipping"]:
                    self.shipping_amount = Decimal(data['shipping']['amount'])
                #add shipping to subtotal
                self.subtotal = self.subtotal + self.shipping_amount
        #Calculates the totals of the PO
        #calculate total after discount
        if self.supplier.discount != 0:
            #percentage
            if sys.version_info[:2] == (2, 6):
                percentage = Decimal(str(self.supplier.discount))/100
            elif sys.version_info[:2] == (2, 7):
                percentage = Decimal(self.supplier.discount)/100
            #amount to discount based off of subtotal
            discount_amount = self.subtotal * percentage
            #remaining total after subtracting discount
            self.total = self.subtotal - discount_amount
        #if no supplier discount
        else:
            #total is equal to subtotal
            self.total = self.subtotal
        #calculate total after tax
        if self.vat != 0 or self.vat != '0':
            #get vat percentage
            if sys.version_info[:2] == (2, 6):
                percentage = Decimal(str(self.vat)) / 100
            elif sys.version_info[:2] == (2, 7):
                percentage = Decimal(self.vat) / 100
            #get vat amount
            vat_amount = self.total * percentage
            #remaining grand total after adding vat
            self.grand_total = self.total + vat_amount
        else:
            #grand total is equal to total
            self.grand_total = self.total

        #save the data
        self.save()
        #creates the PDF and retrieves the returned
        #data concerning location of file
        if "attention" in data:
            att_id = data["attention"]["id"]
            att = SupplierContact.objects.get(id=att_id)
        else:
            att = None
        #Create the pdf object and have it create a pdf
        pdf = PurchaseOrderPDF(supplier=self.supplier, supplies=self.supplies,
                               po=self, attention=att)
        filename = pdf.create()
        #update pdf
        self.__upload(filename)
        self.save()

    #get data
    def get_data(self, user=None):
        #get the url
        data = {
                'url': self.get_url(),
                'id': self.id,
                'order_date': self.order_date.isoformat(),
                'employee': self.employee.first_name + ' ' + self.employee.last_name
                }
        return data

    def get_url(self):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                            settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key=self.key,
                                force_http=True)
        #return the url
        return url

    #uploads the pdf
    def __upload(self, filename):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                            settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = "purchase_order/Purchase_Order-%s.pdf" % self.id
        #upload file and set acl
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        #Remove original
        os.remove(filename)
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        self.key = k.key
        self.save()

class PurchaseOrderItems(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder)
    supply = models.ForeignKey(Supply, db_column="supply_id")
    quantity = models.IntegerField()
    discount = models.IntegerField()
    unit_cost = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    currency = models.CharField(max_length=10, default="THB")

    #set po
    def setPO(self, po):
        self.purchase_order = po

    #create
    def create(self, data):
        if "id" in data:
            self.supply = Supply.objects.get(id=data["id"])
            self.description = self.supply.description
            self.cost = self.supply.cost
            self.discount = self.supply.discount
            if self.supply.discount == 0:
                self.unit_cost = self.supply.cost
            else:
                if sys.version_info[:2] == (2, 6):
                    discount_amount = self.supply.cost * (Decimal(str(self.supply.discount) / 100))
                elif sys.version_info[:2] == (2, 7):
                    discount_amount = self.supply.cost * (Decimal(self.supply.discount) / 100)
                self.unit_cost = self.supply.cost - discount_amount

        if "quantity" in data:
            self.quantity = data["quantity"]
            #if there is a discount apply the discount
            print self.unit_cost
            print self.quantity
            self.total = self.unit_cost * Decimal(self.quantity)
