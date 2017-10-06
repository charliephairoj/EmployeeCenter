"""
Models for the Purchase Orders App
"""
import sys
import datetime
import logging
import math
from decimal import Decimal
import httplib2
import hashlib
import random
import string

import boto.ses
from django.template.loader import render_to_string
from django.db import models
from django.contrib.auth.models import User
from oauth2client.contrib.django_orm import Storage
from apiclient import discovery

from administrator.models import Log as BaseLog
from supplies.models import Supply, Log, Product
from contacts.models import Supplier
from media.models import S3Object
from po.PDF import PurchaseOrderPDF, InventoryPurchaseOrderPDF
from projects.models import Project, Room, Phase
from administrator.models import CredentialsModel


logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    company = models.TextField(default="Alinea Group")
    supplier = models.ForeignKey(Supplier)
    order_date = models.DateTimeField(auto_now_add=True)
    created = models.DateTimeField(auto_now_add=True)
    receive_date = models.DateTimeField(null=True)
    paid_date = models.DateTimeField(null=True)
    terms = models.IntegerField(default=0)
    vat = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)
    shipping_type = models.CharField(max_length=10, default="none")
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="THB")
    
    # refers to the total of all items
    subtotal = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    
    # refers to total after discount
    total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    
    # refers to the todal after vat
    grand_total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    employee = models.ForeignKey(User)
    last_modified = models.DateTimeField(auto_now=True)
    status = models.TextField(default="AWAITING APPROVAL")
    pdf = models.ForeignKey(S3Object, null=True)
    auto_print_pdf = models.ForeignKey(S3Object, null=True, related_name="auto_print_po")
    project = models.ForeignKey(Project, null=True, blank=True, related_name="purchase_orders")
    room = models.ForeignKey(Room, null=True)
    phase = models.ForeignKey(Phase, null=True)
    deposit = models.IntegerField(default=0)
    deposit_type = models.TextField(default="percent")
    revision = models.IntegerField(default=0)
    comments = models.TextField(null=True)
    calendar_event_id = models.TextField(null=True)

    # Approval fields
    approval_key = models.TextField(null=True)
    approval_salt = models.TextField(null=True)
    approval_pass = models.TextField(null=True)
    
    current_user = None 
    calendar_service = None

    @classmethod
    def create(cls, user=None, **kwargs):
        """
        Creates a purchase order
        
        This method creates the order details first, then
        creates the supplies. The totals of the supplies are
        then added and applied to the purchase order.
        The order and supplies are then saved
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
        order.total = order.subtotal - ((Decimal(order.discount) / 100) * order.subtotal)
        order.grand_total = Decimal(order.total) * (Decimal(1) + Decimal(order.vat) / 100)
        
        # Save the order
        order.save()
        
        # Save all the items in the order
        for supply in order.temporary_supplies:
            supply.purchase_order = order
            supply.save()
           
        # Create and upload pdf
        """
        pdf = PurchaseOrderPDF(po=order, items=order.items.all(),
                               supplier=order.supplier)
        filename = pdf.create()
        key = "purchase_order/PO-{0}.pdf".format(order.id)
        order.pdf = S3Object.create(filename, key, 'document.dellarobbiathailand.com')
        order.save()
        """
        
        return order
    
    def calculate_total(self):
        """
        Calculate the subtotal, total, and grand total
        """
        
        return Decimal(str(round(self._calculate_grand_total(), 2)))
        
    def create_pdf(self):
        """
        Creates a pdf and returns the filename
        """
        items = self.items.all().order_by('id')
        for item in items:
            item.supply.supplier = item.purchase_order.supplier
        
        # Create and upload pdf
        pdf = PurchaseOrderPDF(po=self, items=items,
                               supplier=self.supplier,
                               revision=self.revision,
                               revision_date=self.order_date)
                               
        auto_print_pdf = InventoryPurchaseOrderPDF(po=self, items=items,
                                                   supplier=self.supplier,
                                                   revision=self.revision,
                                                   revision_date=self.order_date)
                               
        filename = pdf.create()
        filename2 = auto_print_pdf.create()
        return filename, filename2
        
    def create_and_upload_pdf(self):
        """
        Creates a pdf and uploads it to the S3 service
        """
        filename, filename2 = self.create_pdf()
        key = "purchase_order/PO-{0}.pdf".format(self.id)
        self.pdf = S3Object.create(filename,
                                   key,
                                   'document.dellarobbiathailand.com')
        
        auto_key = "purchase_order/PO-{0}-auto.pdf".format(self.id)
        self.auto_print_pdf = S3Object.create(filename2,
                                              auto_key,
                                              'document.dellarobbiathailand.com')
        
        self.save()

    def email_approver(self):
        
        conn = boto.ses.connect_to_region('us-east-1')
        recipients = ["charliep@alineagroup.co"]

        approval_url = "http://localhost:8000/api/v1/purchase-order/approval/"
        approval_url += "?pass={0}".format(self.create_approval_pass())
        html_string = render_to_string('purchase_order_approval.html', {'po': self,
                                                                       'items': self.items.all()})

        

        logger.debug(html_string)
        #Send email
        """
        conn.send_email('no-reply@dellarobbiathailand.com',
                        u'Purchase Order from {0} Received'.format(purchase_order.supplier.name),
                        body,
                        recipients,
                        format='html')
        """
    
    def _calculate_subtotal(self):
        """
        Calculate the subtotal
        """
        if self.items.count() > 0:
            self.subtotal = sum([item.total for item in self.items.all()])
        else:
            raise ValueError('Purchase Order cannot not have 0 items')
        
        logger.debug("The subtotal is {0:.2f}".format(self.subtotal))
        
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

        logger.debug("The total is {0:.2f}".format(self.total))
        
        return self.total
    
    def _calculate_grand_total(self):
        """
        Calcualte the grand total
        """
        logger.info('\nCalculating total...')
        total = self._calculate_total()
        
        logger.debug("The vat is at {0}%".format(self.vat))
        if self.vat > 0:
            self.grand_total = total + (total * (Decimal(self.vat) / Decimal('100')))
        else:
            self.grand_total = total
        
        # Convert to 2 decimal places
        self.grand_total = Decimal(str(math.ceil(self.grand_total * 100) / 100))
        
        logger.debug("The grand total is {0:.2f}".format(self.grand_total))
        logger.info("Total calculated. \n")
        
        return self.grand_total
        
    def _get_calendar_service(self, user):
        if self.calendar_service:
            self.calendar_service
        else:
            
            storage = Storage(CredentialsModel, 'id', user, 'credential')
            credentials = storage.get()
        
            http = credentials.authorize(httplib2.Http())
            self.calendar_service = discovery.build('calendar', 'v3', http=http)
            
        return self.calendar_service
        
    def _get_calendar(self, user):
        service = self._get_calendar_service(user)
        response = service.calendarList().list().execute()
        
        calendar_summaries = [cal['summary'].lower() for cal in response['items']]
    
        # Check if user does not already has account payables
        if 'receivables' not in calendar_summaries:
            # Get calendar
            cal_id = 'dellarobbiathailand.com_vl7drjcuulloicm0qlupgsr4ko@group.calendar.google.com'
            calendar = service.calendars().get(calendarId=cal_id).execute()
     
            # Add calendar to user's calendarList
            service.calendarList().insert(body={
                'id': calendar['id']
            }).execute()
            
        else:
            # Get calendar is already in calendarList
            for cal in response['items']:
                if cal['summary'].lower() == 'receivables':
                    calendar = cal
            
        return calendar
        
    def create_calendar_event(self, user):
        """Create a calendar event for the expected delivery date
        
        """
        service = self._get_calendar_service(user)
        calendar = self._get_calendar(user)
        
        response = service.events().insert(calendarId=calendar['id'], 
                                           body=self._get_event_body()).execute()
        self.calendar_event_id = response['id']
        self.save()
        
    def update_calendar_event(self, user=None):
        """Create a calendar event for the expected delivery date
        
        """
        if user is None:
            user = self.current_user or self.employee
        
        if self.calendar_event_id:
            
            service = self._get_calendar_service(user)
            calendar = self._get_calendar(user)
        
            resp = service.events().update(calendarId=calendar['id'], 
                                           eventId=self.calendar_event_id, 
                                           body=self._get_event_body()).execute()
                                          
        else:
            
            self.create_calendar_event(user)
                                                                       
    def _get_event_body(self):
        evt = {
            'summary': "Purchase Order {0}".format(self.id),
            'location': self._get_address_as_string(),
            'description': self._get_description_as_string(),
            'start': {
                'date': self.receive_date.strftime('%Y-%m-%d')
            },
            'end': {
                'date': self.receive_date.strftime('%Y-%m-%d')
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                  {'method': 'email', 'minutes': 24 * 60 * 2},
                  {'method': 'email', 'minutes': 120},
                ]
            }
        }
        
        return evt

    def _get_address_as_string(self):
        try:
            addr_str = ""
            addr = self.supplier.addresses.all()[0]
        
            addr_str += addr.address1 + ", " + addr.city + ", " + addr.territory
            addr_str += ", " + addr.country + " " + addr.zipcode
        
            return addr_str
        except Exception as e:
            logger.warn(e)
            return ""

    def _get_description_as_string(self):
        description = u"""
        Purchase Order: {0}
        Supplier: {1}
        Qty     Items: 
        """.format(self.id, self.supplier.name)
        
        for i in self.items.all().order_by('id'):
            description += u"{0:.2f}  {1}".format(i.quantity, i.description)
            
        return description

    def create_approval_key(self):
        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return key

    def create_approval_pass(self):
        """
        Return approval_pass, which is created 
        by the hash of the approval_key
        """
        return hashlib.sha512(self.approval_key + self.approval_salt).hexdigest()

    def email_approver(self):
        # Styles
        main_container_style = """
        width:50em;
        height:100%;
        font-family: Tahoma;
        display: block;
        float:none;
        text-align:center;
        padding:5em 1em;"""
        button_container_style = """
        padding:1em 0;
        display:block;
        float:left;
        """
        button_style = """
        float:left;
        appearance: button;
        background:green;
        width:5em;
        padding:1em 0;
        display:block;
        text-align:center;
        border-radius:4px;
        color:rgba(255, 255, 255, 1);
        text-decoration: none;
        outline: none;
        overflow: hidden;
        cursor: pointer;
        border:5px solid rgba(199, 199, 199, 1);
        """

        
        conn = boto.ses.connect_to_region('us-east-1')
        recipients = ["charliep@alineagroup.co"]

        approval_url = "https://employee.alineagroup.co/api/v1/purchase-order/approval/"
        #approval_url = "http://localhost:8000/api/v1/purchase-order/approval/"
        
        approval_url += "?pass={0}&status=approved&id={1}".format(self.create_approval_pass(), 
                                                                  self.id)
        body = render_to_string('purchase_order_approval.html', {'po': self,
                                                                 'items': self.items.all(), 
                                                                 'approval_url': approval_url,
                                                                 'pdf_url':self.pdf.generate_url(time=172800),
                                                                 'main_container_style': main_container_style,
                                                                 'button_container_style': button_container_style,
                                                                 'button_style': button_style
                                                                 })
        #Send email
        
        conn.send_email('no-reply@dellarobbiathailand.com',
                        u'Approval Request: Purchase Order {0}: ({1})'.format(self.id,
                                                                              self.supplier.name),
                        body,
                        recipients,
                        format='html')


    def email_requester(self):
        # Styles
        main_container_style = """
        width:50em;
        height:100%;
        font-family: Tahoma;
        display: block;
        float:none;
        text-align:center;
        padding:5em 1em;"""
        button_container_style = """
        padding:1em 0;
        display:block;
        float:left;
        """
        button_style = """
        float:left;
        appearance: button;
        background:green;
        width:5em;
        padding:1em 0;
        display:block;
        text-align:center;
        border-radius:4px;
        color:rgba(255, 255, 255, 1);
        text-decoration: none;
        outline: none;
        overflow: hidden;
        cursor: pointer;
        border:5px solid rgba(199, 199, 199, 1);
        """

        
        conn = boto.ses.connect_to_region('us-east-1')
        recipients = [po.employee.email]
      
        body = render_to_string('purchase_order_approved.html', {'po': self,
                                                                 'items': self.items.all(), 
                                                                 'pdf_url':self.pdf.generate_url(time=172800),
                                                                 'main_container_style': main_container_style,
                                                                 'button_container_style': button_container_style,
                                                                 'button_style': button_style
                                                                 })
        #Send email
        
        conn.send_email('no-reply@dellarobbiathailand.com',
                        u'Approved: Purchase Order {0}: ({1})'.format(self.id,
                                                                      self.supplier.name),
                        body,
                        recipients,
                        format='html')
        

    def approve(self, approval_pass):
        if approval_pass == self.create_approval_pass():
            self.approval_pass = approval_pass
            self.status = "APPROVED"
            self.save()

            return True
        else:
            return False
        
        
class Item(models.Model):
    
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items')
    supply = models.ForeignKey(Supply, db_column="supply_id", related_name="po_item")
    description = models.TextField()
    quantity = models.DecimalField(decimal_places=10, max_digits=24)
    status = models.TextField(default="Ordered")
    discount = models.IntegerField(default=0)
    unit_cost = models.DecimalField(decimal_places=4, max_digits=15, default=0)
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    comments = models.TextField(null=True)
        
    @classmethod
    def create(cls, supplier=None, **kwargs):
        item = cls()
        try:
            item.supply = Supply.objects.get(id=kwargs['supply']["id"])
        except KeyError:
            item.supply = Supply.objects.get(id=kwargs['id'])
            
        item.supply.supplier = supplier
        item.description = item.supply.description
        
        # Apply costs
        if "cost" in kwargs:
            if Decimal(kwargs['cost']) != item.supply.cost:
                item.unit_cost = Decimal(kwargs['cost'])
                product = Product.objects.get(supply=item.supply, supplier=supplier)
                old_price = product.cost
                product.cost = Decimal(kwargs['cost'])
                product.save()
                
                message = u"Price change from {0}{2} to {1}{2} for {3} [Supplier: {4}]"
                log = Log(supply=item.supply,
                          supplier=supplier,
                          action="PRICE CHANGE",
                          quantity=None,
                          cost=product.cost,
                          message=message.format(old_price,
                                                 product.cost,
                                                 supplier.currency,
                                                 item.supply.description,
                                                 supplier.name))
                log.save()
        else:
            item.unit_cost = item.supply.cost
        item.discount = item.supply.discount
        if "discount" in kwargs:
            item.discount = kwargs['discount']
            
        if "comments" in kwargs:
            item.comments = kwargs['comments']
        
        item.quantity = int(kwargs["quantity"])
        
        item.calculate_total()
       
        return item
    
    def calculate_total(self):
        """
        Calculate the totals based on the unit_cost, quantity
        and the discount provied
        """
        # Calculate late the unit_cost based on discount if available
        logger.debug(self.unit_cost)
        if not self.unit_cost:
            self.unit_cost = self.supply.cost
        if self.supply.discount == 0 and self.discount == 0:
            
            logger.debug(u"{0} unit cost is {1}".format(self.description, self.unit_cost))
        else:
            logger.debug(u"{0} discount is {1}%".format(self.description, self.discount))
            if sys.version_info[:2] == (2, 6):
                discount_percent = (Decimal(str(self.discount)) / Decimal('100'))
                discount_amount = Decimal(str(self.unit_cost)) * discount_percent
            elif sys.version_info[:2] == (2, 7):
                discount_percent = (Decimal(self.discount) / Decimal('100'))
                discount_amount = Decimal(self.unit_cost) * discount_percent
            
            # Debuggin message
            message = u"{0} discounted unit cost is {1}"
            logger.debug(message.format(self.description,
                                        self.unit_cost - discount_amount))
        
        # Set the discount to be used.
        # Note: ENTERED DISCOUNT OVERRULES SAVED DISCOUNT
        self.discount = self.discount or self.supply.discount
        
        unit_cost = Decimal(self.unit_cost)
        discount = unit_cost * (Decimal(self.discount) / Decimal('100'))
        unit_cost = unit_cost - discount
        self.total = unit_cost * Decimal(self.quantity)

        logger.debug(u"{0} total quantity is {1}".format(self.description, self.quantity))
        logger.debug(u"{0} total cost is {1:.2f}".format(self.description, self.total))

        
class Log(BaseLog):
    log_ptr = models.OneToOneField(BaseLog, related_name='+')
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='logs')

    @classmethod
    def create(cls, **kwargs):

        log_type = kwargs.pop('type', 'PURCHASE ORDER')
        

        log = cls(type=log_type, **kwargs)
        log.save()

        return log