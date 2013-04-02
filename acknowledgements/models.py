import os
import datetime
import dateutil.parser

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto.ses

from contacts.models import Customer
from products.models import Product, Upholstery
from supplies.models import Fabric
from acknowledgements.PDF import AcknowledgementPDF, ProductionPDF
from auth.models import Log


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
    delivery_date = models.DateTimeField()
    status = models.TextField()
    production_key = models.TextField()
    acknowledgement_key = models.TextField()
    bucket = models.TextField()
    remarks = models.TextField()
    fob = models.TextField()
    shipping_method = models.TextField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    vat = models.IntegerField(default=0)
    last_modified = models.DateTimeField()

    #Get Data
    def get_data(self):
        data = {
                'id': self.id,
                'delivery_date': self.delivery_date.isoformat(),
                'time_created': self.time_created.isoformat(),
                'status': self.status,
                'remarks': self.remarks,
                'fob': self.fob,
                'vat': self.vat,
                'shipping': self.shipping_method,
                'customer': self.customer.get_data(),
                'employee': u'{0} {1}'.format(self.employee.first_name,
                                              self.employee.last_name),
                'products': []}
        for item in self.item_set.all().order_by('id'):
            data['products'].append(item.get_data())
        return data

    #Create Acknowledgement
    def create(self, data, user=None):
        #Set ack information
        self.customer = Customer.objects.get(id=data['customer']['id'])
        self.employee = user
        self.set_delivery_date(data['delivery_date'])
        if "vat" in data:
            self.vat = int(data["vat"])
        if "po_id" in data:
            self.po_id = data["po_id"]
        if "remarks" in data:
            self.remarks = data["remarks"]
        self.status = 'ACKNOWLEDGED'
        self.save()
        #Set products information
        for product_data in data['products']:
            self.set_product(product_data)
        #Calculate totals
        self.calculate_totals()
        self.save()
        #Insert into the previous database
        #self.insert_into_old_db()
        #Initialize and create pdf
        ack_filename, production_filename = self.create_pdfs()
        #Upload and return the url
        self.upload_acknowledgement(ack_filename)
        self.upload_production(production_filename)
        #Email if decoroom
        if "decoroom" in self.customer.name.lower():
            self.email_decoroom()
        self.create_log("Ack# {0} Created", self.delivery_date, self.employee)
        urls = {'production_url': self.get_url(self.production_key),
                'acknowledgement_url': self.get_url(self.acknowledgement_key)}
        return urls

    def update(self, data, employee=None):
        print data["delivery_date"]
        if "delivery_date" in data:
            self.set_delivery_date(data["delivery_date"], employee=employee)
        self.save()
        """ack_filename, production_filename = self.create_pdfs()
        #Upload and return the url

        ack_key = self.upload(ack_filename, 'Acknowledgement', appendix='-revision')
        production_key = self.upload(production_filename, 'Production', appendix='-revision')
        #Email if decoroom
        urls = {'production_url': self.get_url(production_key),
                'acknowledgement_url': self.get_url(ack_key)}
        return urls"""
        return {}

    def create_pdfs(self):
        products = self.item_set.all().order_by('id')
        ack_pdf = AcknowledgementPDF(customer=self.customer, ack=self,
                                     products=products)
        ack_filename = ack_pdf.create()
        production_pdf = ProductionPDF(customer=self.customer, ack=self,
                                       products=products)
        production_filename = production_pdf.create()
        return ack_filename, production_filename

    def create_log(self, action, delivery_date=None, employee=None):
        log = AcknowledgementLog()
        log.acknowledgement = self
        if employee is not None:
            log.employee = employee
        else:
            log.employee = self.employee
        if delivery_date is None:
            log.delivery_date = self.delivery_date
        else:
            log.delivery_date = delivery_date
        log.action = action
        log.save()

    def set_delivery_date(self, delivery_date, employee=None):
        """This function sets the delivery date and then
        conditionally performs additional actions if the
        delivery_date has been previously set."""
        delivery_date = dateutil.parser.parse(delivery_date)
        if self.delivery_date != None:
            action = "Change Delivery Date to {0}".format(delivery_date.strftime('%B %d, %Y'))
            self.create_log(action, delivery_date, employee=employee)

        self.delivery_date = delivery_date

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
        discount = (Decimal(self.discount) / 100) * running_total
        running_total -= discount
        vat = (Decimal(self.vat) / 100) * running_total
        running_total += vat
        self.total = running_total

    #Get the correct product based on type
    def get_product(self, product_data):
        if product_data["type"] == "Upholstery":
            return Upholstery.objects.get(product_ptr_id=product_data["id"])

    def email(self, key, recipients):
        key_id = settings.AWS_ACCESS_KEY_ID
        access_key = settings.AWS_SECRET_ACCESS_KEY
        conn = boto.ses.connect_to_region('us-east-1',
                                          aws_access_key_id=key_id,
                                          aws_secret_access_key=access_key)
        body = u"""<table width="500" cellpadding="3" cellspacing="0">
                      <tr>
                          <td style="border-bottom-width:1px; border-bottom-style:solid; border-bottom-color:#777" width="70%"> 
                              <a href="http://www.dellarobbiathailand.com"><img height="30px" src="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/DRLogo.jpg"></a> 
                          </td>
                          <td style="border-bottom-width:1px; border-bottom-style:solid; border-bottom-color:#777; color:#777; font-size:14px" width="30%" align="right" valign="bottom">Order Received</td> 
                      </tr>
                      <tr>
                          <td width="500" colspan="2">
                          <br />
                          <br />
                          <p> Dear {customer},
                          <br />
                          <br /> Thank you for placing an order with us. Here are the details of your order, for your conveniece: 
                          <br />
                          <br />
                          <table cellpadding="3" cellspacing="0" width="500">
                              <tr>
                                  <td align="left"> <b style="color:#000">Order Number:</b></td>
                                  <td align="right"> <b>{id}</b> </td>
                              </tr>
                              <tr>
                                  <td align="left">
                                      <b style="color:#000">Acknowledgement:</b>
                                  </td>
                                  <td align="right">
                                      <a href="{src}">View Your Acknowledgement(Link Valid for 72 Hours)</a>
                                  </td>
                              </tr>
                              <tr>
                                  <td align="left"> <b style="color:#000">Estimated Delivery Date:</b>
                                  </td>
                                  <td align="right"> <b>{delivery_date}</b>
                                  </td>
                              </tr>
                          </table>
                          <br />
                          <br />
                          If you have any questions, comments or concerns, please don\'t hesistate to
                          <a href="info@dellarobbiathailand.com">contact us</a>.
                          <br />
                          <br /> Sincerely,
                          <br />The Dellarobbia Customer Service Team
                      </p>
                  </td>
              </tr>
          </table>""".format(id=self.id, customer=self.customer.name,
                             src=self.get_url(key, 259200),
                             delivery_date=self.delivery_date.strftime('%B %d, %Y'))

        conn.send_email('no-replay@dellarobbiathailand.com', 
                        'Acknowledgement of Order Placed',
                        body,
                        recipients,
                        format='html')

    def email_decoroom(self):
        self.email(self.acknowledgement_key, ['praparat@decoroom.com'])
        self.email(self.production_key, ['sales@decoroom.com'])

    #Get the Url of the document
    def get_url(self, key, time=1800):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(time, 'GET', bucket=self.bucket, key=key, force_http=True)
        #return the url
        return url

    #uploads the pdf
    def upload(self, filename, file_type, appendix='', *args, **kwargs):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                            settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = "acknowledgement/{0}-{1}{2}.pdf".format(file_type, self.id,
                                                        appendix)
        #upload file and set acl
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        #Remove original
        os.remove(filename)
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        return k.key

    def upload_acknowledgement(self, filename, *args, **kwargs):
        self.acknowledgement_key = self.upload(filename, "Acknowledgement", *args, **kwargs)
        self.save()

    def upload_production(self, filename, *args, **kwargs):
        self.production_key = self.upload(filename, "Production", *args, **kwargs)
        self.save()


#Create the Acknowledgement Items
class Item(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement)
    product = models.ForeignKey(Product)
    type = models.CharField(max_length=20)
    #Price not including discount
    quantity = models.IntegerField(null=False)
    unit_price = models.DecimalField(null=True, max_digits=15,
                                     decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    fabric = models.ForeignKey(Fabric)
    fabric_description = models.TextField(default=None)
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size',
                                         default=False)
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
            if "quantity" in data:
                self.quantity = int(data["quantity"])

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
        if price is None:
            price = 0
        #Set the unit price then total
        self.unit_price = price
        self.total = self.unit_price * Decimal(self.quantity)
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
        if "comments" in data:
            self.comments = data["comments"]
        #Set dimensions
        if "is_custom_size" in data:
            if data["is_custom_size"] == True:
                self.is_custom_size = True
                #Checks if data is greater than 0
                if "width" in data and data['width'] > 0:
                    self.width = int(data['width'])
                if "depth" in data and data['depth'] > 0:
                    self.depth = int(data['depth'])
                if "height" in data and data['height'] > 0:
                    self.height = int(data['height'])
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
                    if "quantity" not in pillow:
                        pillow["quantity"] = 1
                    pillows.append(pillow)
            #Get pillows
            for pillow in pillows:
                ack_pillow = Pillow()
                ack_pillow.item = self
                ack_pillow.type = pillow["type"]
                ack_pillow.quantity = pillow["quantity"] * self.quantity
                fabric_id = pillow["fabric"]["id"]
                ack_pillow.fabric = Fabric.objects.get(id=fabric_id)
                ack_pillow.save()

    def get_data(self):
        data = {'id': self.id,
                'is_custom_size': self.is_custom_size,
                'width': self.width,
                'height': self.height,
                'depth': self.depth,
                'description': self.description,
                'comments': self.comments,
                'quantity': self.quantity,
                'pillows': [],
                'image': {'url': self._get_image_url()}}
        for pillow in self.pillow_set.all():
            data["pillows"].append(pillow.get_data())
        try:
            data.update({'fabric': {'fabric': self.fabric.description,
                                    'image': {'url': self.fabric.image_url}}})
        except:
            pass
        return data

    def _get_image_url(self):
        if self.bucket is not None and self.image_key is not None:

            conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                                settings.AWS_SECRET_ACCESS_KEY)
            url = conn.generate_url(1800, 'GET', bucket=self.bucket,
                                    key=self.image_key, force_http=True)
        else:
            url = None
        return url


#Pillows for Acknowledgement items
class Pillow(models.Model):
    item = models.ForeignKey(Item)
    type = models.CharField(db_column="type", max_length=10, null=True)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric)

    def get_data(self):
        data = {'type': self.type,
                'quantity': self.quantity}
        try:
            data.update({'fabric': {'description': self.fabric.description,
                                    'image': {'url': self.fabric.image_url}}})
        except:
            pass
        return data


class AcknowledgementLog(Log):
    acknowledgement = models.ForeignKey(Acknowledgement)
    delivery_date = models.DateTimeField()



