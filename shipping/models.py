import sys, os
import datetime
import logging
import psycopg2
import dateutil.parser
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key

from acknowledgements.models import Acknowledgement, Item as AckItem
from contacts.models import Customer
from shipping.PDF import ShippingPDF
import acknowledgements
from auth.models import S3Object


class Shipping(models.Model):
    delivery_date = models.DateTimeField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    acknowledgement = models.ForeignKey(Acknowledgement,
                                        on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    time_created = models.DateTimeField(auto_now_add=True)
    pdf = models.ForeignKey(S3Object, related_name='+', null=True)
    comments = models.TextField(null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def get_data(self):

        data = {'acknowledgement': {'id': self.acknowledgement.id},
                'delivery_date': self.delivery_date.isoformat(),
                'customer': self.customer.to_dict(),
                'id': self.id,
                'employee': '{0} {1}'.format(self.employee.first_name,
                                             self.employee.last_name)}
        try:
            data['products'] = [product.get_data() for product in self.item_set.all()]
        except AttributeError:
            data['products'] = [product.to_dict() for product in self.item_set.all()]
       
        return data

    @classmethod
    def create(cls, user=None, override_id=False, **kwargs):
        data = kwargs
        shipping = cls()
        if override_id and 'id' in kwargs:
            shipping.id = kwargs['id']
        #Set the data from the shippping
        shipping.acknowledgement = Acknowledgement.objects.get(id=data["acknowledgement"]['id'])
        try:
            shipping.customer = Customer.objects.get(id=data['customer']['id'])
        except KeyError:
            shipping.customer = shipping.acknowledgement.customer
        shipping.employee = user
        try:
            shipping.delivery_date = data["delivery_date"]
        except KeyError:
            shipping.delivery_date = shipping.acknowledgement.delivery_date
            
        if "comments" in data:
            shipping.comments = data["comments"]
        else:
            shipping.comments = shipping.acknowledgement.remarks
            
        shipping.save()

        try:
            shipping.process_items(kwargs['items'])
        except:
            shipping.process_items([{'id':item.id} for item in shipping.acknowledgement.items.all()])

        #shipping.update_acknowledgement_data()
        #Initialize and create pdf
        pdf = ShippingPDF(customer=shipping.customer, shipping=shipping,
                          products=shipping.item_set.all().order_by('id'))
        shipping_filename = pdf.create()
        #Upload and return the url
        shipping.pdf = S3Object.create(shipping_filename,
                                   "shipping/Shipping-{0}.pdf".format(shipping.id),
                                   'document.dellarobbiathailand.com')
        shipping.save()

        return shipping
    
    def process_items(self, items):
        """
        Creates all the items in the array
        """
        id_list = [item['id'] for item in items]
        for item in self.acknowledgement.items.all():
            if item.id in id_list:
                shipped_item = Item()
                shipped_item.shipping = self
                shipped_item.set_data_from_acknowledgement_item(item)
                shipped_item.save()
                
                #Set the status of the item
                item.status = 'SHIPPED'
                item.save()

    def set_product(self, data):

        acknowledgement_item = AckItem.objects.get(id=data['id'])
        item = Item()
        item.shipping = self
        item.set_data_from_acknowledgement_item(acknowledgement_item)
        if "comments" in data:
            item.comments = data["comments"]
        item.save()

        acknowledgement_item.status = 'SHIPPED'
        acknowledgement_item.save()

    def update_acknowledgement_data(self):
        self.acknowledgement.current_employee = self.employee
        self.acknowledgement.delivery_date = self.delivery_date
        if len(self.acknowledgement.item_set.all()) == len(self.item_set.all()):
            self.acknowledgement.status = 'SHIPPED'
        else:
            self.acknowledgement.status = 'PARTIALLY SHIPPED'
        self.acknowledgement.save()
        
    def create_pdf(self):
        #shipping.update_acknowledgement_data()
        #Initialize and create pdf
        pdf = ShippingPDF(customer=self.customer, shipping=self,
                          products=self.item_set.all().order_by('id'))
        filename = pdf.create()
        
        return filename
        
    def create_and_upload_pdf(self):
        """
        Creates a pdf of the shipping manifest and uploads
        it to the S3 service
        """
        filename = self.create_pdf()
       
        #Upload and return the url
        self.pdf = S3Object.create(filename,
                                   "shipping/Shipping-{0}.pdf".format(self.id),
                                   'document.dellarobbiathailand.com')
        self.save()
        return self.pdf

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

    def to_dict(self):
        data = {'id': self.id,
                'description': self.description,
                'quantity': self.quantity,
                'comments': self.comments}
        try:
            data.update(self.item.to_dict())

        except AttributeError as e:
            pass
        return data
    
    def get_data(self):
        data = {'id': self.id,
                'description': self.description,
                'quantity': self.quantity,
                'comments': self.comments}
        
        try:
            data.update(self.item.to_dict())
        except:
            pass
        
        return data

