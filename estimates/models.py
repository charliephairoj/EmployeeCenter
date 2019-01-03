import os
import dateutil.parser
import math
import logging
from decimal import *
from datetime import datetime

from pytz import timezone
from django.conf import settings
from django.db import models
from administrator.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto.ses

from contacts.models import Customer
from products.models import Product, Upholstery
from projects.models import Project
from supplies.models import Fabric
from estimates.PDF import EstimatePDF
from media.models import Log, S3Object
from acknowledgements.models import Acknowledgement
from deals.models import Event, Deal


logger = logging.getLogger(__name__)


class Estimate(models.Model):
    po_id = models.TextField(default=None, null=True)
    company = models.TextField(default="Alinea Group")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, related_name='quotations')
    employee = models.ForeignKey(User, db_column='employee_id', on_delete=models.PROTECT, null=True)
    time_created = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(db_column='delivery_date', null=True, default=datetime.now())
    status = models.TextField(default='ACKNOWLEDGED', db_column='status')
    remarks = models.TextField(default='', blank=True)
    fob = models.TextField(default="Bangkok", blank=True)
    shipping_method = models.TextField(default="Truck", blank=True)
    
    project = models.ForeignKey(Project, null=True, related_name='estimates')
    last_modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    pdf = models.ForeignKey(S3Object, null=True, related_name='+')
    files = models.ManyToManyField(S3Object, through="File", related_name="quotations")
    acknowledgement = models.OneToOneField(Acknowledgement, null=True, related_name="quotation")
    deal = models.ForeignKey(Deal, null=True, related_name="quotations")

    # Order Terms
    currency = models.TextField(default='THB')
    lead_time = models.TextField(default="4 weeks")
    deposit = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # VATs
    vat = models.IntegerField(default=0)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    #Discounts
    discount = models.IntegerField(default=0)
    second_discount = models.IntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    second_discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    #Totals
    # Totals of item totals
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after first discount
    post_discount_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after second Discount
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after all discounts and Vats
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # To Be Deprecated
    """
    @property
    def delivery_date(self):
        return self._delivery_date
    
    @delivery_date.setter
    def delivery_date(self, value):
        self._delivery_date = value
    """
    
    def delete(self):
        """
        Overrides the standard delete method.
        
        This method will simply make the acknowledgement as deleted in
        the database rather an actually delete the record
        """
        self.deleted = True
    
    def create_and_update_deal(self, employee=None):
        """
        Create a new deal based on the 
        """
        employee = employee or self.employee
        # Check that a deal for this estimate does not already exist
        if self.deal:
            deal = self.deal
        else:
            # Create description string
            description = u"{0}".format(self.customer.name)
            if self.project and self.project.codename:
                description += u" - {0}".format(self.project.codename)

            deal = Deal.objects.create(customer=self.customer,
                                        currency=self.customer.currency,
                                        status='proposal',
                                        description=description,
                                        total=self.total,
                                        employee=employee)

            self.deal = deal
            self.save()

            event = Event.objects.create(deal=deal,
                                         description="Quotation created")

        data = {
            'description': description,
            'customer': self.customer,
            'currency': self.customer.currency or 'THB',
            'total': self.total,
            'status': 'proposal'
        }

        return deal

    def create_and_upload_pdf(self, delete_original=True):
        ack_filename = self.create_pdf()
        ack_key = "estimate/{0}/Quotation-{0}.pdf".format(self.id)
        
        bucket = "document.dellarobbiathailand.com"
        ack_pdf = S3Object.create(ack_filename, ack_key, bucket, delete_original=delete_original)
        
        self.pdf = ack_pdf

        self.save()
        
    def create_pdf(self):
        """Creates Production and Acknowledgement PDFs

        This method will extract the necessary data to 
        create the pdfs from the object itself. It requires
        no arguments
        """
        products = self.items.exclude(deleted=True).order_by('description')
        estimate_pdf = EstimatePDF(customer=self.customer, estimate=self, products=products)
        estimate_filename = estimate_pdf.create()
        
        return estimate_filename

    def calculate_totals(self, items=None):
        #Define items if not already defined
        if not items:
            items = self.items.exclude(deleted=True)

        totals = self._calculate_totals(items)

        # Totals
        self.subtotal = totals['subtotal']
        self.post_discount_total = totals['post_discount_total']
        self.total = totals['total']
        self.grand_total = totals['grand_total']

        # VAT
        self.vat_amount = totals['vat_amount']
        self.second_discount_amount = totals['second_discount_amount']

        # Discounts
        self.discount_amount = totals['discount_amount']
        self.second_discount_amount = totals['second_discount_amount']

        self.save()

    def _calculate_totals(self, items=None):
        """Calculates the total of the order

        Uses the items argument to calculate the cost
        of the project. If the argument is null then the
        items are pulled from the database relationship.
        We use the argument first in the case of where
        we are creating a new Acknowledgement, and the
        items and acknowledgement have not yet been saved
        """
        # Totals
        # Total of items totals
        subtotal = 0
        # Total after discount        
        post_discount_total = 0
        # Total after second discount
        total = 0
        # Total after Vat
        grand_total = 0

        # Running total to check
        running_total = 0

        # Discount amounts
        # First Discount
        discount_amount = 0
        # Second Amount
        second_discount_amount = 0

        # Calculations
        # Calculate the subtotal
        for product in items:
            logger.debug("item: {0:.2f} x {1} = {2:.2f} + ".format(product.unit_price, product.quantity, product.total))
            subtotal += product.total

        # Set running_total to subtotal
        running_total += subtotal
            
        # Set the subtotal
        logger.debug("subtotal: = {0:.2f}".format(running_total))
        
        if subtotal == 0:
            return {
                'subtotal': 0,
                'post_discount_total': 0,
                'total': 0,
                'grand_total': 0,
                'vat_amount': 0,
                'discount_amount': 0,
                'second_discount_amount': 0
            }


        # Calculate discount
        discount_amount = (Decimal(self.discount) / 100) * subtotal
        logger.debug("discount {0}%: - {1:.2f}".format(self.discount, discount_amount))

        # Assert Discount amount is proportional to subtotal percent
        assert (discount_amount / subtotal) == Decimal(self.discount) / 100, "{0}: {1}".format((discount_amount / subtotal), Decimal(self.discount) / 100)

        # Apply discount
        post_discount_total = subtotal - discount_amount
        running_total -= discount_amount

        # Assert Discounted amount is proportional to discount and subtotal
        assert post_discount_total == running_total
        assert (post_discount_total / subtotal) == ((100 - Decimal(self.discount)) / 100)

        # Calculate a second discount
        second_discount_amount = (Decimal(self.second_discount) / 100) * post_discount_total
        logger.debug("second discount {0}%: - {1:.2f}".format(self.second_discount, second_discount_amount))
        
        # Assert second discount amount is proportional to total percent
        assert (second_discount_amount / post_discount_total) == Decimal(self.second_discount) / 100
        # Assert second discount amount is not proportional to total percent
        if self.second_discount > 0:
            assert (second_discount_amount / subtotal) != Decimal(self.second_discount) / 100

        # Apply second discount
        total = post_discount_total - second_discount_amount
        running_total -= second_discount_amount
        logger.debug("total: = {0:.2f}".format(total))

        # Assert total is proportional to subtotal
        assert total == running_total
        tpart1 = (total / subtotal)
        tpart2 = 1 - (Decimal(self.discount) / 100) 
        tpart2 = tpart2 - ((Decimal(self.discount) / 100) * (Decimal(self.second_discount) / 100))
        assert tpart2 > 0 and tpart2 <= 1
        assert tpart1 == tpart2, "{0}: {1}".format(tpart1, tpart2)
        if self.second_discount > 0:
            t2part1 = (total / subtotal)
            t2part2 = 1 - (Decimal(self.discount) / 100) 
            t2part2 = tpart2 - (Decimal(self.second_discount) / 100)
            assert t2part2 > 0 and t2part2 <= 1
            assert t2part1 != t2part2

        
        #Calculate VAT
        vat_amount = (Decimal(self.vat) / 100) * total
        logger.debug("vat: + {0:.2f}".format(vat_amount))

        # Assert VAT
        assert (vat_amount / total) == (Decimal(self.vat) / 100)

        # Apply VAT
        grand_total = total + vat_amount
        running_total += vat_amount
        logger.debug("grand total: = {0:.2f}".format(grand_total))

        # Assert second discounted amount is proportional to discount and total
        assert grand_total == running_total
        assert (grand_total / total) == Decimal('1') + (Decimal(self.vat) / 100)
        assert grand_total == (subtotal - discount_amount - second_discount_amount + vat_amount)

        return {
            'subtotal': subtotal,
            'post_discount_total': post_discount_total,
            'total': total,
            'grand_total': grand_total,
            'vat_amount': vat_amount,
            'discount_amount': discount_amount,
            'second_discount_amount': second_discount_amount
        }

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
        conn = boto.ses.connect_to_region('us-east-1')
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



class File(models.Model):
    estimate = models.ForeignKey(Estimate)
    file = models.ForeignKey(S3Object, related_name='quotation_files')
 
    
class Item(models.Model):
    estimate = models.ForeignKey(Estimate, related_name="items")
    product = models.ForeignKey(Product, null=True, related_name="estimate_item_product")
    type = models.TextField(null=True, blank=True)
    fabric = models.ForeignKey(Fabric, null=True, related_name="estimate_item_fabric")
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size', default=False)
    is_custom_item = models.BooleanField(default=False)
    status = models.TextField(default="open")
    comments = models.TextField(default="", blank=True)
    location = models.TextField(default="", blank=True)
    image = models.ForeignKey(S3Object, null=True, related_name="estimate_item_image")
    deleted = models.BooleanField(default=False)
    inventory = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)

    # Dimensions
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.TextField(default='mm')

    # Price Related
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(default=0, max_digits=15, decimal_places=2)
    total = models.DecimalField(default=0, max_digits=15, decimal_places=2)

    class Meta:
        permissions = (('change_item_price', 'Can edit item price'),
                       ('change_fabric', "Can change fabric"))

    @classmethod
    def create(cls, estimate=None, commit=True, **kwargs):
        """Creates an Item"""
        item = cls()
        item.estimate = estimate
        try:
            item.product = Product.objects.get(id=kwargs["id"])
            logger.info(u"Item set to {0}...".format(item.product.description))
        except KeyError:
            try:
                item.product = Product.objects.get(id=kwargs["product"]["id"])
            except KeyError:
                item.product = Product.objects.get(id=10436)
        except Product.DoesNotExist:
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

    def delete(self, *args, **kwargs):

        self.deleted = True
        self.save()

    def _apply_product_data(self):
        """Applies data from the set product

        Requires no arguments. The data is extracted
        from the product referenced by the item
        """
        
        self.description = self.product.description
        
        """
        This section has been deprecated as we are now moving
        to a single price system
        
        #Determines the unit price of the
        #the item based on the type of 
        #customer. And then calculates the
        #total price based on quantity
        if self.acknowledgement.customer.type == "Retail":
            self.unit_price = self.product.retail_price
        elif self.acknowledgement.customer.type == "Dealer":
            self.unit_price = self.product.wholesale_price
        else:
            self.unit_price = self.product.retail_price
        """
        self.unit_price = self.product.price
        logger.info(u"Item unit price set to {0:.2f}...".format(self.unit_price))

        #Calculate the total cost of the the item
        self.total = self.unit_price * Decimal(self.quantity)
        logger.info(u"Item total price set to {0:.2f}...".format(self.total))

        #Set the appropriate dimensions or to 0
        #if no dimensions are available from the model
        logger.info(u"Setting standard dimensions from standard product...")
        self.width = self.product.width if self.product.width else 0
        self.depth = self.product.depth if self.product.depth else 0
        self.height = self.product.height if self.product.height else 0

        self.image = self.product.image
        

    def _apply_data(self, **kwargs):
        """Applies data to the attributes

        Requires a User to authenticate what can and
        cannot be applied"""
        if "status" in kwargs:
            self.status = kwargs["status"]
            if self.status.lower() == "inventory":
                self.inventory = True
        if "comments" in kwargs:
            self.comments = kwargs["comments"]
        if "description" in kwargs:
            self.description = kwargs['description']
        #Set the size of item if custom
        if "is_custom_size" in kwargs:
            if kwargs["is_custom_size"] == True:
                self.is_custom_size = True
                try:
                    self.width = int(kwargs['width'])
                except (ValueError, KeyError, TypeError):
                    pass
                try:
                    self.depth = int(kwargs['depth'])
                except (ValueError, KeyError, TypeError):
                    pass
                try:
                    self.height = int(kwargs['height'])
                except (ValueError, KeyError, TypeError):
                    pass

        #Calculate the price of the item
        if "custom_price" in kwargs:
            try:
                if float(kwargs['custom_price']) > 0:
                    self.unit_price = Decimal(kwargs["custom_price"])
                    self.total = self.unit_price * Decimal(str(self.quantity))
                else:
                    self._calculate_custom_price()
            except: 
                self._calculate_custom_price()
        else:
            self._calculate_custom_price()

        #Create a Item from a custom product
        if "is_custom" in kwargs:
            if kwargs["is_custom"] == True:
                self.is_custom_item = True
                self.description = kwargs["description"]
                if "image" in kwargs:
                    self.image = S3Object.objects.get(pk=kwargs["image"]["id"])
                
                if self.description.strip() == "Custom Custom":
                    logger.error(u"Custom Item Description is still wrong")
        #Sets the fabric for the item
        if "fabric" in kwargs:
            try:
                self.fabric = Fabric.objects.get(pk=kwargs["fabric"]["id"])
                logger.info(u"{0} fabric set to {1} \n".format(self.description,
                                                           self.fabric.description))
            except Fabric.DoesNotExist as e:
                print u"Error: {0} /Fabric: {1}".format(e, kwargs["fabric"]["id"])

        #Sets all the pillows and the fabrics
        #for the item
        if "pillows" in kwargs:
            pillows = self._condense_pillows(kwargs["pillows"])
            self.pillows = [self._create_pillow(keys[0],
                                                pillows[keys],
                                                keys[1]) for keys in pillows]

    def _calculate_custom_price(self):
        """
        Caluates the custom price based on dimensions.
        
        Dellarobbia Collection:
        Charge 10% for first 15cm change, then adds 1% for each extra 5cm for all dimensions summatively
        
        Dwell Living:
        Charge 5% for first 15cm change, then adds 1% for each extra 5cm for all dimensions summatively
        """
        logger.info(u"Calculating custom price for {0}...".format(self.description))
        dimensions = {}
        try:
            dimensions['width_difference'] = self.width - self.product.width
        except:
            dimensions['width_difference'] = 0
        try:
            dimensions['depth_difference'] = self.depth - self.product.depth
        except:
            dimensions['depth_difference'] = 0
        try:
            dimensions['height_difference'] = self.height - self.product.height
        except:
            dimensions['height_difference'] = 0

        if self.product.collection == "Dellarobbia Thailand":
            upcharge_percentage = sum(self._calculate_upcharge(dimensions[key], 150, 10, 1) for key in dimensions)
        elif self.product.collection == "Dwell Living":
            upcharge_percentage = sum(self._calculate_upcharge(dimensions[key], 150, 5, 1) for key in dimensions)
        else:
            upcharge_percentage = 0

        self.unit_price = self.unit_price + (self.unit_price * (Decimal(upcharge_percentage) / 100))
        logger.info(u"Setting unit price of {0} to {1:.2f}".format(self.description, 
                                                              self.unit_price))
        
        self.total = self.unit_price * self.quantity
        logger.info(u"Setting total of {0} to {1:.2f}...".format(self.description,
                                                            self.total))

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
                pillows[(pillow["type"], pillow["fabric"]["id"])] += int(1)
            except KeyError:
                try:
                    pillows[(pillow["type"], pillow["fabric"]["id"])] = int(1)
                except KeyError:
                    try:
                        pillows[(pillow["type"], None)] += int(1)
                    except KeyError:
                        pillows[(pillow["type"], None)] = int(1)
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
            conn = S3Connection()
            url = conn.generate_url(1800, 'GET', bucket=self.bucket,
                                    key=self.image_key, force_http=True)
            return url
        except Exception:
            return None


class Pillow(models.Model):
    item = models.ForeignKey(Item, related_name='pillows')
    type = models.CharField(db_column="type", max_length=10)
    quantity = models.IntegerField(default=1)
    fabric = models.ForeignKey(Fabric, null=True, blank=True, related_name="estimate_pillow_fabric")

    @classmethod
    def create(cls, **kwargs):
        """Creates a new pillow"""
        pillow = cls(**kwargs)
        pillow.save()
        return pillow


class Log(models.Model):
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now=True, db_column='log_timestamp')
    delivery_date = models.DateField(null=True)
    estimate = models.ForeignKey(Estimate)

    @classmethod
    def create(cls, event, estimate, employee):
        """Creates an acknowlegement log"""
        log = cls(event=event, estimate=estimate,
                  employee=employee)
        log.save()
        return log

    def to_dict(self):
        """Get the log data"""

        return {'event': self.event,
                'employee': "{0} {1}".format(self.employee.first_name, self.employee.last_name),
                'timestamp': self.timestamp.isoformat()}


class Delivery(models.Model):
    estimate = models.ForeignKey(Estimate, null=True)
    description = models.TextField()
    _delivery_date = models.DateTimeField()
    longitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    latitude = models.DecimalField(decimal_places=6, max_digits=9, null=True)
    last_modified = models.DateTimeField(auto_now=True)

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
