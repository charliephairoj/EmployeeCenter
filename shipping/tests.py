"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from decimal import Decimal
import dateutil
 
from django.test import TestCase
from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase

from acknowledgements.models import Acknowledgement, Item as AckItem
from shipping.models import Shipping
from supplies.models import Fabric
from products.models import Product
from contacts.models import Customer, Supplier, Address


base_delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_customer = {'first_name': "John",
                 "last_name": "Smith",
                 "type": "Dealer",
                 "currency": "USD"}
base_supplier = {"name": "Test Supplier",
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
                "retail_price": 100000,
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


class ShippingResourceTest(ResourceTestCase):
    
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
        
        #Create supplier, customer and addrss
        self.customer = Customer(**base_customer)
        self.customer.save()
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        
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
    
    def create_shipping(self):
        #create a shipping item
        self.shipping = Shipping.create(acknowledgement={'id': 1}, customer={'id': 1},
                                        user=self.user, delivery_date=base_delivery_date,
                                        items=[{'id': 1}, {'id': 2}])
        self.shipping.save()
        
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Tests getting a list of objects via GET
        """
        #Create a shipping to retrieve
        self.create_shipping()
        
        resp = self.api_client.get('/api/v1/shipping', format='json', authentication=self.get_credentials())
        self.assertHttpOK(resp)
        
        #Validate the resources returned
        resp_obj = self.deserialize(resp)
        self.assertEqual(len(resp_obj['objects']), 1)
        
    def test_get(self):
        """
        Tests getting an object via GET
        """
        self.create_shipping()
        
        #Test the resp
        resp = self.api_client.get('/api/v1/shipping/1', format='json', 
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        
        #Validate the object
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertIn("customer", obj)
        self.assertEqual(obj['customer']['id'], 1)
    
    def test_post(self):
        """
        Tests creating a resource via POST
        """
        #self.skipTest("intensive")
        #Validate the resp and obj creation
        self.assertEqual(Shipping.objects.count(), 0)
        resp = self.api_client.post('/api/v1/shipping', format='json',
                                    authentication=self.get_credentials(),
                                    data={'acknowledgement': {'id': 1},
                                          'delivery_date': base_delivery_date,
                                          'employee': {'id': self.user.id},
                                          'items': [{'id': 1}, {'id': 2}]})
        self.assertHttpCreated(resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #validate the object returned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertIn('customer', obj)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertIn('last_modified', obj)
        self.assertIn('time_created', obj)
        
    def test_put(self):
        """
        Tests updating a resource via PUT
        """
        self.create_shipping()
        self.assertEqual(Shipping.objects.count(), 1)
        resp = self.api_client.put('/api/v1/shipping/1', format='json',
                                   authentication=self.get_credentials(),
                                   data={'delivery_date':base_delivery_date,
                                         'comments': 'test'})
        self.assertHttpOK(resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #Validate the obj
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertEqual(obj['comments'], 'test')
        
    def test_patch(self):
        """
        Tests updating a resoure via the PATCH
        """
        self.create_shipping()
        self.assertEqual(Shipping.objects.count(), 1)
        resp = self.api_client.patch('/api/v1/shipping/1', format='json',
                                   authentication=self.get_credentials(),
                                   data={'comments': 'test'})
        self.assertHttpAccepted(resp)
        self.assertEqual(Shipping.objects.count(), 1)
        
        #Validate the obj
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['customer']['id'], 1)
        self.assertEqual(obj['comments'], 'test')
        
    def test_delete(self):
        """
        Tests deleting a resource via DELETE
        """
        self.create_shipping()
        self.assertEqual(Shipping.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/shipping/1', format='json',
                                      authentication=self.get_credentials())
        self.assertHttpAccepted(resp)
        self.assertEqual(Shipping.objects.count(), 0)
        
        
            
        
        
        