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
from auth.models import Log, S3Object


class Acknowledgement(models.Model):
    po_id = models.TextField(default=None, null=True)
    discount = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    time_created = models.DateTimeField(auto_now_add=True)
    _delivery_date = models.DateTimeField(db_column='delivery_date')
    status = models.TextField()
    production_key = models.TextField(null=True)
    acknowledgement_key = models.TextField(null=True)
    original_acknowledgement_key = models.TextField(null=True)
    bucket = models.TextField(null=True)
    remarks = models.TextField()
    fob = models.TextField(null=True)
    shipping_method = models.TextField(null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    vat = models.IntegerField(default=0, null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    acknowledgement_pdf = models.ForeignKey(S3Object,
                                            null=True,
                                            related_name='+',
                                            db_column="acknowledgement_pdf")
    production_pdf = models.ForeignKey(S3Object,
                                       null=True,
                                       related_name='+',
                                       db_column="production_pdf")
    original_acknowledgement_pdf = models.ForeignKey(S3Object,
                                                     null=True,
                                                     related_name='+',
                                                     db_column="original_acknowledgement_pdf")

    @property
    def delivery_date(self):
        return self._delivery_date

    @delivery_date.setter
    def delivery_date(self, new_date):
        """
        Sets the delivery date and logs it.

        The setter will change the current delivery date,
        log the change, and change the delivery item if
        the new date is now the same as the current delivery
        date
        """
        bkk_tz = timezone('Asia/Bangkok')
        try:
            delivery_date = new_date.astimezone(bkk_tz)
        except:
            delivery_date = dateutil.parser.parse(new_date).astimezone(bkk_tz)

        if self._delivery_date == None:
            self._delivery_date = delivery_date
        elif delivery_date != self._delivery_date.astimezone(bkk_tz):
            old_delivery_date = self._delivery_date
            self._delivery_date = delivery_date

        try:
            employee = self.current_employee
        except:
            employee = self.employee
        #Log the information as a change or set
        if self.id:
            try:
                message = "Delivery Date for Acknowledgement# {0} set to {1}"
                message.format(self.id, delivery_date.strftime('%B %d, %Y'))
            except:
                message = """Delivery Date for Acknowledgement# {0}
                             changed from {1} to {2}"""
                message.format(self.id,
                               old_delivery_date.strftime('%B %d, %Y'),
                               delivery_date.strftime('%B %d, %Y'))
            AcknowledgementLog.create(message, self, employee)

    @classmethod
    def create(cls, user, **kwargs):
        """Creates the acknowledgement

        This method accept data to set and then creates
        an accompanying PDF and logs the event. A User
        Object is required to authorize certain data
        """
        acknowledgement = cls()
        acknowledgement.customer = Customer.objects.get(id=kwargs['customer']['id'])
        acknowledgement.employee = user

        acknowledgement.delivery_date = dateutil.parser.parse(kwargs['delivery_date'])
        acknowledgement.status = 'ACKNOWLEDGED'
        try:
            acknowledgement.vat = int(kwargs["vat"])
        except KeyError:
            acknowledgement.vat = 0
        try:
            acknowledgement.po_id = kwargs["po_id"]
        except KeyError:
            raise AttributeError("Missing Purchase Order number.")
        try:
            acknowledgement.remarks = kwargs["remarks"]
        except KeyError:
            pass
        #Create the products without saving
        acknowledgement.items = [Item.create(acknowledgement=acknowledgement,
                                             commit=False,
                                             **product_data) for product_data in kwargs['products']]

        acknowledgement.calculate_totals(acknowledgement.items)
        
        #Save the ack and by overriden method, the items
        acknowledgement.save()

        #Log creation of the acknowledgement
        AcknowledgementLog.create("Ack# {0} Created".format(acknowledgement.id),
                                    acknowledgement,
                                    acknowledgement.employee)

        #Create the order PDFs
        ack, production = acknowledgement._create_pdfs()
        ack_key = "acknowledgement/Acknowledgement-{0}.pdf".format(acknowledgement.id)
        production_key = "acknowledgement/Production-{0}.pdf".format(acknowledgement.id)
        bucket = "document.dellarobbiathailand.com"
        ack_pdf = S3Object.create(ack, ack_key, bucket, encrypt_key=True)
        prod_pdf = S3Object.create(production, production_key, bucket, encrypt_key=True)
        acknowledgement.acknowledgement_pdf = ack_pdf
        acknowledgement.production_pdf = prod_pdf
        acknowledgement.original_acknowledgement_pdf = ack_pdf

        #Save Ack with pdf data
        acknowledgement.save()

        #Email decoroom
        if "decoroom" in acknowledgement.customer.name.lower():
            acknowledgement._email_decoroom()
        return acknowledgement

    def update(self, data=None, employee=None):
        """"Updates the acknowledgement

        Updates the acknowledgement with the new data
        and creates a new pdf for acknowledgement and production
        """
        self.current_employee = employee
        try:
            self.delivery_date = data["delivery_date"]
            self.save()
        except:
            pass

        self.calculate_totals()

        ack_filename, production_filename = self._create_pdfs()
        ack_key = "acknowledgement/Acknowledgement-{0}-revision.pdf".format(self.id)
        production_key = "acknowledgement/Production-{0}-revision.pdf".format(self.id)
        bucket = "document.dellarobbiathailand.com"
        ack_pdf = S3Object.create(ack_filename, ack_key, bucket)
        prod_pdf = S3Object.create(production_filename, production_key, bucket)

        self.acknowledgement_pdf = ack_pdf
        self.production_pdf = prod_pdf

        self.save()

    def ship(self, delivery_date, employee):
        """Changes status to 'SHIPPED'

        Change the order status to ship and logs who ships it
        """
        try:
            message = "Ack# {0} shipped on {1}".format(self.id, delivery_date.strftime('%B %d, %Y'))
        except AttributeError:
            raise TypeError("Missing Delivery Date")

        AcknowledgementLog.create(message, self.acknowledgement, employee)

    def to_dict(self):
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
                'customer': self.customer.to_dict(),
                'employee': u'{0} {1}'.format(self.employee.first_name, self.employee.last_name),
                'products': [item.to_dict() for item in self.item_set.all().order_by('id')]}

        return data

    def generate_url(self, file_type, expires=1800):
        """Generates an url for the file type"""
        if file_type.lower() == "acknowledgement":
            return self.acknowledgement_pdf.generate_url()
        elif file_type.lower() == "production":
            return self.production_pdf.generate_url()

    def save(self):
        super(Acknowledgement, self).save()
        for item in self.items:
            item.acknowledgement = self
            item.save()

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

    def calculate_totals(self, items=None):
        """Calculates the total of the order

        Uses the items argument to calculate the cost
        of the project. If the argument is null then the
        items are pulled from the database relationship.
        We use the argument first in the case of where
        we are creating a new Acknowledgement, and the
        items and acknowledgement have not yet been saved
        """
        running_total = 0

        #Define items if not already defined
        if not items:
            items = self.item_set.all()
        for product in items:
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

    def _email(self, pdf, recipients):
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
                             src=pdf.generate_url(),
                             delivery_date=self.delivery_date.strftime('%B %d, %Y'))

        conn.send_email('no-replay@dellarobbiathailand.com',
                        'Acknowledgement of Order Placed',
                        body,
                        recipients,
                        format='html')

    def _email_decoroom(self):
        """Emails decoroom"""
        self._email(self.acknowledgement_pdf, ['praparat@decoroom.com'])
        self._email(self.production_pdf, ['sales@decoroom.com'])


class Item(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement, null=True)
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
    location = models.TextField(null=True)
    image = models.ForeignKey(S3Object, null=True)

    @classmethod
    def create(cls, acknowledgement=None, commit=True, **kwargs):
        """Creates an Item"""
        item = cls()
        item.acknowledgement = acknowledgement

        try:
            item.product = Product.objects.get(id=kwargs["id"])
        except:
            item.product = Product.objects.get(id=10436)
        item.status = "ACKNOWLEDGED"

        try:
            item.quantity = int(kwargs["quantity"])
        except KeyError:
            raise AttributeError("Missing Quantity.")

        item._apply_product_data()
        item._apply_data(**kwargs)

        #Save the item if commit is true
        if commit:
            item.save()

        return item

    def update(self, data, employee):
        """Updates an item"""
        if "fabric" in data:
            fabric = Fabric.objects.get(id=data["fabric"]["id"])
            if fabric != self.fabric:
                if self.fabric:
                    message = "Change fabric from {0} to {1}".format(self.fabric.description, fabric.description)
                else:
                    message = "Change fabric to {0}".format(fabric.description)
                self.fabric = fabric
                AcknowledgementLog.create(message, self.acknowledgement, employee)
        if "pillows" in data:
            for pillow_data in data["pillows"]:
                pillow = Pillow.objects.get(id=pillow_data["id"])
                fabric = Fabric.objects.get(id=pillow_data["fabric"]["id"])
                pillow.fabric = fabric
                pillow.save()
        if "status" in data:
            if data["status"] != self.status:
                self.status = data["status"]
                try:
                    message = "Item# {0} from Acknowledgement #{1} has been {2} due to:{3}".format(self.id, 
                                                                                                    self.acknowledgement.id, 
                                                                                                    self.status,
                                                                                                    data['status_message'])
                except:
                    message = "Item# {0} from Acknowledgement #{1} has been {2}".format(self.id, 
                                                                                         self.acknowledgement.id, 
                                                                                         self.status)
                AcknowledgementLog.create(message, self.acknowledgement, employee)

        self.save()

    def save(self):
        """
        Saves the object
        
        This method first saves the object, and then saves any unsaved pillows
        via the pillow attribute
        """
        super(Item, self).save()
        try:
            for pillow in self.pillows:
                pillow.item = self
                pillow.save()
        except AttributeError:
            pass

    def ship(self, delivery_date, employee):
        status = 'SHIPPED'
        message = "Ack Item# {0}({1}) shipped on {2}".format(self.id, self.description, delivery_date.strftime(''))
        AcknowledgementLog.create(message, self.acknowledgement, employee)

    def to_dict(self):
        """Retrieves data about the item"""
        data = {'id': self.id,
                'acknowledgement': {'id': self.acknowledgement.id},
                'is_custom_size': self.is_custom_size,
                'width': self.width,
                'height': self.height,
                'depth': self.depth,
                'description': self.description,
                'comments': self.comments,
                'quantity': self.quantity,
                'pillows': [pillow.to_dict() for pillow in self.pillow_set.all()],
                'status': self.status}
        try:
                data['image'] = {'url': self.image.generate_url()}
        except AttributeError:
            pass

        if self.fabric:
            data.update({'fabric': {'id': self.fabric.id,
                                    'description': self.fabric.description,
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

        try:
            self.image = self.product.image
        except:
            pass

    def _apply_data(self, **kwargs):
        """Applies data to the attributes

        Requires a User to authenticate what can and
        cannot be applied"""
        if "comments" in kwargs:
            self.comments = kwargs["comments"]

        #Set the size of item if custom
        if "is_custom_size" in kwargs:
            if kwargs["is_custom_size"] == True:
                self.is_custom_size = True
                if "width" in kwargs and kwargs['width'] > 0 and kwargs["width"]:
                    self.width = int(kwargs['width'])
                if "depth" in kwargs and kwargs['depth'] > 0 and kwargs["depth"]:
                    self.depth = int(kwargs['depth'])
                if "height" in kwargs and kwargs['height'] > 0 and kwargs["height"]:
                    self.height = int(kwargs['height'])

        #Calculate the price of the item
        if "custom_price" in kwargs:
            self.unit_price = Decimal(kwargs["custom_price"])
            self.total = self.unit_price * Decimal(self.quantity)
        else:
            try:
                self._calculate_custom_price()
            except TypeError as e:
                print e 

        #Create a Item from a custom product
        if "is_custom" in kwargs:
            if kwargs["is_custom"] == True:
                self.is_custom_item = True
                self.description = kwargs["description"]
                if "image" in kwargs:
                    self.image = S3Object.objects.get(pk=kwargs["image"]["id"])
        if "fabric" in kwargs:
            try:
                self.fabric = Fabric.objects.get(pk=kwargs["fabric"]["id"])
            except Fabric.DoesNotExist as e:
                print "Error: {0} /Fabric: {1}".format(e, kwargs["fabric"]["id"])

        if "pillows" in kwargs:
            pillows = self._condense_pillows(kwargs["pillows"])
            self.pillows = [self._create_pillow(keys[0],
                                                pillows[keys],
                                                keys[1]) for keys in pillows]

            print pillows

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
        self.total = self.unit_price * self.quantity

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

        pillows = {}
        for pillow in pillows_data:
            try:
                pillows[(pillow["type"], pillow["fabric"]["id"])] += 1
            except KeyError:
                try:
                    pillows[(pillow["type"], pillow["fabric"]["id"])] = 1
                except KeyError:
                    try:
                        pillows[(pillow["type"], None)] += 1
                    except KeyError:
                        pillows[(pillow["type"], None)] = 1
        return pillows
    
    def _create_pillow(self, type, quantity, fabric_id=None):
        """
        Creates and returns a pillow
        
        This method will create a pillow. If there is a corresponding fabric
        it is added to the pillow, if not then the pillow is returned without one
        """
        try:
            return Pillow(item=self,
                          type=type,
                          quantity=quantity,
                          fabric=Fabric.objects.get(pk=fabric_id))
        except Fabric.DoesNotExist:
            return Pillow(item=self,
                          type=type,
                          quantity=quantity)

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
    type = models.CharField(db_column="type", max_length=10)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric, null=True)

    @classmethod
    def create(cls, **kwargs):
        """Creates a new pillow"""
        pillow = cls(**kwargs)
        pillow.save()
        return pillow

    def to_dict(self):
        """Gets all the pillow's data"""
        data = {'id': self.id,
                'type': self.type,
                'quantity': self.quantity}
        try:
            data.update({'fabric': {'id': self.fabric.id,
                                    'description': self.fabric.description,
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

    def to_dict(self):
        """Get the log data"""

        return {'event': self.event,
                'employee': "{0} {1}".format(self.employee.first_name, self.employee.last_name),
                'timestamp': self.timestamp.isoformat()}


class Delivery(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement, null=True)
    description = models.TextField()
    _delivery_date = models.DateTimeField()
    longitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    latitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    @property
    def delivery_date(self):
        return self._delivery_date

    @delivery_date.setter
    def delivery_date(self, new_date):
        self._delivery_date = new_date

    @classmethod
    def create(cls, **kwargs):
        delivery = cls(**kwargs)
        try:
            delivery.description = kwargs["description"]
            delivery.delivery_date = kwargs["delivery_date"]
        except:
            raise Exception("Missing required information")

        try:
            delivery.latitude = kwargs["latitude"]
            delivery.longitude = kwargs["longitude"]
        except:
            pass

        try:
            delivery.acknowledgement = kwargs["acknowledgement"]
        except:
            pass

        delivery.save()
        return delivery

    def to_dict(self):
        return {'id': self.id,
                'description': self.description,
                'delivery_date': self.delivery_date.isoformat()}
