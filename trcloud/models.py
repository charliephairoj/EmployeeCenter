#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import requests
import json
import hashlib
import time
from datetime import datetime
import math
import pprint

from django.db import models

pp = pprint.PrettyPrinter(indent=4, width=1)
logger = logging.getLogger(__name__)


class BaseTRModelMixin(object):
    @classmethod
    def _prepare_body_for_request(cls, data):
        timestamp = str(int(math.floor(time.time())))
        
        """
        Test Settings
        """
        predata = {
            "company_id":"6",
            "passkey":"65da331b0d94e45a910fb88e1d29cdc7",
            "securekey": hashlib.md5("0d94e4" +"t" + timestamp).hexdigest(),
            "timestamp": timestamp,
        }

        """
        predata = {
            "company_id":"5",
            "passkey":"b01ebdb1ce5a28f803de6973cd833fb4",
            "securekey": hashlib.md5("ce5a28" +"t" + timestamp).hexdigest(),
            "timestamp": timestamp,
        }
        """



        # Merge the request keys and information with the body data
        data.update(predata)
        logger.debug(pp.pformat(data))
        # Transform data into JSON string per specification
        body = {"json" : json.dumps(data)}

        return body
    
    @classmethod
    def _parse_response(cls, response):
        """JSON parses the response and returns if the post was a success"""

        # Change response from text to data
        data = json.loads(response.text)
        
        # If the response is a success return it
        if int(data['success']) == 1:
            if 'head' in data:
                return data['head']
            elif 'result' in data:
                return data['result']
            else:
                return data
        else:
            raise Exception("The submission failed")

    @classmethod
    def _send_request(cls, url, data):
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Origin': 'http://localhost'}
        response = requests.post(url, data=data, headers=headers)
       
        data = cls._parse_response(response)
        return data
    
    @classmethod
    def _search(cls, url, index=0, keyword=''):

        data = {'index': index,
                'keyword': keyword}
                
        response = cls._send_request(url, cls._prepare_body_for_request(data))
        return response

    @classmethod
    def _retrieve(cls, url, id):
        
        data = {'id': id}

        response = cls._send_request(url, cls._prepare_body_for_request(data))
        return response

    def _create(self, url, data):

        data = self._prepare_body_for_request(data)

        response = self._send_request(url, data)
        return response

    def _update(self, url, data):
        data = self._prepare_body_for_request(data)

        response = self._send_request(url, data)
        return response


class TRContact(BaseTRModelMixin):
    id = ""
    contact_id = ""
    title = ""
    name = ""
    organization = ""
    contact_type = "normal"
    branch = "Headquarter"
    tax_id  = ""
    source  = ""
    
    address = ""
    telephone  = ""
    email =""
    
    shipping_address = ""
    shipping_email = ""
    shipping_telephone = ""
    
    bn_credit_limit = "0"
    iv_credit_limit = "0"
    
    credit_expense = "0"
    credit_revenue = "0"
    remark = ""
    condition =""
    
    bill = ""
    expense = ""
    invoice = ""
    payment = ""
    receipt = ""

    @classmethod
    def retrieve(cls, id):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-contact/retrieve-contact.php"
        data = cls._retrieve(url, id)

        return data
    
    @classmethod
    def search(cls, keyword):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-contact/search-contact.php"
        data = cls._search(url=url, keyword=keyword)
         
        return data

    def create(self):
        data = {}
        
        # Populate data for submission from Attributes
        for i in dir(self):
            if not i.startswith('_') and not callable(getattr(self, i)):
                data[i] = getattr(self, i)
        
        # Delete contact_id as this is a creation
        del data['contact_id']
        # Delete the id as there should be no id until after creation
        del data['id']

        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-contact/contact.php"
        data = self._create(url, data)
        logger.debug(data)
        self.contact_id = data['contact_id']
       

class Supply(BaseTRModelMixin):
    pass


class PurchaseOrder(BaseTRModelMixin):
    reference = ""
    date = datetime.now()
    invoice_note = ""
    payment_term = "cash"
    company_format = "PO"
    document_number = ""
    discount = "0"
    tax = "7%"
    total = ""
    grand_total = ""
    tax_option = "ex"
    url = ""
    status = "New"
    staff = ""
    department = ""
    project = ""
    customer = {}
    products = []

    @classmethod
    def search(cls, keyword):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-po/search-po.php"
        data = cls._search(url=url, keyword=keyword)
         
        return data
    
    @classmethod
    def retrieve(cls, id):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-po/retrieve-po.php"
        data = cls._retrieve(url, id)

        return data

    def create(self):
        """Create a new purchase order in the TRCloud Accounting system"""
        data = {}
        for i in dir(self):
            if not i.startswith('_') and not callable(getattr(self, i)):
                data[i] = getattr(self, i)
            
        print data
       


class Quotation(BaseTRModelMixin):
    
    @classmethod
    def search(cls, keyword):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-revenue/search-invoice.php"
        data = cls._search(url=url, keyword=keyword)
         
        return data
    
    @classmethod
    def retrieve(cls, id):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-quotation/retrieve-quotation.php"
        data = cls._retrieve(url, id)

        return data

    def _create_in_trcloud(self):
        pass
        # Reconcile customer with TRCloud

        # Prepare the data package

        # Convert to JSON

        # Send the data to TRCloud endpoint for Alinea

    def _update_in_trcloud(self):
        pass
        # Reconcile customer with TRCloud

        # Prepare the data package

        # Convert to JSON

        # Send the data to TRCloud endpoint for Alinea


class TRSalesOrder(BaseTRModelMixin):
    id = ""
    document_number = ""
    issue_date = ""
    delivery_date = ""
    payment_term = "Cash"
    company_format = "SO"
    tax_option = "ex"
    status = "New"
    customer_id = ""
    customer = {"add_contact": False,
                "update_contact": False}
    products = []
    
    @classmethod
    def search(cls, keyword):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-so/search-so.php"
        data = cls._search(url=url, keyword=keyword)
         
        return data
    
    @classmethod
    def retrieve(cls, id):
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-so/retrieve-so.php"
        data = cls._retrieve(url, id)

        return data

    def create(self):
        data = {}
        
        # Populate data for submission from Attributes
        for i in dir(self):
            if not i.startswith('_') and not callable(getattr(self, i)):
                data[i] = getattr(self, i)
        
        # Populate the customer data
        data["customer"] = self.customer
        
        data["product"] = self.products
        # Delete id as this is a creation
        del data['id']
        del data['customer_id']
        logger.debug(data)
        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-so/so.php"
        data = self._create(url, data)
        logger.debug(data)
        self.id = data['id']

    def update(self):
        data = {}
        
        # Populate data for submission from Attributes
        for i in dir(self):
            if not i.startswith('_') and not callable(getattr(self, i)):
                data[i] = getattr(self, i)
        
        # Populate the customer data
        data["customer"] = self.customer
        
        data["product"] = self.products
        

        url = "https://alinea.trcloud.co/extension/api-connector/end-point/engine-so/edit-so.php"
        data = self._create(url, data)
        logger.debug(data)
        self.id = data['id']

    def _update_in_trcloud(self):
        pass
        # Reconcile customer with TRCloud

        # Prepare the data package

        # Convert to JSON

        # Send the data to TRCloud endpoint for Alinea