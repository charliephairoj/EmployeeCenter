#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import dateutil.parser
import math
import logging
from decimal import *
import httplib2

from pytz import timezone
from datetime import datetime
from django.conf import settings
from django.db import models
from administrator.models import User, Storage
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto.ses
#from oauth2client.contrib.django_orm import Storage
from oauth2client.contrib import gce
from apiclient import discovery

from contacts.models import Customer
from products.models import Product, Upholstery
from projects.models import Project, Room, Phase
from receipts.PDF import ReceiptPDF
from media.models import Log, S3Object
from administrator.models import Company, CredentialsModel, Log as BaseLog
from trcloud.models import TRSalesOrder, TRContact
from acknowledgements.models import Acknowledgement, Item as AckItem
from invoices.models import Invoice, Item as InvItem

logger = logging.getLogger(__name__)


class Receipt(models.Model):
    document_number = models.IntegerField(default=0)
    company = models.ForeignKey(Company)
    company_name = models.TextField(default="Alinea Group Co., Ltd.")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, related_name='receipts')
    employee = models.ForeignKey(User, db_column='employee_id', on_delete=models.PROTECT, null=True)
    acknowledgement = models.ForeignKey(Acknowledgement, on_delete=models.PROTECT, null=True, related_name='receipts')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, null=True, related_name='receipts')
    time_created = models.DateTimeField(auto_now_add=True)
    paid_date = models.DateTimeField(default=datetime.now)
    status = models.TextField(default='paid')
    remarks = models.TextField(null=True, default=None, blank=True)
    last_modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    pdf = models.ForeignKey(S3Object,
                            null=True,
                            related_name='+',
                            db_column="pdf")
    
    files = models.ManyToManyField(S3Object, through="File", related_name="receipt")
    calendar_event_id = models.TextField(null=True)
    
    current_user = None 
    calendar_service = None

    # VATs
    vat = models.IntegerField(default=0)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    #Discounts
    discount = models.IntegerField(default=0)
    second_discount = models.IntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    second_discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Totals
    # Totals of item totals
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after first discount
    post_discount_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after second Discount
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Total after all discounts and Vats
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
        
    # @property
    # def status(self):
    #     return self._status

    # @status.setter
    # def status(self, value):
    #     self._status = value

    def save(self, *args, **kwargs):
        if self.document_number == 0 or self.document_number is None:
            try:
                last_id = Receipt.objects.filter(company=self.company).latest('document_number').document_number + 1
            except Invoice.DoesNotExist:
                last_id = 100001

            self.document_number = last_id

        super(Receipt, self).save(*args, **kwargs)

    def delete(self):
        """
        Overrides the standard delete method.
        
        This method will simply make the receipt as deleted in
        the database rather an actually delete the record
        """
        self.deleted = True

    def filtered_logs(self):
        """Filter logs source"""
        return self.logs.exclude(type__icontains="error")

    
    def create_and_upload_pdf(self, delete_original=True):
        receipt_filename = self.create_pdf()
        receipt_key = "receipt/{0}/Receipt-{0}.pdf".format(self.id)
        
        bucket = "document.dellarobbiathailand.com"
        receipt_pdf = S3Object.create(receipt_filename, receipt_key, bucket, delete_original=delete_original)
       
        # Save references for files
        self.pdf = receipt_pdf
        
        self.save()
        
    def create_pdf(self):
        """Creates Production and Receipt PDFs

        This method will extract the necessary data to 
        create the pdfs from the object itself. It requires
        no arguments
        """
        products = self.items.all().order_by('id')

        # Initialize pdfs
        receipt_pdf = ReceiptPDF(customer=self.customer, receipt=self, products=products)
        
        # Create pdfs
        receipt_filename = receipt_pdf.create()
        
        return receipt_filename
        
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
        we are creating a new Receipt, and the
        items and receipt have not yet been saved
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
            logger.debug("item: {0:.2f} x {1} = {2:.2f}".format(product.unit_price, product.quantity, product.total))
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
        discount_amount = (Decimal(self.discount) / Decimal('100')) * subtotal
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
            'subtotal': self._format_precision(subtotal),
            'post_discount_total': self._format_precision(post_discount_total),
            'total': self._format_precision(total),
            'grand_total': self._format_precision(grand_total),
            'vat_amount': self._format_precision(vat_amount),
            'discount_amount': self._format_precision(discount_amount),
            'second_discount_amount': self._format_precision(second_discount_amount)
        }

    
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
        if 'receipts' not in calendar_summaries:
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
                if cal['summary'].lower() == 'receipts':
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
            'summary': "Ack {0}".format(self.id),
            'location': self._get_address_as_string(),
            'description': self._get_description_as_string(),
            'start': {
                'date': self.paid_date.strftime('%Y-%m-%d')
            },
            'end': {
                'date': self.paid_date.strftime('%Y-%m-%d')
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
            addr = self.customer.addresses.all()[0]
        
            addr_str += addr.address1 + ", " + addr.city + ", " + addr.territory
            addr_str += ", " + addr.country + " " + addr.zipcode
        
            return addr_str
        except Exception as e:
            logger.warn(e)
            return ""
        
    def _get_description_as_string(self):
        description = u"""
        Receipt: {0}
        Customer: {1}
        Qty     Items: 
        """.format(self.id, self.customer.name)
        
        for i in self.items.all().order_by('id'):
            description += u"{0:.2f}  {1}".format(i.quantity, i.description)
            
        return description

    def _format_precision(self, value):
        return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        
    def __str__(self):
        return u"Receipt #{0}".format(self.id)


        

class File(models.Model):
    receipt = models.ForeignKey(Receipt)
    file = models.ForeignKey(S3Object, related_name='receipt_files')
    
    
class Item(models.Model):
    trcloud_id = models.IntegerField(null=True, blank=True)
    receipt = models.ForeignKey(Receipt, related_name="items")
    invoice_item = models.ForeignKey(InvItem, null=True, related_name="receipt_items")
    quantity = models.DecimalField(max_digits=15, decimal_places=2, null=False)
    unit_price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    description = models.TextField()
    status = models.CharField(db_column="status", max_length=50, default="paid")
    comments = models.TextField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)


class Log(BaseLog):
    log_ptr = models.OneToOneField(BaseLog, related_name='+')
    receipt = models.ForeignKey(Receipt, related_name='logs')

    @classmethod
    def create(cls, **kwargs):

        log_type = kwargs.pop('type', 'RECEIPT')

        log = cls(type=log_type, **kwargs)
        log.save()

        return log
    

