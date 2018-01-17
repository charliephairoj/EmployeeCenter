#!/usr/bin/env python
# -*- coding: utf-8 -*-
from decimal import Decimal
import logging
import pprint

from django.db import models
from oauth2client.contrib.django_orm import Storage
from apiclient import discovery
import gdata.contacts.client
import gdata.contacts.data

from administrator.models import CredentialsModel, OAuth2TokenFromCredentials
from trcloud.models import TRContact


pp = pprint.PrettyPrinter(width=1, indent=4)
logger = logging.getLogger(__name__)


class Contact(models.Model):
    trcloud_id = models.IntegerField(null=True, default=0)
    name = models.TextField()
    name_th = models.TextField(null=True, blank=True)
    telephone = models.TextField()
    fax = models.TextField()
    email = models.CharField(max_length=200, null=True, blank=True)
    job_title = models.TextField(null=True)
    is_supplier = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    discount = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, null=True)
    notes = models.TextField(null=True, default="", blank=True)
    deleted = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)
    contact = models.ForeignKey('self', related_name="contacts", null=True)
    contact_service = None
    website = models.TextField(null=True, blank=True)
    google_contact_id = models.TextField(null=True, blank=True)
    tax_id = models.TextField(null=True, blank=True)
    bank = models.TextField(null=True, default="")
    bank_account_number = models.TextField(null=True, default="")

    #class Meta:
        #ordering = ['name']

    @classmethod   
    def get_google_contacts_service(self, user):
        if self.contact_service is None:
            storage = Storage(CredentialsModel, 'id', user, 'credential')
            auth_token = OAuth2TokenFromCredentials(storage.get())
            self.contact_service = gdata.contacts.client.ContactsClient()
            auth_token.authorize(self.contact_service)
            
        return self.contact_service
        
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
    address1 = models.CharField(max_length=160)
    address2 = models.CharField(max_length=160, null=True)
    city = models.CharField(max_length=100)
    territory = models.TextField(null=True)
    country = models.CharField(max_length=150)
    zipcode = models.TextField()
    contact = models.ForeignKey(Contact, related_name="addresses")
    latitude = models.DecimalField(decimal_places=15, max_digits=20, null=True)
    longitude = models.DecimalField(decimal_places=15, max_digits=20, null=True)
    user_defined_latlng = models.BooleanField(default=False)
    
    @property
    def lat(self):
        return self.latitude
    
    @lat.setter
    def lat(self, latitude):
        self.latitude = latitude
        
    @property
    def lng(self):
        return self.longitude
    
    @lng.setter
    def lng(self, longitude):
        self.longitude = longitude
    
    @classmethod
    def create(cls, **kwargs):
        address = cls(**kwargs)

        if not address.address1:
            raise AttributeError("Missing 'address'")
        if not address.city:
            raise AttributeError("Missing 'city'")
        if not address.territory:
            raise AttributeError("Missing 'territory'")
        if not address.country:
            raise AttributeError("Missing 'country'")
        if not address.zipcode:
            raise AttributeError("Missing 'zipcode'")

        try:
            address.latitude = kwargs["lat"]
            address.longitude = kwargs["lng"]
        except:
            pass

        address.save()
        return address

    def update(self, data):
        if "address1" in data:
            self.address1 = data["address1"]
        if "address2" in data:
            self.address2 = data["address2"]
        if "city" in data:
            self.city = data["city"]
        if "territory" in data:
            self.territory = data["territory"]
        if "country" in data:
            self.country = data["country"]
        if "zipcode" in data:
            self.zipcode = data["zipcode"]
        """We have to change to str before decimal from float in order
        to accomodate python pre 2.7"""
        if "lat" in data:
            self.latitude = Decimal(str(data['lat']))
        if "lng" in data:
            self.longitude = Decimal(str(data['lng']))
        self.save()


class Customer(Contact):
    first_name = models.TextField()
    last_name = models.TextField(null=True)
    type = models.CharField(max_length=10, default="Retail")

    #class Meta:
        #ordering = ['name']
    
    def _init__(self, *args, **kwargs):
        super(Customer, self).__init__(*args, **kwargs)
        self.is_customer = True
    


class Supplier(Contact):
    terms = models.IntegerField(default=0)
    
    def _init__(self, *args, **kwargs):
        super(Supplier, self).__init__(*args, **kwargs)
        self.is_supplier = True
    


class SupplierContact(models.Model):
    name = models.TextField()
    email = models.TextField(null=True, blank=True)
    telephone = models.TextField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier)
    primary = models.BooleanField(db_column='primary_contact', default=False)

    



