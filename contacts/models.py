#!/usr/bin/env python
# -*- coding: utf-8 -*-
from decimal import Decimal
import logging
import pprint

from django.db import models
from apiclient import discovery
import gdata.contacts.client
import gdata.contacts.data

from administrator.models import CredentialsModel, OAuth2TokenFromCredentials, Storage
from administrator.models import Company
from accounting.models import Account
from trcloud.models import TRContact
from media.models import S3Object
from accounting.account import service as acc_service


pp = pprint.PrettyPrinter(width=1, indent=4)
logger = logging.getLogger(__name__)


class Contact(models.Model):

    # Business Related Attributes
    tax_id = models.TextField(null=True, blank=True)
    bank = models.TextField(null=True, default="")
    bank_account_number = models.TextField(null=True, default="")
    terms = models.TextField(null=False, default="50/net")
    address = models.TextField(null=True)
    branch = models.TextField(null=True)

    trcloud_id = models.IntegerField(null=True, default=0)
    name = models.TextField()
    name_th = models.TextField(null=True, blank=True)
    telephone = models.TextField(null=True, blank=True)
    fax = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=200, null=True, blank=True)
    job_title = models.TextField(null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    discount = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, null=True, default="THB")
    notes = models.TextField(null=True, default="", blank=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)
    contact = models.ForeignKey('self', related_name="contacts", null=True, on_delete=models.CASCADE)
    contact_service = None
    website = models.TextField(null=True, blank=True)
    google_contact_id = models.TextField(null=True, blank=True)

    # Accounting
    account_receivable = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, related_name='receivable_contact')
    account_payable = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, related_name='payable_contact')

    # Relationships
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    files = models.ManyToManyField(S3Object, through="File", related_name="contact")   

    @classmethod   
    def get_google_contacts_service(self, user):
        if self.contact_service is None:
            storage = Storage(CredentialsModel, 'id', user, 'credential')
            auth_token = OAuth2TokenFromCredentials(storage.get())
            self.contact_service = gdata.contacts.client.ContactsClient()
            auth_token.authorize(self.contact_service)
            
        return self.contact_service

    def save(self, *args, **kwargs):

        if self.account_payable is None:
            self.account_payable = acc_service.create_account_payable(self.company, self)

        if self.account_receivable is None:
            self.account_receivable = acc_service.create_account_receivable(self.company, self)

        super(Contact, self).save(*args, **kwargs)
        
    def sync_google_contacts(self, user):
        # Make the service availabel via the self.contact_service attribute
        self.get_google_contacts_service(user)
        
        # Loop through all the contacts
        for contact in self.contacts.all():
            if contact.google_contact_id:
                try:
                    self._update_google_contact(contact)
                except gdata.client.RequestError, e:
                    if e.status == 404:
                        self._create_google_contact(contact)
            else:
                self._create_google_contact(contact)
                
    def _create_google_contact(self, contact):
        """Create a new google contact
        """
        new_contact = gdata.contacts.data.ContactEntry()
        new_contact.name = gdata.data.Name(full_name=gdata.data.FullName(text=contact.name))
        
        if contact.email:
            new_contact.email.append(gdata.data.Email(address=contact.email,
                                                      primary='true',
                                                      rel=gdata.data.WORK_REL))
        if contact.telephone:
            new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.telephone,
                                                                   rel=gdata.data.WORK_REL, 
                                                                   primary='true'))
            
        g_contact = self.contact_service.CreateContact(new_contact)
        
        # Save and the contact ID
        contact.google_contact_id = g_contact.id.text
        contact.save()
        assert contact.google_contact_id
        
    def _update_google_contact(self, contact):
        """Update the google contact
        """
        g_contact = self.contact_service.GetContact(contact.google_contact_id)
        g_contact.name.full_name.text = contact.name
        
        if contact.email:
            try:
                g_contact.email[0].address = contact.email
                g_contact.email[0].primary = 'true'
                g_contact.email[0].rel = rel=gdata.data.WORK_REL
            except IndexError as e:
                logger.warn(e)
                g_contact.email.append(gdata.data.Email(address=contact.email,
                                                        primary='true',
                                                        rel=gdata.data.WORK_REL))
        
        if contact.telephone:
            try:
                g_contact.phone_number[0].text = contact.telephone
            except (IndexError, Exception) as e:
                logger.warn(e)
                logger.debug(contact.telephone)
                logger.debug(g_contact.phone_number)
                g_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.telephone,
                                                                     rel=gdata.data.WORK_REL, 
                                                                     primary='true'))
                
        # Update the google contact
        g_contact = self.contact_service.Update(g_contact)
        assert contact.google_contact_id

    def create_in_trcloud(self):
        """Create the contact in trcloud"""
        tr_contact = TRContact()

        # Set Type
        tr_contact.contact_type = "Client"
        tr_contact.branch = u"สำนักงานใหญ่"

        # Populate data for submission from Attributes

        for i in dir(self):
            attrs = dir(tr_contact)
            if not i.startswith('_') and i.lower() in attrs:
                setattr(tr_contact, i, getattr(self, i) or '')
            #if not i.startswith('_') and not callable(getattr(self, i)) and hasattr(tr_contact, i):
            #    setattr(tr_contact, i, getattr(self, i))
        
        # Set Orgnization name 
        if u"co.," or u"บริษัท" in self.name.lower():
            tr_contact.organization = self.name
        
        # Populate address data
        address = self.addresses.all()[0]
        tr_address = "{0}, {1}, {2}, {3} {4}".format(address.address1,
                                                     address.city,
                                                     address.territory,
                                                     address.country,
                                                     address.zipcode)
        tr_contact.address = tr_address

        tr_contact.create()
        
        self.trcloud_id = tr_contact.contact_id
        self.save()
    


class Address(models.Model):
    address1 = models.TextField(null=True)
    address2 = models.TextField(null=True, default=None)
    city = models.TextField(null=True)
    territory = models.TextField(null=True)
    country = models.TextField(null=True)
    zipcode = models.TextField(null=True)
    contact = models.ForeignKey(Contact, related_name="addresses", on_delete=models.CASCADE)
    latitude = models.DecimalField(decimal_places=15, max_digits=20, null=True)
    longitude = models.DecimalField(decimal_places=15, max_digits=20, null=True)
    user_defined_latlng = models.BooleanField(default=False)


class Customer(Contact):
    first_name = models.TextField(null=True)
    last_name = models.TextField(null=True)
    type = models.CharField(max_length=10, default="Retail")

    #class Meta:
        #ordering = ['name']


class Supplier(Contact):
    pass

class SupplierContact(models.Model):
    name = models.TextField()
    email = models.TextField(null=True, blank=True)
    telephone = models.TextField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    primary = models.BooleanField(db_column='primary_contact', default=False)


class File(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    file = models.ForeignKey(S3Object, on_delete=models.CASCADE)




