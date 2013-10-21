"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from decimal import Decimal
import random
import json

from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User, Permission

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Foam, SupplyLog
from auth.models import S3Object


base_supplier = {"name": "Test Supplier",
                 "currency": "USD"}
base_address = {"address": {"address1": "22471 Sunbroon",
                            "city": "Mission Viejo",
                            "territory": "CA",
                            "country": "USA",
                            "zipcode": "92839"}}

base_supply = {"description": "test",
               "width": 100,
               "depth": 200,
               "height": 300,
               "purchasing_units": "ml",
               "reference": "A2234",
               "cost": 100,
               "quantity": 10.8,
               "supplier": {"id": 1}}

base_fabric = base_supply.copy()
base_fabric.update({"pattern": "Max",
                    "color": "Hot Pink"})


def create_user(block_permissions=[]):
    """
    Creates a user
    """
    user = User.objects.create_user('test{0}'.format(random.randint(1, 100000)), 'test', 'test')
    user
    user.is_staff = True
    user.save()

    #Add permissions
    for p in Permission.objects.all():
        if p.codename not in block_permissions:
            user.user_permissions.add(p)
    return user
     
            
class SupplyViewTest(TestCase):
    def setUp(self):
        """
        Set up the view 
        
        -login the user
        """
        
        User.objects.create_user('test', 'test', 'test')
        self.supplier = Supplier(**base_supplier)
        self.supplier.save()
        self.supply = Supply.create(**base_supply)
        self.supply2 = Supply.create(**base_supply)
        self.client.login(username='test', password='test')

    def test_get(self):
        """
        Tests that a standard get call works
        """
        
        #Testing standard GET
        response = self.client.get('/supply')
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(content), 2)
        self.assertIsNotNone(response.content)
        
        #Testing get with pk
        response = self.client.get('/supply/2')
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.content)
        
    def test_post(self):
        """
        Tests posting to the server
        """
        response = self.client.post('/supply', base_supply)
        content = response.content
        self.assertEqual(response.status_code, 201)


