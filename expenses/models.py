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
from administrator.models import User, Storage, Company
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto.ses
#from oauth2client.contrib.django_orm import Storage
from oauth2client.contrib import gce
from apiclient import discovery

from contacts.models import Supplier
from products.models import Product, Upholstery
from supplies.models import Supply
from projects.models import Project, Room, Phase
from invoices.PDF import InvoicePDF
from media.models import Log, S3Object
from administrator.models import CredentialsModel, Log as BaseLog
from trcloud.models import TRSalesOrder, TRContact
from acknowledgements.models import Acknowledgement, Item as AckItem
from accounting.models import JournalEntry


logger = logging.getLogger(__name__)


class Expense(models.Model):
    company_name = models.TextField(default="Alinea Group Co., Ltd.")
    
    time_created = models.DateTimeField(auto_now_add=True)
    status = models.TextField(db_column='status', default='open')
    remarks = models.TextField(null=True, default=None, blank=True)
    
    last_modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    pdf = models.ForeignKey(S3Object,
                                            null=True,
                                            related_name='+',
                                            db_column="pdf")
    
    current_user = None 

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

    # Accounting
    journal_entry = models.ForeignKey(JournalEntry, null=True, related_name="expenses")
    
    # Relationships
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, related_name='expenses')
    employee = models.ForeignKey(User, db_column='employee_id', on_delete=models.PROTECT, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='expenses')
    project = models.ForeignKey(Project, null=True, blank=True, related_name='expenses')
    room = models.ForeignKey(Room, null=True, blank=True, related_name='expenses')
    phase = models.ForeignKey(Phase, null=True, blank=True, related_name='expenses')
    files = models.ManyToManyField(S3Object, through="File", related_name="expenses")

    
    # @property
    # def status(self):
    #     return self._status

    # @status.setter
    # def status(self, value):
    #     self._status = value
        
    def delete(self):
        """
        Overrides the standard delete method.
        
        This method will simply make the invoice as deleted in
        the database rather an actually delete the record
        """
        self.deleted = True

    def create_and_upload_pdf(self, delete_original=True):
        invoice_filename = self.create_pdf()
        invoice_key = "invoice/{0}/Invoice-{0}.pdf".format(self.id)
        
        bucket = "document.dellarobbiathailand.com"
        invoice_pdf = S3Object.create(invoice_filename, invoice_key, bucket, delete_original=delete_original)
       
        # Save references for files
        self.pdf = invoice_pdf
        
        self.save()
        
    def create_pdf(self):
        """Creates Production and Invoice PDFs

        This method will extract the necessary data to 
        create the pdfs from the object itself. It requires
        no arguments
        """
        products = self.items.all().order_by('id')

        # Initialize pdfs
        invoice_pdf = InvoicePDF(customer=self.customer, invoice=self, products=products)
        
        # Create pdfs
        invoice_filename = invoice_pdf.create()
        
        return invoice_filename
        
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
        we are creating a new Invoice, and the
        items and invoice have not yet been saved
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

    def _format_precision(self, value):
        return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        
    def __str__(self):
        return u"Invoice #{0}".format(self.id)


        

class File(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    file = models.ForeignKey(S3Object, related_name='invoice_files')
    
    
class Item(models.Model):
    expense = models.ForeignKey(Expense, related_name="items", on_delete=models.PROTECT)
    supply = models.ForeignKey(Supply, null=True, related_name="purchased", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2, null=False)
    unit_price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    description = models.TextField()
    status = models.CharField(db_column="status", max_length=50, default="invoiced")
    comments = models.TextField(null=True, blank=True)
    image = models.ForeignKey(S3Object, null=True, blank=True, related_name="invoice_items")
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)


class Log(BaseLog):
    log_ptr = models.OneToOneField(BaseLog, related_name='+')
    expense = models.ForeignKey(Expense, related_name='logs')

    @classmethod
    def create(cls, **kwargs):

        log_type = kwargs.pop('type', 'EXPENSE')

        log = cls(type=log_type, **kwargs)
        log.save()

        return log
    

