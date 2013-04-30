import os
import dateutil.parser
import math
from decimal import Decimal

from pytz import timezone
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


class Acknowledgement(models.Model):
    po_id = models.TextField(default=None, null=True)
    discount = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    time_created = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField()
    status = models.TextField()
    production_key = models.TextField(null=True)
    acknowledgement_key = models.TextField(null=True)
    original_acknowledgement_key = models.TextField(null=True)
    bucket = models.TextField(null=True)
    remarks = models.TextField()
    fob = models.TextField(null=True)
    shipping_method = models.TextField(null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    vat = models.IntegerField(default=0, null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    @classmethod
    def create(cls, data, user):
        """Creates the acknowledgement

        This method accept data to set and then creates
        an accompanying PDF and logs the event. A User
        Object is required to authorize certain data
        """
        acknowledgement = cls()
        acknowledgement.customer = Customer.objects.get(id=data['customer']['id'])
        acknowledgement.employee = user
        acknowledgement.delivery_date = dateutil.parser.parse(data['delivery_date'])
        acknowledgement.status = 'ACKNOWLEDGED'
        if "vat" in data:
            acknowledgement.vat = int(data["vat"])
        if "po_id" in data:
            acknowledgement.po_id = data["po_id"]
        if "remarks" in data:
            acknowledgement.remarks = data["remarks"]
        acknowledgement.save()

        for product_data in data['products']:
            Item.create(product_data, acknowledgement=acknowledgement)

        acknowledgement.calculate_totals()
        acknowledgement.save()

        ack, production = acknowledgement._create_pdfs()
        a_key = acknowledgement._upload_acknowledgement(ack)
        p_key = acknowledgement._upload_production(production)
        acknowledgement.original_acknowledgement_key = a_key
        acknowledgement.save()

        AcknowledgementLog.create("Ack# {0} Created".format(acknowledgement.id),
                                    acknowledgement,
                                    acknowledgement.employee)

        if "decoroom" in acknowledgement.customer.name.lower():
            acknowledgement._email_decoroom()
        return acknowledgement

    def update(self, data=None, employee=None):
        """"Updates the acknowledgement

        Updates the acknowledgement with the new data
        and creates a new pdf for acknowledgement and production
        """
        if data:
            if "delivery_date" in data:
                self._set_delivery_date(data["delivery_date"], employee=employee)
            self.save()

        ack_filename, production_filename = self._create_pdfs()
        ack_key = self._upload(ack_filename, 'Acknowledgement', appendix='-revision')
        production_key = self._upload(production_filename, 'Production', appendix='-revision')

        self.acknowledgement_key = ack_key
        self.production_key = production_key
        self.save()

    def get_data(self):
        """Retrieves authorized information from the object.

        Requires User object to gain full access to the data.
        The method will then check if certain permissions are
        met before adding them to the outgoing data.
        """
        data = {'id': self.id,
                'delivery_date': self.delivery_date.isoformat(),
                'time_created': self.time_created.isoformat(),
                'status': self.status,
                'remarks': self.remarks,
                'fob': self.fob,
                'vat': self.vat,
                'shipping': self.shipping_method,
                'customer': self.customer.get_data(),
                'employee': u'{0} {1}'.format(self.employee.first_name, self.employee.last_name),
                'products': [item.get_data() for item in self.item_set.all().order_by('id')]}

        return data

    def generate_url(self, file_type, expires=1800):
        """Generates an url for the file type"""
        if file_type.lower() == "acknowledgement":
            return self._generate_url(self.acknowledgement_key, expires)
        elif file_type.lower() == "production":
            return self._generate_url(self.production_key, expires)

    def _set_delivery_date(self, delivery_date, employee=None):
        """Changes the delivery date.

        This function sets the delivery date and then
        conditionally performs additional actions if the
        delivery_date has been previously set.
        """
        bkk_tz = timezone('Asia/Bangkok')
        delivery_date = dateutil.parser.parse(delivery_date).astimezone(bkk_tz)
        if self.delivery_date != None:
            o_dd = self.delivery_date.astimezone(bkk_tz)
            dds = (o_dd.strftime('%B %d. %Y'),
                   delivery_date.strftime('%B %d, %Y'))
            event = "Change Delivery Date from {0} to {1}".format(*dds)
        else:
            event = "Delivery Date set to {0}".format(delivery_date.strftime('%B %d, %Y'))

        AcknowledgementLog.create(event, self, employee=employee)
        self.delivery_date = delivery_date

    def _create_pdfs(self):
        """Creates Production and Acknowledgement PDFs

        This method will extract the necessary data to 
        create the pdfs from the object itself. It requires
        no arguments
        """
        products = self.item_set.all().order_by('id')
        ack_pdf = AcknowledgementPDF(customer=self.customer, ack=self, products=products)
        production_pdf = ProductionPDF(customer=self.customer, ack=self, products=products)
        ack_filename = ack_pdf.create()
        production_filename = production_pdf.create()
        return ack_filename, production_filename

    def calculate_totals(self):
        running_total = 0
        for product in self.item_set.all():
            running_total += product.total
        self.subtotal = running_total
        discount = (Decimal(self.discount) / 100) * running_total
        running_total -= discount
        vat = (Decimal(self.vat) / 100) * running_total
        running_total += vat
        self.total = running_total

    def _change_fabric(self, product, fabric, employee=None):
        """Changes the fabric for a product

        Requires the product, the fabric and the employee performing
        the change. The event is logged using the provided employee
        """
        try:
            message = "Changed fabric from {0} to {1}".format(product.fabric.description, fabric.description)
        except:
            message = "Changed fabric to {0}".format(fabric.description)
        self._create_log(message, employee)
        product.fabric = fabric
        product.save()

    def _email(self, key, recipients):
        """Emails an order confirmation"""
        key_id = settings.AWS_ACCESS_KEY_ID
        access_key = settings.AWS_SECRET_ACCESS_KEY
        conn = boto.ses.connect_to_region('us-east-1', aws_access_key_id=key_id, aws_secret_access_key=access_key)
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
                             src=self._generate_url(key, 259200),
                             delivery_date=self.delivery_date.strftime('%B %d, %Y'))

        conn.send_email('no-replay@dellarobbiathailand.com',
                        'Acknowledgement of Order Placed',
                        body,
                        recipients,
                        format='html')

    def _email_decoroom(self):
        """Emails decoroom"""
        self._email(self.acknowledgement_key, ['praparat@decoroom.com'])
        self._email(self.production_key, ['sales@decoroom.com'])

    #Get the Url of the document
    def _generate_url(self, key, time=1800):
        """generate a url for the key"""
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(time, 'GET', bucket=self.bucket, key=key, force_http=True)
        #return the url
        return url

    #uploads the pdf
    def _upload(self, filename, file_type, appendix='', *args, **kwargs):
        """Uploads the file to the to our S3 service

        Requies the filename, the file type. if an Appendix is provided
        then the file is appended with that before the filetype.
        """
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        k = Key(bucket)
        k.key = "acknowledgement/{0}-{1}{2}.pdf".format(file_type, self.id, appendix)
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        os.remove(filename)
        self.bucket = "document.dellarobbiathailand.com"
        return k.key

    def _upload_acknowledgement(self, filename, *args, **kwargs):
        """Uploads the file as an acknowledgement

        Requires the filename. This method will upload the file and
        store it in the S3 service and the database as the acknowledgement
        """
        self.acknowledgement_key = self._upload(filename, "Acknowledgement", *args, **kwargs)
        return self.acknowledgement_key

    def _upload_production(self, filename, *args, **kwargs):
        """Uploads the file as an production

        Requires the filename. This method will upload the file and
        store it in the S3 service and the database as the production
        """
        self.production_key = self._upload(filename, "Production", *args, **kwargs)
        return self.production_key


class Item(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement)
    product = models.ForeignKey(Product)
    type = models.CharField(max_length=20)
    quantity = models.IntegerField(null=False)
    unit_price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    fabric = models.ForeignKey(Fabric, null=True)
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size', default=False)
    is_custom_item = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    bucket = models.TextField(null=True)
    image_key = models.TextField(null=True)
    comments = models.TextField(null=True)

    @classmethod
    def create(cls, data, acknowledgement, **kwargs):
        """Creates an Item"""
        item = cls(**kwargs)
        item.acknowledgement = acknowledgement
        try:
            item.product = Product.objects.get(id=data["id"])
        except:
            item.product = Product.objects.get(id=10436)
        item.status = "ACKNOWLEDGED"
        try:
            item.quantity = data["quantity"]
        except KeyError:
            raise Exception
        item._apply_product_data()
        item._apply_data(data)
        item.save()
        return item

    def update(self, data, employee):
        """Updates an item"""
        if "fabric" in data:
            fabric = Fabric.objects.get(id=data["fabric"]["id"])
            try:
                message = "Change fabric from {0} to {1}".format(self.fabric, fabric)
            except Exception:
                message = "Change fabric to {0}".format(fabric)
            self.fabric = fabric
            AcknowledgementLog.create(message, self.acknowledgement, employee)

    def get_data(self):
        """Retrieves data about the item"""
        data = {'id': self.id,
                'is_custom_size': self.is_custom_size,
                'width': self.width,
                'height': self.height,
                'depth': self.depth,
                'description': self.description,
                'comments': self.comments,
                'quantity': self.quantity,
                'pillows': [pillow.get_data() for pillow in self.pillow_set.all()],
                'status': self.status,
                'image': {'url': self._get_image_url()}}
        if self.fabric:
            data.update({'fabric': {'fabric': self.fabric.description,
                                    'image': {'url': self.fabric.image_url}}})
        return data

    def _apply_product_data(self):
        """Applies data from the set product

        Requires no arguments. The data is extracted
        from the product referenced by the item
        """
        self.description = self.product.description
        if self.acknowledgement.customer.type == "Retail":
            self.unit_price = self.product.retail_price
        elif self.acknowledgement.customer.type == "Dealer":
            self.unit_price = self.product.wholesale_price
        else:
            self.unit_price = self.product.retail_price

        self.total = self.unit_price * Decimal(self.quantity)

        self.width = self.product.width
        self.depth = self.product.depth
        self.height = self.product.height

        self.bucket = self.product.bucket
        self.image_key = self.product.image_key
        self.save()

    def _apply_data(self, data):
        """Applies data to the attributes

        Requires a User to authenticate what can and
        cannot be applied"""
        if "comments" in data:
            self.comments = data["comments"]

        if "is_custom_size" in data:
            if data["is_custom_size"] == True:
                self.is_custom_size = True
                if "width" in data and data['width'] > 0:
                    self.width = int(data['width'])
                if "depth" in data and data['depth'] > 0:
                    self.depth = int(data['depth'])
                if "height" in data and data['height'] > 0:
                    self.height = int(data['height'])
                self._calculate_custom_price()

        if "is_custom" in data:
            if data["is_custom"] == True:
                self.is_custom_item = True
                self.description = data["description"]

                if "image" in data:
                    self.image_key = data["image"]["key"]
                    self.bucket = data["image"]["bucket"]

        if "fabric" in data:
            self.fabric = Fabric.objects.get(id=data["fabric"]["id"])

        if "pillows" in data:
            pillows = self._condense_pillows(data["pillows"])
            for pillow in pillows:
                try:
                    pillow = Pillow.create(item=self, type=pillow["type"],
                                           quantity=pillow["quantity"] * self.quantity,
                                           fabric=Fabric.objects.get(id=pillow["fabric"]["id"]))
                except KeyError:
                    print "Missing type or quantity"
                except Fabric.DoesNotExist:
                    pillow = Pillow.create(item=self, type=pillow["type"],
                                           quantity=pillow["quantity"] * self.quantity)

    def _calculate_custom_price(self):
        """Caluates the custom price based on dimensions."""
        dimensions = {'width_difference': self.width - self.product.width,
                      'depth_difference': self.depth - self.product.depth,
                      'height_difference': self.height - self.product.height}
        if self.product.collection == "Dellarobbia Thailand":
            upcharge_percentage = sum(self._calculate_upcharge(dimensions[key], 150, 10, 1) for key in dimensions)
        elif self.product.collection == "Dwell Living":
            upcharge_percentage = sum(self._calculate_upcharge(dimensions[key], 150, 5, 1) for key in dimensions)
        else:
            upcharge_percentage = 0
        self.unit_price = self.unit_price + (self.unit_price * (Decimal(upcharge_percentage) / 100))

    def _calculate_upcharge(self, difference, boundary, initial, increment):
        """Returns the correct upcharge percentage as a whole number

        >>>self._calculate_upcharge(100, 150, 10, 1)
        10
        """
        if difference > 0:
            upcharge_percentage = initial + sum(increment for i in xrange(int(math.ceil(float(difference - boundary) / 50))))
            return upcharge_percentage
        else:
            return 0

    def _condense_pillows(self, pillows_data):
        """Removes the duplicate pillows from the data and condenses it.

        Duplicates pillows are added together and the duplicates are removed
        with the presence reflected in the quantity of a single pillow
        """
        pillows = []
        for pillow in pillows_data:
            for i, item in enumerate(pillows):
                if item["type"] == pillow["type"] and item["fabric"]["description"] == pillow["fabric"]["description"]:
                        pillows[i]["quantity"] += 1
                        break
            else:
                if "quantity" not in pillow:
                    pillow["quantity"] = 1
                pillows.append(pillow)
        return pillows

    def _get_image_url(self):
        """Gets the item's default image."""
        try:
            conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                                settings.AWS_SECRET_ACCESS_KEY)
            url = conn.generate_url(1800, 'GET', bucket=self.bucket,
                                    key=self.image_key, force_http=True)
            return url
        except Exception:
            return None


class Pillow(models.Model):
    item = models.ForeignKey(Item)
    type = models.CharField(db_column="type", max_length=10, null=True)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric)

    @classmethod
    def create(cls, **kwargs):
        """Creates a new pillow"""
        pillow = cls(**kwargs)
        pillow.save()
        return pillow

    def get_data(self):
        """Gets all the pillow's data"""
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

    @classmethod
    def create(cls, event, acknowledgement, employee):
        """Creates an acknowlegement log"""
        log = cls(event=event, acknowledgement=acknowledgement,
                  employee=employee)
        log.save()
        return log

    def get_data(self):
        """Get the log data"""
        
        return {'event': self.event,
                'employee': "{0} {1}".format(self.employee.first_name, self.employee.last_name),
                'timestamp': self.timestamp.isoformat()}
