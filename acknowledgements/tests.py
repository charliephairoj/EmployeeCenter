"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from decimal import Decimal
import dateutil
import json
import logging
import unittest
import copy
import subprocess

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission, Group, ContentType
from rest_framework.test import APIRequestFactory, APITestCase, APIClient

from acknowledgements.models import Acknowledgement, Item, Pillow
from supplies.models import Fabric, Reservation, Log
from contacts.models import Customer, Address, Supplier
from products.models import Product
from media.models import S3Object
from projects.models import Project


base_delivery_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_customer = {'id': 1,
                 'first_name': "John",
                 "last_name": "Smith",
                 'name': "John Smith",
                 'fax': '09223',
                 'telephone': '234234',
                 'notes': 'hi',
                 'email': 'ok@yahoo.com',
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
base_ack = {'customer': base_customer,
            'po_id': '123-213-231',
            'vat': 0,
            'delivery_date': base_delivery_date.isoformat(),
            'employee': {'id': 1},
            #New Project to be created
            'project': {'codename': 'Ladawan1'},
            'remarks': 'h',
            'shipping_method': 'h',
            'fob': 'h',
            'items': [
                       #Item 1:
                       #Complete upholstery with pillows and fabrics,
                       #and product assigned via the 'id'
                       {'id': 1,
                       'description': 'Test Sofa Max',
                       'quantity': 2,
                       'fabric': {'id':1},
                       'fabric_quantity': 10,
                       'pillows':[{"type": "back",
                                   "fabric": {'id': 1}},
                                  {"type": "back",
                                   "fabric": {'id': 1}},
                                  {"type": "back",
                                   "fabric": {'id': 2}},
                                  {"type": "accent",
                                   "fabric": {'id': 2}},
                                  {"type": "accent"}]},
                         #Item 2:
                         #Table product with custom size
                         {'id': 1,
                          'description': 'High Gloss Table',
                          'quantity': 1,
                          'is_custom_size': True,
                          'width': 1500,
                          'depth': 760,
                          'height': 320,
                          'fabric_quantity': 5,
                          "fabric": {'id': 1}},
                         #item 3:
                         #Custom item with no product
                         {"description": "test custom item",
                          "custom_price": 0,
                          'width': 1,
                          'is_custom_item': True,
                          "quantity": 1}]}
                          
                         


logger = logging.getLogger(__name__)                
    

class AcknowledgementResourceTest(APITestCase):
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
        customer = copy.deepcopy(base_customer)
        del customer['id']
        self.customer = Customer(**customer)
        self.customer.save()
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.address = Address(address1="Jiggle", contact=self.customer)
        self.address.save()
        
        #Create a product to add
        self.product = Product.create(self.user, **base_product)
        self.product.save()
        
        #Create custom product
        self.custom_product = Product()
        self.custom_product.id = 10436
        self.custom_product.save()
        
        self.fabric = Fabric.create(**base_fabric)
        f_data = base_fabric.copy()
        f_data["pattern"] = "Stripe"
        self.fabric2 = Fabric.create(**f_data)
        
        #Create custom product
        self.custom_product = Product.create(self.user, description="Custom Custom", id=10436,
                                             width=0, depth=0, height=0,
                                             price=0, wholesale_price=0, retail_price=0)
        self.custom_product.id = 10436
        self.custom_product.save()
        
        self.image = S3Object(key='test', bucket='test')
        self.image.save()
        
        #Create acknowledgement
        ack_data = base_ack.copy()
        del ack_data['customer']
        del ack_data['items']
        del ack_data['employee']
        del ack_data['project']
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
        item_data = {'is_custom': True,
                     'description': 'F-04 Sofa',
                     'quantity': 3}
        self.item2 = Item.create(acknowledgement=self.ack, **item_data)
        self.client.login(username="tester", password="pass")

    def get_credentials(self):
        return None#self.create_basic(username=self.username, password=self.password)
        
            
    def test_get_list(self):
        """
        Tests getting the list of acknowledgements
        """
        #Get and verify the resp
        resp = self.client.get('/api/v1/acknowledgement/')
        self.assertEqual(resp.status_code, 200, msg=resp)

        #Verify the data sent
        resp_obj = resp.data
        self.assertIsNotNone(resp_obj['results'])
        self.assertEqual(len(resp_obj['results']), 1)
        self.assertEqual(len(resp_obj['results'][0]['items']), 2)
    
    def test_get(self):
        """
        Tests getting the acknowledgement
        """
        #Get and verify the resp
        resp = self.client.get('/api/v1/acknowledgement/1/')
        self.assertEqual(resp.status_code, 200, msg=resp)

        #Verify the data sent
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 1)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['po_id'], '123-213-231')
        self.assertEqual(dateutil.parser.parse(ack['delivery_date']), base_delivery_date)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal(0))
    
    def xtest_post_dr_vs_pci(self):
        """
        Test POSTING ack with company as 'Dellarobbia Thailand' vs 'Pacific Carpet'
        """
        logger.debug("\n\n Testing creating acknowledgement with diferring companies\n")
        ack1_data = copy.deepcopy(base_ack)
        ack1_data['company'] = 'Dellarobbia Thailand'
        ack
        
    def test_post_with_discount(self):
        """
        Testing POSTing data to the api
        """
        
        logger.debug("\n\n Testing creating acknowledgement with a discount \n")
        #Apply a discount to the customer
        self.customer.discount = 50
        self.customer.save()
                
        #POST and verify the response
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/',  
                                data=base_ack,
                                format='json')

        #Verify that http response is appropriate
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        #Verify that an acknowledgement is created in the system
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal(158500))
        self.assertEqual(len(ack['items']), 3)
        self.assertIn('project', ack)
        self.assertEqual(ack['project']['id'], 1)
        self.assertEqual(ack['project']['codename'], 'Ladawan1')
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
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
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), 0)
        
        #Tests links to document
        """
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
        """
        
        #Tests the acknowledgement in the database
        root_ack = Acknowledgement.objects.get(pk=2)
        logger.debug(root_ack.project)
        self.assertEqual(root_ack.id, 2)
        self.assertEqual(root_ack.items.count(), 3)
        self.assertIsInstance(root_ack.project, Project)
        self.assertEqual(root_ack.project.id, 1)
        self.assertEqual(root_ack.project.codename, "Ladawan1")
        root_ack_items = root_ack.items.all()
        item1 = root_ack_items[0]
        item2 = root_ack_items[1]
        item3 = root_ack_items[2]
        self.assertEqual(item1.acknowledgement.id, 2)
        self.assertEqual(item1.description, 'Test Sofa Max')
        self.assertEqual(item1.quantity, 2)
        self.assertEqual(item1.width, 1000)
        self.assertEqual(item1.height, 320)
        self.assertEqual(item1.depth, 760)
        self.assertFalse(item1.is_custom_item)
        self.assertFalse(item1.is_custom_size)
        self.assertEqual(item2.acknowledgement.id, 2)
        self.assertEqual(item2.description, 'High Gloss Table')
        self.assertEqual(item2.width, 1500)
        self.assertEqual(item2.height, 320)
        self.assertEqual(item2.depth, 760)
        self.assertTrue(item2.is_custom_size)
        self.assertFalse(item2.is_custom_item)
        self.assertEqual(item3.acknowledgement.id, 2)
        self.assertEqual(item3.description, 'test custom item')
        self.assertEqual(item3.width, 1)
        self.assertTrue(item3.is_custom_item)
        self.assertEqual(item3.quantity, 1)
        
        #Test Fabric Log
        self.assertEqual(Log.objects.filter(acknowledgement_id=root_ack.id).count(), 1)
        log = Log.objects.get(acknowledgement_id=root_ack.id)
        self.assertEqual(log.quantity, Decimal('25'))
        self.assertEqual(log.action, 'RESERVE')
        self.assertEqual(log.acknowledgement_id, '2')
        self.assertEqual(log.message, 'Reserve 25m of Pattern: Max, Col: charcoal for Ack#2')
        
    def test_post_with_custom_image(self):
        """
        Testing POSTing data to the api with custom item with custom image
        """
        
        logger.debug("\n\n Testing creating acknowledgement with a custom image \n")
        #Apply a discount to the customer
        ack = copy.deepcopy(base_ack)
        ack['items'][2]['image'] = {'id': 1}
                
        #POST and verify the response
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/',  
                                data=ack,
                                format='json')

        #Verify that http response is appropriate
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        #Verify that an acknowledgement is created in the system
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal(317000))
        self.assertEqual(len(ack['items']), 3)
        self.assertIn('project', ack)
        self.assertEqual(ack['project']['id'], 1)
        self.assertEqual(ack['project']['codename'], 'Ladawan1')
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
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
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), 0)
        self.assertIsNotNone(item3['image'])
        self.assertIn('url', item3['image'])
        
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
        logger.debug(ack['pdf']['confirmation'])
        print "\n\n\n"
        
        #Tests the acknowledgement in the database
        root_ack = Acknowledgement.objects.get(pk=2)
        logger.debug(root_ack.project)
        self.assertEqual(root_ack.id, 2)
        self.assertEqual(root_ack.items.count(), 3)
        self.assertIsInstance(root_ack.project, Project)
        self.assertEqual(root_ack.project.id, 1)
        self.assertEqual(root_ack.project.codename, "Ladawan1")
        root_ack_items = root_ack.items.all()
        item1 = root_ack_items[0]
        item2 = root_ack_items[1]
        item3 = root_ack_items[2]
        self.assertEqual(item1.acknowledgement.id, 2)
        self.assertEqual(item1.description, 'Test Sofa Max')
        self.assertEqual(item1.quantity, 2)
        self.assertEqual(item1.width, 1000)
        self.assertEqual(item1.height, 320)
        self.assertEqual(item1.depth, 760)
        self.assertFalse(item1.is_custom_item)
        self.assertFalse(item1.is_custom_size)
        self.assertEqual(item2.acknowledgement.id, 2)
        self.assertEqual(item2.description, 'High Gloss Table')
        self.assertEqual(item2.width, 1500)
        self.assertEqual(item2.height, 320)
        self.assertEqual(item2.depth, 760)
        self.assertTrue(item2.is_custom_size)
        self.assertFalse(item2.is_custom_item)
        self.assertEqual(item3.acknowledgement.id, 2)
        self.assertEqual(item3.description, 'test custom item')
        self.assertEqual(item3.width, 1)
        self.assertTrue(item3.is_custom_item)
        self.assertEqual(item3.quantity, 1)
    
    def test_post_without_vat(self):
        """
        Testing POSTing data to the api
        """
        logger.debug("\n\n Testing creating acknowledgement without vat \n")
        
        #POST and verify the response
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/', format='json',
                                    data=base_ack,
                                    authentication=self.get_credentials())

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal('317000'))
        self.assertEqual(len(ack['items']), 3)
        self.assertIn('project', ack)
        self.assertEqual(ack['project']['id'], 1)
        self.assertEqual(ack['project']['codename'], 'Ladawan1')
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
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
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), 0)
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
    
    def test_post_with_vat(self):
        """
        Testing POSTing data to the api if there
        is vat
        """
        logger.debug("\n\n Testing creating acknowledgement with vat \n")
        
        #Altering replication of base ack data
        ack_data = base_ack.copy()
        ack_data['vat'] = 7
        
        #Verifying current number of acknowledgements in database
        self.assertEqual(Acknowledgement.objects.count(), 1)
        
        resp = self.client.post('/api/v1/acknowledgement/', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
    
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 7)
        self.assertEqual(Decimal(ack['total']), Decimal(339190.00))
        self.assertEqual(len(ack['items']), 3)
        self.assertIn('project', ack)
        self.assertEqual(ack['project']['id'], 1)
        self.assertEqual(ack['project']['codename'], 'Ladawan1')
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
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
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), 0)
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
    
    def test_post_with_vat_and_discount(self):
        """
        Testing POSTing data to the api if there
        is vat
        """
        logger.debug("\n\n Testing creating acknowledgement with a discount and vat \n")
        
        #Set customer discount
        self.customer.discount = 50
        self.customer.save()
        
        #POST and verify the response
        ack_data = base_ack.copy()
        ack_data['vat'] = 7
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
        

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 7)
        self.assertEqual(Decimal(ack['total']), Decimal('169595.000'))
        self.assertEqual(len(ack['items']), 3)
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
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
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal(117000))
        self.assertEqual(Decimal(item2['total']), Decimal(117000))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), 0)
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
        
    def test_post_with_custom_price(self):
        """
        Test creating a custom price for all three item types
        """
        logger.debug("\n\n Testing creating acknowledgement with custom prices for all items \n")
                
        #POST and verify the response
        ack_data = copy.deepcopy(base_ack)
        ack_data['items'][0]['custom_price'] = 100
        ack_data['items'][1]['custom_price'] = 200
        ack_data['items'][2]['custom_price'] = 300

        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
        

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal('700.00'))
        self.assertEqual(len(ack['items']), 3)
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertEqual(item1['fabric']['id'], 1)
        self.assertEqual(len(item1['pillows']), 4)
        self.assertEqual(Decimal(item1['unit_price']), Decimal('100'))
        self.assertEqual(Decimal(item1['total']), Decimal('200'))
        
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal('200'))
        self.assertEqual(Decimal(item2['total']), Decimal('200'))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        self.assertEqual(Decimal(item3['unit_price']), Decimal('300'))
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
        
    def test_post_where_first_item_has_no_fabric(self):
        """
        Test creating a custom price for all three item types
        """
        logger.debug("\n\n Testing creating acknowledgement with custom prices for all items \n")
                
        #POST and verify the response
        ack_data = copy.deepcopy(base_ack)
        del ack_data['items'][0]['fabric']
        del ack_data['items'][0]['pillows'][0]['fabric']

        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.post('/api/v1/acknowledgement/', format='json',
                                    data=ack_data,
                                    authentication=self.get_credentials())
        

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Acknowledgement.objects.count(), 2)
        
        #Verify the resulting acknowledgement
        #that is returned from the post data
        ack = resp.data
        self.assertIsNotNone(ack)
        self.assertEqual(ack['id'], 2)
        self.assertEqual(ack['customer']['id'], 1)
        self.assertEqual(ack['employee']['id'], 1)
        self.assertEqual(ack['vat'], 0)
        self.assertEqual(Decimal(ack['total']), Decimal('317000'))
        self.assertEqual(len(ack['items']), 3)
        
        #Test standard sized item 
        item1 = ack['items'][0]
        self.assertEqual(item1['id'], 3)
        self.assertEqual(item1['description'], 'Test Sofa Max')
        self.assertEqual(item1['quantity'], 2)
        self.assertFalse(item1['is_custom_size'])
        self.assertFalse(item1['is_custom_item'])
        self.assertEqual(item1['width'], 1000)
        self.assertEqual(item1['height'], 320)
        self.assertEqual(item1['depth'], 760)
        self.assertIsNone(item1['fabric'])
        self.assertEqual(len(item1['pillows']), 5)
        self.assertEqual(Decimal(item1['unit_price']), Decimal('100000'))
        self.assertEqual(Decimal(item1['total']), Decimal('200000'))
        
        #Test custom sized item
        item2 = ack['items'][1]
        self.assertEqual(item2['id'], 4)
        self.assertEqual(item2['description'], 'High Gloss Table')
        self.assertEqual(item2['quantity'], 1)
        self.assertTrue(item2['is_custom_size'])
        self.assertFalse(item2['is_custom_item'])
        self.assertEqual(item2['width'], 1500)
        self.assertEqual(item2['height'], 320)
        self.assertEqual(item2['depth'], 760)
        self.assertEqual(item2['fabric']['id'], 1)
        self.assertEqual(Decimal(item2['unit_price']), Decimal('117000'))
        self.assertEqual(Decimal(item2['total']), Decimal('117000'))
        
        #Test custom item with width
        item3 = ack['items'][2]
        self.assertEqual(item3['width'], 1)
        self.assertEqual(item3['description'], 'test custom item')
        self.assertTrue(item3['is_custom_item'])
        self.assertEqual(item3['quantity'], 1)
        
        #Tests links to document
        self.assertIsNotNone(ack['pdf'])
        self.assertIsNotNone(ack['pdf']['acknowledgement'])
        self.assertIsNotNone(ack['pdf']['production'])
        self.assertIsNotNone(ack['pdf']['confirmation'])
    
    @unittest.skip('currently not allowed')    
    def test_put(self):
        """
        Test making a PUT call
        """
        logger.debug("\n\n Testing updating via put \n")
        
        ack_data = base_ack.copy()
        ack_data['items'][0]['id'] = 1
        del ack_data['items'][0]['pillows'][-1]
        ack_data['items'][1]['id'] = 2
        ack_data['items'][1]['description'] = 'F-04 Sofa'
        ack_data['items'][1]['is_custom_item'] = True
        del ack_data['items'][2]
        ack_data['delivery_date'] = datetime.now()
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.put('/api/v1/acknowledgement/1/', 
                                   format='json',
                                   data=ack_data,
                                   authentication=self.get_credentials())
        logger.debug(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Acknowledgement.objects.count(), 1)
        
        #Validate the change
        ack = resp.data
        #self.assertEqual(dateutil.parser.parse(ack['delivery_date']), ack_data['delivery_date'])
        logger.debug(ack['items'][0]['pillows'])
        #Tests ack in database
        ack = Acknowledgement.objects.get(pk=1)
        items = ack.items.all()
            
        item1 = items[0]
        self.assertEqual(item1.description, 'Test Sofa Max')
        self.assertEqual(item1.pillows.count(), 3)

        item2 = items[1]
        self.assertEqual(item2.description, 'F-04 Sofa')
        self.assertTrue(item2.is_custom_item)
    
    def test_changing_delivery_date(self):
        """
        Test making a PUT call
        """
        logger.debug("\n\n Testing updating via put \n")
        
        d = datetime.now()
        
        ack_data = base_ack.copy()
       
        ack_data['delivery_date'] = d
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.put('/api/v1/acknowledgement/1/', 
                                   format='json',
                                   data=ack_data,
                                   authentication=self.get_credentials())

        self.assertEqual(resp.status_code, 200, msg=resp)
        
        ack = resp.data
        #logger.debug(ack['delivery_date'])
        #d1 = datetime.strptime(ack['delivery_date'])
        
        #self.assertEqual(d1.date(), d.date())
        
        ack = Acknowledgement.objects.all()[0]
        self.assertEqual(ack.delivery_date.date(), d.date())
        
    #@unittest.skip('ok')    
    def test_delete(self):
        """
        Test making a DELETE call
        
        'Delete' in this model has been overridden so that no acknowledgement 
        is truly deleted. Instead the 'delete' column in the database is marked 
        as true
        """
        self.assertEqual(Acknowledgement.objects.count(), 1)
        resp = self.client.delete('/api/v1/acknowledgement/1/',
                                      authentication=self.get_credentials())

        self.assertEqual(Acknowledgement.objects.count(), 1)
  
  
@unittest.skip('i')     
class TestItemResource(APITestCase):
    def setUp(self):
        """
        Sets up environment for tests
        """
        super(TestItemResource, self).setUp()
        
        self.create_user()
        
        self.client.login(username='test', password='test')
        
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
        del ack_data['project']
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
        resp = self.client.get('/api/v1/acknowledgement-item')
        #self.assertHttpOK(resp)
        
        #Tests the resp
        resp_obj = self.deserialize(resp)
        self.assertIn("objects", resp_obj)
        self.assertEqual(len(resp_obj['objects']), 1)
        
    def test_get(self):
        """
        Tests getting an item via GET
        """
        #Tests the resp
        resp = self.client.get('/api/v1/acknowledgement-item/1')
        #self.assertHttpOK(resp)
        
    def test_failed_create(self):
        """
        Tests that when attempting to create via POST
        it is returned as unauthorized
        """
        resp = self.client.post('/api/v1/acknowledgement-item/', format='json',
                                    data=self.item_data)
        #self.assertHttpMethodNotAllowed(resp)
        
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
        resp = self.client.put('/api/v1/acknowledgement-item/1', format='json',
                                   data=modified_item_data)
        #self.assertHttpOK(resp)
        self.assertEqual(Item.objects.all()[0].fabric.id, 2)
        
        #Tests the data returned
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['fabric']['id'], 2)
        self.assertEqual(obj['width'], 888)
        self.assertEqual(obj['quantity'], 1)
