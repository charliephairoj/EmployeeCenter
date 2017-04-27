from __future__ import unicode_literals
import logging
import requests
import json
import hashlib
import time
import math

from django.db import models


logger = logging.getLogger(__name__)


class BaseTRModelMixin(object):
    @classmethod
    def _prepare_body_for_request(cls, data):
        timestamp = str(int(math.floor(time.time())))
        predata = {
            "company_id":"5",
            "passkey":"b01ebdb1ce5a28f803de6973cd833fb4",
            "securekey": hashlib.md5("ce5a28" +"t" + timestamp).hexdigest(),
            "timestamp": timestamp,
        }

        # Merge the request keys and information with the body data
        data.update(predata)

        # Transform data into JSON string per specification
        body = {"json" : json.dumps(data)}

        return body
    
    @classmethod
    def _parse_response(cls, response):
        """JSON parses the response and returns if the post was a success"""

        # Change response from text to data
        data = json.loads(response.text)
        print data
        # If the response is a success return it
        if int(data['success']) == 1:
            if 'head' in data:
                return data['head']
            elif 'result' in data:
                return data['result']
        else:
            pass

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

class Quotation(BaseTRModelMixin, models.Model):
    trcloud_id = models.IntegerField()
    
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


class SaleOrder(BaseTRModelMixin, models.Model):
    trcloud_id = models.IntegerField()
    issue_date = models.DateField()
    payment_term = models.TextField()
    company_format = models.TextField()
    
    
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