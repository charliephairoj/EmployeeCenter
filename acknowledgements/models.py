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
from contacts.models import Customer
from products.models import Product, Upholstery
from supplies.models import Fabric
from acknowledgements.PDF import AcknowledgementPDF, ProductionPDF
# Create your models here.

#Create the __init__ial Acknowledgement category
class Acknowledgement(models.Model):
    #Customer's PO ID
    #We keep for customer
    #courtesy
    po_id = models.TextField(default=None)
    discount = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
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
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    vat = models.IntegerField(default=0)
    
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
                'customer':'%s' % (self.customer.name),
                'employee':'%s %s' %(self.employee.first_name, self.employee.last_name), 
                'products':[]}
        for item in self.item_set.all():
            data['products'].append(item.get_data())
        return data
    
    #Create Acknowledgement
    def create(self, data, user=None):
        #Set ack information
        self.customer = Customer.objects.get(id=data['customer']['id'])
        self.employee = user
        date_obj = data['delivery_date']
        self.delivery_date = datetime.date(date_obj['year'], date_obj['month'], date_obj['date'])
        if "vat" in data: self.vat = int(data["vat"]) 
        if "po_id" in data: self.po_id = data["po_id"]
        if "remarks" in data: self.remarks = data["remarks"]
        self.status = 'ACKNOWLEDGED'
        self.save()
        #Set products information
        for product_data in data['products']:
            self.set_product(product_data)
        #Calculate totals
        self.calculate_totals()
        self.save()
        #Insert into the previous database
        self.insert_into_old_db()
        #Initialize and create pdf  
        ack_pdf = AcknowledgementPDF(customer=self.customer, ack=self, products=self.item_set.all().order_by('id'))
        ack_filename = ack_pdf.create()
        production_pdf = ProductionPDF(customer=self.customer, ack=self, products=self.item_set.all().order_by('id'))
        production_filename = production_pdf.create()
        #Upload and return the url
        self.upload_acknowledgement(ack_filename)
        self.upload_production(production_filename)
        
        urls = {'production_url': self.get_url(self.production_key),
                'acknowledgement_url':self.get_url(self.acknowledgement_key)} 
                
    
        return urls
    
    #Set the product from data
    def set_product(self, product_data):
        if "id" in product_data:
            #Get the product by id
            product = Product.objects.get(id=product_data["id"])
        else:
            product = Product.objects.get(id=10436)
        #Create Ack Item and assign product data
        ack_item = Item()
        ack_item.acknowledgement = self
       
        ack_item.set_data(product, data=product_data, customer=self.customer)
        ack_item.save()
        
    #Calculate totals and subtotals
    def calculate_totals(self):
        running_total = 0
        #Loop through products
        for product in self.item_set.all():
            #Add Price
            running_total += product.total
        #Set Subtotal
        self.subtotal = running_total
        discount = (Decimal(self.discount)/100)*running_total
        running_total -= discount
        vat = (Decimal(self.vat)/100)*running_total
        running_total += vat
        self.total = running_total
    
    #Get the correct product based on type    
    def get_product(self, product_data):
        if product_data["type"] == "Upholstery":
            return Upholstery.objects.get(product_ptr_id=product_data["id"])
    
    #Get the Url of the document
    def get_url(self, key):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key=key, force_http=True)
        #return the url
        return url
    
      
    #uploads the pdf
    def upload(self, filename, file_type):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it 
        k = Key(bucket)        
        #Set file name
        k.key = "acknowledgement/%s-%s.pdf" % (file_type, self.id)
        #upload file and set acl
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        #Remove original
        os.remove(filename)
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        return k.key
        
    def upload_acknowledgement(self, filename):
        self.acknowledgement_key = self.upload(filename, "Acknowledgement")
        self.save()
        
    def upload_production(self, filename):
        self.production_key = self.upload(filename, "Production")
        self.save()
        
    def insert_into_old_db(self):
        conn = psycopg2.connect(host='54.251.62.47', user='postgres', password='Har6401Vard88')
        cur = conn.cursor()
        customer_upsert = """WITH upsert AS (UPDATE customers SET name = %(name)s, telephone = %(telephone)s, email = %(email)s
            WHERE customer_id = %(id)s RETURNING customer_id) INSERT INTO customers(customer_id, name, telephone, email) SELECT %(id)s, %(name)s,
            %(telephone)s, %(email)s WHERE NOT EXISTS (SELECT 1 FROM upsert)"""
        address_upsert = """WITH upsert AS (UPDATE customer_addresses SET customer_id = %(customer_id)s, address = %(address)s,
            city = %(city)s, territory = %(territory)s, country = %(country)s, zipcode = %(zipcode)s WHERE address_id = %(id)s 
            RETURNING customer_id) INSERT INTO customer_addresses(customer_id, address, city, territory, country, zipcode) SELECT %(id)s, 
            %(address)s, %(city)s, %(territory)s, %(country)s, %(zipcode)s WHERE NOT EXISTS (SELECT 1 FROM upsert)"""
        ack_query = """INSERT INTO acknowledgements (acknowledgement_id, customer_id, time_created, delivery_date, po_id, employee_id, status) 
        VALUES(%(id)s, %(customer_id)s, %(time_created)s, %(delivery_date)s, %(po_id)s, %(employee_id)s, 'ACKNOWLEDGED')"""
        product_query = """INSERT INTO acknowledgement_items(acknowledgement_item_id, acknowledgement_id, product_id, quantity,
        fabric, item_description, custom, custom_item, width, depth, height, status) VALUES(%(item_id)s, %(acknowledgement_id)s, %(product_id)s,
        %(quantity)s, %(fabric)s, %(description)s, %(is_custom_size)s, %(is_custom_item)s, %(width)s, %(depth)s, %(height)s, 'ACKNOWLEDGED')"""
        pillow_query = """INSERT INTO acknowledgement_item_pillows(acknowledgement_pillow_id, acknowledgement_item_id, type,
            quantity, fabric) VALUES(%(id)s, %(item_id)s, %(type)s, %(quantity)s, %(fabric)s)"""
        customer_data = {'id':self.customer.id,
                         'name':self.customer.name,
                         'telephone':self.customer.telephone,
                         'email':self.customer.email}
        address = self.customer.address_set.all()[0]
        address_data = {'id':address.id,
                        'customer_id':address.contact.id,
                        'address':address.address1,
                        'city':address.city,
                        'territory':address.territory,
                        'country':address.country,
                        'zipcode':address.zipcode}
        ack_data = {'id':self.id, 
                    'customer_id':self.customer.id,
                    'time_created':self.time_created,
                    'delivery_date':self.delivery_date,
                    'po_id':self.po_id,
                    'employee_id':15001} 
        
        cur.execute(customer_upsert, customer_data)
        cur.execute(address_upsert, address_data)
        cur.execute(ack_query, ack_data)
        
        
        for item in self.item_set.all():
            #Attempt to get fabric and uses none 
            #If there is no fabric
            try:
                fabric = item.fabric.description
            except:
                fabric = None
            item_data = {'item_id':item.id,
                         'product_id':item.product.id,
                         'acknowledgement_id':self.id,
                         'quantity':item.quantity,
                         'fabric':fabric,
                         'description':item.description,
                         'is_custom_size':item.is_custom_size,
                         'is_custom_item':item.is_custom_item,
                         'width':item.width,
                         'depth':item.depth,
                         'height':item.height}
            cur.execute(product_query, item_data)
            for pillow in item.pillow_set.all():
                pillow_data = {'id':pillow.id, 
                               'item_id':item.id,
                               'type':pillow.type,
                               'quantity':pillow.quantity,
                               'fabric':pillow.fabric.description}
                cur.execute(pillow_query, pillow_data)
        #Commit the changes
        conn.commit()
        
#Create the Acknowledgement Items
class Item(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement)
    product = models.ForeignKey(Product)
    type = models.CharField(max_length=20)
    #Price not including discount
    quantity = models.IntegerField(null=False)
    unit_price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    fabric = models.ForeignKey(Fabric)
    fabric_description = models.TextField(default=None)
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size', default=False)
    is_custom_item = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    bucket = models.TextField()
    image_key = models.TextField()
    comments = models.TextField()
    
    def set_data(self, product, data=None, user=None, customer=None):
        """Set the objects attributes with data from the product
        as defined by the database. After, if there is a data object
        they data object will used to be set the attributes with the 
        proper check for which can be overwritten and which can't"""
        #Set quantity used for calculation later
        if data != None:
            if "quantity" in data: self.quantity = int(data["quantity"])
            
        else:
            self.quantity = 0
        #Set from product
        self._set_attr_from_product(product, customer)
        #Set from data if exists
        if data != None:
            self._set_attr_from_data(data)
                
    def _set_attr_from_product(self, product, customer):
        self.description = product.description
        self.product = product
        #Get Price based on customer typpe
        if customer.type == "Retail":
            price = product.retail_price
        elif customer.type == "Dealer":
            price = product.wholesale_price
        else:
            if product.retail_price != 0 and product.retail_price is not None:
                price = product.retail_price
            else:
                price = 0
        #Make price 0 if none
        if price is None: price = 0
        #Set the unit price then total 
        self.unit_price = price
        self.total = self.unit_price*Decimal(self.quantity)
        #Set dimensions
        self.width = product.width
        self.depth = product.depth
        self.height = product.height
        #Set Image properties
        self.bucket = product.bucket
        self.image_key = product.image_key
        self.save()
        
                
    def _set_attr_from_data(self, data):
        """Sets the attribute, but checks if they
        exists first."""
        if "comments" in data: self.comments = data["comments"]
        #Set dimensions
        if "is_custom_size" in data:
            if data["is_custom_size"] == True:
                self.is_custom_size = True
                #Checks if data is greater than 0
                if "width" in data and data['width'] > 0: self.width = int(data['width'])
                if "depth" in data and data['depth'] > 0: self.depth = int(data['depth'])
                if "height" in data and data['height'] > 0: self.height = int(data['height'])
        #Checks if it a custom item
        if "is_custom" in data:
            if data["is_custom"] == True:
                self.is_custom_item = True
                self.description = data["description"]
                #Add Image to product if exists
                if "image" in data:
                    self.image_key = data["image"]["key"]
                    self.bucket = data["image"]["bucket"]
        #Checks if fabric in data
        if "fabric" in data:
            fabric = Fabric.objects.get(id=data["fabric"]["id"])
            self.fabric = fabric
        #Checks if this item has pillows
        if "pillows" in data:
            pillows = []
            for pillow in data["pillows"]:
                for i, item in enumerate(pillows):
                    if item["type"] == pillow["type"] and item["fabric"]["description"] == pillow["fabric"]["description"]:
                            pillows[i]["quantity"] += 1
                            break
                else:
                    if "quantity" not in pillow: pillow["quantity"] = 1
                    pillows.append(pillow)
                    
           
            #Get pillows
        
            for pillow in pillows:
                ack_pillow = Pillow()
                ack_pillow.item = self
                ack_pillow.type = pillow["type"]
                ack_pillow.quantity = pillow["quantity"]*self.quantity
                ack_pillow.fabric = Fabric.objects.get(id=pillow["fabric"]["id"])
                ack_pillow.save()
    
    def get_data(self):
        data = {'id':self.id,
                'is_custom_size':self.is_custom_size,
                'width':self.width,
                'height':self.height,
                'depth':self.depth,
                'description':self.description,
                'comments':self.comments,
                'image':{'url':self._get_image_url()}}
        return data
    
    def _get_image_url(self):
        if self.bucket is not None and self.image_key is not None:
            conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
            url = conn.generate_url(1800, 'GET', bucket=self.bucket, key=self.image_key, force_http=True)
        else:
            url = None
        return url
        
#Pillows for Acknowledgement items
class Pillow(models.Model):
    item = models.ForeignKey(Item)
    type = models.CharField(max_length=10, null=True)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric)
        
    





