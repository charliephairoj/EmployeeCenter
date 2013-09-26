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

from acknowledgements.models import Acknowledgement, AcknowledgementLog, Item as AckItem
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
    bucket = models.TextField()
    time_created = models.DateTimeField(auto_now_add=True)
    shipping_key = models.TextField()
    pdf = models.ForeignKey(S3Object, related_name='+')
    comments = models.TextField()
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    connection = S3Connection(settings.AWS_ACCESS_KEY_ID,
                              settings.AWS_SECRET_ACCESS_KEY)

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

    def create(self, data, user):
        #Set the data from the shippping
        self.customer = Customer.objects.get(id=data['customer']['id'])
        self.acknowledgement = Acknowledgement.objects.get(id=data["acknowledgement"]['id'])
        self.employee = user
        self.delivery_date = dateutil.parser.parse(data["delivery_date"])
        if "comments" in data:
            self.comments = data["comments"]
        self.save()

        #Set products information
        for product_data in data['products']:
            self.set_product(product_data)

        self.update_acknowledgement_data()
        #Initialize and create pdf
        pdf = ShippingPDF(customer=self.customer, shipping=self,
                          products=self.item_set.all().order_by('id'),
                          connection=self.connection)
        shipping_filename = pdf.create()
        #Upload and return the url
        self.pdf = S3Object.create(shipping_filename,
                                   "shipping/Shipping-{0}.pdf".format(self.id),
                                   'document.dellarobbiathailand.com')
        self.save()

        message = "Acknowledgement {0} Has Shipped: Shipping#{1}".format(self.acknowledgement.id, self.id)
        AcknowledgementLog.create(message, self.acknowledgement, self.employee)

        urls = {'url': self.pdf.generate_url()}
        return urls

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

