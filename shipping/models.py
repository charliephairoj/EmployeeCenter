import sys, os
import datetime
import logging
import psycopg2
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from acknowledgements.models import Acknowledgement
from contacts.models import Customer
from shipping.PDF import ShippingPDF
import acknowledgements


class Shipping(models.Model):
    delivery_date = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    acknowledgement = models.ForeignKey(Acknowledgement, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    bucket = models.TextField()
    time_created = models.DateTimeField(auto_now_add=True)
    shipping_key = models.TextField()
    comments = models.TextField()
    connection = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    
    def get_data(self):
        data = {'delivery_date':self.delivery_date.strftime('%B %d, %Y'),
                'customer':self.customer.get_data(),
                'id':self.id,
                'employee':'{0} {1}'.format(self.employee.first_name, self.employee.last_name)}
        return data
    
    def create(self, data, user):
        #Set the data from the shippping
        self.customer = Customer.objects.get(id=data['customer']['id'])
        self.acknowledgement = Acknowledgement.objects.get(id=data["acknowledgement"]['id'])
        self.employee = user
        self.delivery_date = datetime.datetime.fromtimestamp(data["delivery_date"]/1000.0)
        if "comments" in data: self.comments = data["comments"]
        self.save()
        
        #Set products information
        for product_data in data['products']:
            self.set_product(product_data)
        
        self.set_acknowledgement_data()
        
        #Initialize and create pdf  
        pdf = ShippingPDF(customer=self.customer, shipping=self, products=self.item_set.all().order_by('id'),
                          connection=self.connection)
        shipping_filename = pdf.create()
        #Upload and return the url
        self.shipping_key = self.upload(shipping_filename)
        urls = {'url': self.get_url(self.shipping_key)} 
        return urls
    
    def set_product(self, data):
        acknowledgement_item = acknowledgements.models.Item.objects.get(id=data['id'])
        item = Item()
        item.shipping = self
        item.set_data_from_acknowledgement_item(acknowledgement_item)
        if "comments" in data: item.comments = data["comments"]
        item.save()
    
    def set_acknowledgement_data(self):
        self.acknowledgement.delivery_date = self.delivery_date
        if len(self.acknowledgement.item_set.all()) == len(self.item_set.all()):
            self.acknowledgement.status = 'SHIPPED'
        else:
            self.acknowledgement.status = 'PARTIALLY SHIPPED'
        self.acknowledgement.save()
            
    #uploads the pdf
    def upload(self, filename):
        #start connection
        conn = self.connection
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        k = Key(bucket)        
        k.key = "shipping/Shipping-{0}.pdf".format(self.id)
        #upload file and set acl
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        os.remove(filename)
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        return k.key
      
    #Get the Url of the document
    def get_url(self, key):
        #start connection
        conn = self.connection
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key=key, force_http=True)
        #return the url
        return url
    
class Item(models.Model):
    shipping = models.ForeignKey(Shipping)
    item = models.ForeignKey(acknowledgements.models.Item)
    description = models.TextField()
    quantity = models.IntegerField()    
    comments = models.TextField()
    
    def set_data_from_acknowledgement_item(self, item):
        self.item = item
        self.description = item.description
        self.quantity = item.quantity
    
    
    
        