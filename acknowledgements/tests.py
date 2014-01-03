"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from decimal import Decimal
import dateutil
import json

from django.contrib.auth.models import User, Permission, Group, ContentType
from tastypie.test import ResourceTestCase

from acknowledgements.models import Acknowledgement, Item, Pillow
from supplies.models import Fabric
from contacts.models import Customer, Address, Supplier
from products.models import Product
from auth.models import S3Object

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
                'price': 100000,
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
                          'depth': 760,
                          'height': 320,
                          "fabric": {"id":1}}]}



        
                
    

class AcknowledgementResourceTest(ResourceTestCase):
    """"
    This tests the api acknowledgements:
    
    GET list:
    -get a list of objects
    -objects have items and items have pillows
    
    GET:
    -the acknowledgement has delivery date, order date
    customer, status, total, vat, employee, discount
    -the acknowledgement has a list of items.
    -The items have pillows and fabrics
    -pillows have fabrics
    -the items has dimensions, pillows, fabric, comments
    price per item
    
    POST:
    -create an acknowledgement that has delivery date, order date
    customer, status, total, vat, employee, discount, items
    -the items should have fabrics and pillows where appropriate
    """
    
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
        super(AcknowledgementResourceTest, self).setUp()
        
        self.ct = ContentType(app_label="acknowledgements")
        self.ct.save()
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        p = Permission(content_type=self.ct, codename="change_acknowledgement")
        p.save()
        p2 = Permission(content_type=self.ct, codename="add_acknowledgement")
        p2.save()
        self.user.user_permissions.add(p)
        self.user.user_permissions.add(p2)
        
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
        self.item = Item.create(acknowledgement=self.ack, **item_data)
        
        self.api_client.client.login(username="tester", password="pass")

    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)

    def test_get_list(self):
        """
        Tests getting the list of acknowledgements
        """
        #Get and verify the resp
        resp = self.api_client.get('/api/v1/acknowledgement', format='json',
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)

        #Verify the data sent
        resp_obj = self.deserialize(resp)
        self.assertIsNotNone(resp_obj['objects'])
        self.assertEqual(len(resp_obj['objects']), 1)
        self.assertEqual(len(resp_obj['objects'][0]['items']), 1)
        
    def test_get(self):
        """
        Tests getting the acknowledgement
        """
        #Get and verify the resp
        resp = self.api_client.get('/api/v1/acknowledgement/1', format='json',
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
       
        #Verify the data sent
        ack = self.deserialize(resp)
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 1)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['po_id'], '123-213-231')
        self.assertIsInstance(dateutil.parser.parse(ack['delivery_date']), datetime)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal(0))
        
    def test_post_with_discount(self):
        """
        Testing POSTing data to the api
        """
        #Apply a discount to the customer
        self.customer.discount = 50
        self.customer.save()
        
        #POST and verify the response
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.post('/api/v1/acknowledgement', format='json',
                                    data=base_ack,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = self.deserialize(resp)
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal(158500))
        self.assertEqual(len(ack['items']), 2)
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 2)
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertEqual(item1['fabric']['id'], 1)
        self.assertEqual(len(item1['pillows']), 4)
        self.assertEqual(Decimal(item1['unit_price']), Decimal(100000))
        self.assertEqual(Decimal(item1['total']), Decimal(200000))
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 3)
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        
    def test_post_without_vat(self):
        """
        Testing POSTing data to the api
        """
        #POST and verify the response
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.post('/api/v1/acknowledgement', format='json',
                                    data=base_ack,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = self.deserialize(resp)
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(len(ack['items']), 2)
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 2)
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertEqual(item1['fabric']['id'], 1)
        self.assertEqual(len(item1['pillows']), 4)
        self.assertEqual(Decimal(item1['unit_price']), Decimal(100000))
        self.assertEqual(Decimal(item1['total']), Decimal(200000))
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 3)
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        
    def test_post_with_vat(self):
        """
        Testing POSTing data to the api if there
        is vat
        """
        #POST and verify the response
        ack_data = base_ack.copy()
        ack_data['vat'] = 7
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.post('/api/v1/acknowledgement', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = self.deserialize(resp)
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 7)
        self.assertEqual(Decimal(ack['total']), Decimal(339190.00))
        self.assertEqual(len(ack['items']), 2)
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 2)
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertEqual(item1['fabric']['id'], 1)
        self.assertEqual(len(item1['pillows']), 4)
        self.assertEqual(Decimal(item1['unit_price']), Decimal(100000))
        self.assertEqual(Decimal(item1['total']), Decimal(200000))
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 3)
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        #Tests links to document
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        
    def test_post_with_vat_and_discount(self):
        """
        Testing POSTing data to the api if there
        is vat
        """
        #Set customer discount
        self.customer.discount = 50
        self.customer.save()
        
        #POST and verify the response
        ack_data = base_ack.copy()
        ack_data['vat'] = 7
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.post('/api/v1/acknowledgement', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = self.deserialize(resp)
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 7)
        self.assertEqual(Decimal(ack['total']), Decimal(169595))
        self.assertEqual(len(ack['items']), 2)
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 2)
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertEqual(item1['fabric']['id'], 1)
        self.assertEqual(len(item1['pillows']), 4)
        self.assertEqual(Decimal(item1['unit_price']), Decimal(100000))
        self.assertEqual(Decimal(item1['total']), Decimal(200000))
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 3)
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        #Tests links to document
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        
    def test_put(self):
        """
        Test making a PUT call
        """
        ack_data = base_ack.copy()
        ack_data['delivery_date'] = datetime.now()
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.put('/api/v1/acknowledgement/1', 
                                   format='json',
                                   data=ack_data,
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        self.assertEqual(Acknowledgement.objects.count(), 1)
        
        #Validate the change
        ack = self.deserialize(resp)
        self.assertEqual(dateutil.parser.parse(ack['delivery_date']), ack_data['delivery_date'])

    def test_delete(self):
        """
        Test making a DELETE call
        """
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/acknowledgement/1',
                                      format='json',
                                      authentication=self.get_credentials())
        self.assertEqual(Acknowledgement.objects.count(), 1)
        self.assertHttpMethodNotAllowed(resp)
        
        
class TestItemResource(ResourceTestCase):
    def setUp(self):
        """
        Sets up environment for tests
        """
        super(TestItemResource, self).setUp()
        
        self.create_user()
        
        self.api_client.client.login(username='test', password='test')
        
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
        self.item_data = {'id': 1,
                     'quantity': 1,
                     'is_custom_size': True,
                     'width': 1500,
                     "fabric": {"id":1}}
        self.item = Item.create(acknowledgement=self.ack, **self.item_data)
        
    def create_user(self):
        self.user = User.objects.create_user('test', 'test@yahoo.com', 'test')
        self.ct = ContentType(app_label='acknowledgements')
        self.ct.save()
        perm = Permission(content_type=self.ct, codename='change_item')
        perm.save()
        self.user.user_permissions.add(perm)
        perm = Permission(content_type=self.ct, codename='change_fabric')
        perm.save()
        self.user.user_permissions.add(perm)
        self.assertTrue(self.user.has_perm('acknowledgements.change_item'))
        return self.user
        
    def test_get_list(self):
        """
        Tests getting a list of items via GET
        """
        #Tests the get
        resp = self.api_client.get('/api/v1/acknowledgement-item')
        self.assertHttpOK(resp)
        
        #Tests the resp
        resp_obj = self.deserialize(resp)
        self.assertIn("objects", resp_obj)
        self.assertEqual(len(resp_obj['objects']), 1)
        
    def test_get(self):
        """
        Tests getting an item via GET
        """
        #Tests the resp
        resp = self.api_client.get('/api/v1/acknowledgement-item/1')
        self.assertHttpOK(resp)
        
    def test_failed_create(self):
        """
        Tests that when attempting to create via POST
        it is returned as unauthorized
        """
        resp = self.api_client.post('/api/v1/acknowledgement-item/', format='json',
                                    data=self.item_data)
        self.assertHttpMethodNotAllowed(resp)
        
    def test_update(self):
        """
        Tests updating the item via PUT
        """
        modified_item_data = self.item_data.copy()
        modified_item_data['fabric'] = {'id': 2}
        modified_item_data['width'] = 888
        
        #Sets current fabric
        self.assertEqual(Item.objects.all()[0].fabric.id, 1)
        
        #Tests the response
        resp = self.api_client.put('/api/v1/acknowledgement-item/1', format='json',
                                   data=modified_item_data)
        self.assertHttpOK(resp)
        self.assertEqual(Item.objects.all()[0].fabric.id, 2)
        
        #Tests the data returned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['fabric']['id'], 2)
        self.assertEqual(obj['width'], 888)
        self.assertEqual(obj['quantity'], 1)
