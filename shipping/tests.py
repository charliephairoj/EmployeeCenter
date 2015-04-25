#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from decimal import Decimal
import dateutil
import subprocess
import logging

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from acknowledgements.models import Acknowledgement, Item as AckItem
from shipping.models import Shipping
from supplies.models import Fabric
from products.models import Product
from contacts.models import Customer, Supplier, Address
from projects.models import Project, Phase


logger = logging.getLogger(__name__)


base_delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_customer = {'first_name': "John",
                 "last_name": "Smith",
                 "type": "Dealer",
                 "currency": "USD"}
base_supplier = {"name": u"บริษัท แลนด์ แอนด์ เฮ้าส์ จำักัด (มหาชน)",
                 "id": 1,
                 "currency": "THB"}
base_fabric = {"pattern": "Max",
               "color": "charcoal",
               "reference": "A-2323",
               "quantity": 0,
               "unit_cost": 1.22,
               "supplier": {"id": 1}}
base_product = {"description": "test1",
                "width": 1000,
                "height": 320,
                "depth": 760,
                "price": 100000,
                "wholesale_price": 25000,
                "type": "upholstery",
                "collection": "Dellarobbia Thailand",
                "back_pillow": 4,
                "accent_pillow": 3,
                "id": 1}
base_ack = {'customer': {'id': 1},
            'po_id': '123-213-231',
            'vat': 0,
            'delivery_date': base_delivery_date.isoformat(),
            'employee': {'id': 1},
            'items': [{'id': 1,
                          'quantity': 2,
                          'fabric': {"id": 1},
                          'pillows':[{"type": "back",
                                      "fabric": {"id": 1}},
                                      {"type": "back",
                                       "fabric": {"id": 2}},
                                     {"type": "back",
                                      "fabric": {"id": 1}},
                                     {"type": "accent",
                                      "fabric": {"id": 2}},
                                     {"type": "accent"}]},
                         {'id': 1,
                          'quantity': 1,
                          'is_custom_size': True,
                          'width': 1500,
                          "fabric": {"id":1}}]}


class ShippingResourceTest(APITestCase):
    
    def setUp(self):        
        """
        Set up for the Acknowledgement Test

        Objects created:
        -User
        -Customer
        -Supplier
        -Address
        -product
        -2 fabrics

        After Creating all the needed objects for the Acknowledgement, 
        test that all the objects have been made.
        """
        super(ShippingResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        self.user.save()
        
        self.client.login(username='tester', password='pass')
        
        #Create supplier, customer and addrss
        self.customer = Customer(**base_customer)
        self.customer.save()
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        
        #Create project
        self.project = Project.objects.create(codename="Ladawan")
        
        #Create phase
        self.phase = Phase.objects.create(description="Phase 1/6", project=self.project)
        
        #Create a product to add
        self.product = Product.create(self.user, **base_product)
        self.product.save()
        self.fabric = Fabric.create(**base_fabric)
        f_data = base_fabric.copy()
        f_data["pattern"] = "Stripe"
        self.fabric2 = Fabric.create(**f_data)
        
        #Create acknowledgement
        ack_data = base_ack.copy()
        del ack_data['customer']
        del ack_data['items']
        del ack_data['employee']
        self.ack = Acknowledgement(**ack_data)
        self.ack.customer = self.customer
        self.ack.employee = self.user
        self.ack.save()
        
        #Create an item
        item_data = {'id': 1,
                     'quantity': 1,
                     'is_custom_size': True,
                     'width': 1500,
                     "fabric": {"id":1}}
        self.item = AckItem.create(acknowledgement=self.ack, **item_data)
        
        #Create an item
        item_data = {'id': 1,
                     'quantity': 2,
                     'is_custom_size': True,
                     'width': 1500,
                     "fabric": {"id":1}}
        self.item2 = AckItem.create(acknowledgement=self.ack, **item_data)
    
    def create_shipping(self):
        #create a shipping item
        self.shipping = Shipping.create(acknowledgement={'id': 1}, customer={'id': 1},
                                        user=self.user, delivery_date=base_delivery_date,
                                        items=[{'id': 1}, {'id': 2}])
        self.shipping.save()
        
    def get_credentials(self):
        return None#self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Tests getting a list of objects via GET
        """
        self.skipTest('')
        #Create a shipping to retrieve
        self.create_shipping()
        
        resp = self.client.get('/api/v1/shipping/', format='json', authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 200)
        
        #Validate the resources returned
        resp_obj = resp.data
        self.assertEqual(len(resp_obj['objects']), 1)
        
    def test_get(self):
        """
        Tests getting an object via GET
        """
        self.skipTest('')
        self.create_shipping()
        
        #Test the resp
        resp = self.client.get('/api/v1/shipping/1/', format='json', 
                                   authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 200)
        
        #Validate the object
        obj = resp.data
        self.assertEqual(obj['id'], 1)
        self.assertIn("customer", obj)
        self.assertEqual(obj['customer']['id'], 1)
    
    def test_post_project_shipping(self):
        """
        Test creating a project packing list via POST
        """
        data = {'project': {'id': 1},
                'phase': {'id': 1},
                'items': [
                    {'description': 'TK 1/2'}
                ]}
                
        resp = self.client.post('/api/v1/shipping/', format='json', data=data)
        
        # Test client response
        self.assertEqual(resp.status_code, 201)
        
    def test_post_with_one_item(self):
        """
        Tests creating a resource via POST
        """
        #Validate the resp and obj creation
        self.assertEqual(Shipping.objects.count(), 0)
        shipping_data={'acknowledgement': {'id': 1},
                       'delivery_date': base_delivery_date,
                       'items': [{'id': 1,
                                  'description':'test1',
                                  'quantity': 1},
                                 {'id': 2}]}
        resp = self.client.post('/api/v1/shipping/', data=shipping_data, format='json')

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #validate the object returned
        obj = resp.data
        self.assertEqual(obj['id'], 1)
        self.assertIn('customer', obj)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertIn('last_modified', obj)
        self.assertIn('time_created', obj)
        self.assertEqual(len(obj['items']), 2)
        item1 = obj['items'][0]
        
        #Validate resource in the database
        shipping = Shipping.objects.get(pk=1)
        self.assertEqual(shipping.id, 1)
        self.assertEqual(shipping.customer.id, 1)
        self.assertEqual(shipping.items.count(), 2)
        
    def test_post_with_one_item(self):
        """
        Tests creating a resource via POST
        """
        #Validate the resp and obj creation
        self.assertEqual(Shipping.objects.count(), 0)
        shipping_data={'acknowledgement': {'id': 1},
                       'delivery_date': base_delivery_date,
                       'items': [{'id': 1,
                                  'description':'test1',
                                  'quantity': 1}]}
        resp = self.client.post('/api/v1/shipping/', data=shipping_data, format='json')

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #validate the object returned
        obj = resp.data
        self.assertEqual(obj['id'], 1)
        self.assertIn('customer', obj)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertIn('last_modified', obj)
        self.assertIn('time_created', obj)
        self.assertEqual(len(obj['items']), 1)
        item1 = obj['items'][0]
        
        #Validate resource in the database
        shipping = Shipping.objects.get(pk=1)
        self.assertEqual(shipping.id, 1)
        self.assertEqual(shipping.customer.id, 1)
        self.assertEqual(shipping.items.count(), 1)
                
    def test_put(self):
        """
        Tests updating a resource via PUT
        """
        self.skipTest('')
        self.create_shipping()
        self.assertEqual(Shipping.objects.count(), 1)
        resp = self.client.put('/api/v1/shipping/1/', format='json',
                                   authentication=self.get_credentials(),
                                   data={'delivery_date':base_delivery_date, 'acknowledgement': {'id': 1}})
        self.assertEqual(resp.status_code, 200, msg=resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #Validate the obj
        obj = resp.data
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertEqual(obj['comments'], 'test')
        
    def test_delete(self):
        """
        Tests deleting a resource via DELETE
        """
        self.skipTest('')
        self.create_shipping()
        self.assertEqual(Shipping.objects.count(), 1)
        resp = self.client.delete('/api/v1/shipping/1/', format='json',
                                      authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Shipping.objects.count(), 0)
        
        
            
        
        
        