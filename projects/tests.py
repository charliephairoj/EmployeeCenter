"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import dateutil
import unittest
import logging
import copy
from decimal import Decimal

from django.contrib.auth.models import User, Permission, ContentType
from django.conf import settings
from django.test import TestCase
from tastypie.test import ResourceTestCase
from rest_framework.test import APITestCase

from contacts.models import Customer
from supplies.models import Supply
from products.models import Product, Model, Configuration, Upholstery
from projects.models import Project, Room, Item, ProjectSupply, ItemSupply
from media.models import S3Object


logger = logging.getLogger(__name__)

base_customer = {"first_name": "John",
                 "last_name": "Smith",
                 "currency": "THB",
                 "email": "test@yahoo.com",
                 "telephone": "ok",
                 "addresses": [{"address1": "ok",
                             "city": "ok",
                             "territory": "ok",
                             "country": "thailand",
                             "zipcode": "9823-333"}]}
product_data = {"width": 100,
                "depth": 100,
                "height": 100,
                "description": "Test Product"}
base_due_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
base_project = {"reference": "S5",
                "address": {"address1": "8/10 Moo 4 Lam Lukka",
                            "city": "Lam Lukka",
                            "territory": "Pathum Thani",
                            "country": "Thailand",
                            "zipcode": "98233"},
                "customer": {"id": 1},
                "type": "Condominium",
                "due_date": base_due_date.isoformat(),
                "codename": "Haze"}
base_room = {"project": {"id": 1},
             "reference": "B-01",
             "description": "Master Bedroom"}
base_item = {"room": {"id": 1},
             "type": "Build-In",
             "reference": "F-01",
             "description": "TV Cabinet"}


class ProjectResourceTestCase(APITestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        super(ProjectResourceTestCase, self).setUp()
        
        self.create_user()
        #self.api_client.client.login(username='test', password='test')
        
        #self.customer = Customer.create(**base_customer)
        #self.project = Project.create(**base_project)
        self.project = Project(codename="Ladawan")
        self.project.save()
        self.supply = Supply(description='Grommet')
        self.supply.save()
        self.supply2 = Supply(description='Hinge')
        self.supply2.save()
        self.project_supply = ProjectSupply(supply=self.supply,
                                            project=self.project,
                                            quantity=2)
        self.project_supply.save()
    
    def create_user(self):
        self.user = User.objects.create_user('test', 'test@yahoo.com', 'test')
        self.ct = ContentType(app_label='projects')
        self.ct.save()
        #self._create_and_add_permission('view_cost', self.user)
        self._create_and_add_permission('change_project', self.user)
        #self._create_and_add_permission('add_supply', self.user)
        #self._create_and_add_permission('add_quantity', self.user)
        #self._create_and_add_permission('subtract_quantity', self.user)
       
        
    def _create_and_add_permission(self, codename, user):
        p = Permission(content_type=self.ct, codename=codename)
        p.save()
        user.user_permissions.add(p)
        
    def test_get(self):
        """
        Test retrieving resources via GET
        """
        resp = self.api_client.get('/api/v1/project')
        
        self.assertHttpOK(resp)
        obj = self.deserialize(resp)
        self.assertEqual(len(obj['objects']), 1)
        project = obj['objects'][0]
        self.assertEqual(project['id'], 1)
        self.assertEqual(project['codename'], 'Ladawan')
        
    def test_get_obj(self):
        """
        Tests retrieving a single object via GET
        """
        resp = self.api_client.get('/api/v1/project/1')
        
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['codename'], 'Ladawan')
        self.assertIn('supplies', obj)
        self.assertEqual(len(obj['supplies']), 1)
        supply = obj['supplies'][0]
        self.assertEqual(supply['id'], 1)
        self.assertEqual(supply['description'], 'Grommet')
        self.assertEqual(int(supply['quantity']), 2)
        
    def test_get_all_projects(self):
        """
        Test retrieving full list of projects over 100"""
        for i in xrange(0, 100):
            project = Project(codename=i)
            project.save()

        self.assertEqual(Project.objects.all().count(), 101)
        
        resp = self.client.get('/api/v1/project/?page_size=99999', format='json')
        
        self.assertEqual(resp.status_code, 200)

        data = resp.data['results']
        self.assertEqual(len(data), 101)
        
    @unittest.skip('')
    def test_create_project(self):
        """
        Tests creating a project
        """
        self.assertIsNotNone(self.project)
        self.assertIsInstance(self.project, Project)
        self.assertIsInstance(self.project.customer, Customer)
        self.assertEqual(self.project.customer, self.customer)
        self.assertEqual(self.project.reference, "S5")
        self.assertEqual(self.project.type, "Condominium")
        self.assertEqual(self.project.due_date, base_due_date.date())
        self.assertEqual(self.project.codename, "Haze")

    def test_update_project(self):
        """
        Tests updating a project
        """
        data = {'codename': "Ladawan 329",
                'supplies': [{'id': 1,
                              'description': 'Grommet',
                              'quantity': 5},
                              {'id': 2,
                               'quantity': 10}]}
        
        resp = self.api_client.put('/api/v1/project/1', 
                                   format='json',
                                   data=data)
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['codename'], "Ladawan 329")
        self.assertEqual(len(obj['supplies']), 2)
        
        supply1 = obj['supplies'][0]
        self.assertEqual(supply1['id'], 1)
        self.assertEqual(supply1['description'], 'Grommet')
        self.assertEqual(int(supply1['quantity']), 5)
        
        supply2 = obj['supplies'][1]
        self.assertEqual(supply2['id'], 2)
        self.assertEqual(supply2['description'], 'Hinge')
        self.assertEqual(int(supply2['quantity']), 10)

    def test_update_project_deleting_supply(self):
        """
        Tests deleting a project supply via PUT
        """
        data = {'codename': "Ladawan 329",
                'supplies': [{'id': 2,
                              'description': 'Hinge',
                              'quantity': 10}]}   
                    
        resp = self.api_client.put('/api/v1/project/1', 
                                   format='json',
                                   data=data)
        self.assertHttpOK(resp)
        
        obj = self.deserialize(resp)
        self.assertEqual(obj['id'], 1)
        self.assertEqual(obj['codename'], "Ladawan 329")
        self.assertEqual(len(obj['supplies']), 1)
        
        supply1 = obj['supplies'][0]
        self.assertEqual(supply1['id'], 2)
        self.assertEqual(supply1['description'], 'Hinge')
        self.assertEqual(int(supply1['quantity']), 10)
      
        
    @unittest.skip('')
    def _update_due_date(self):
        """
        Tests the updating of the due date
        """
        due_date = dateutil.parser.parse("2013-04-26T13:59:01.143Z")
        self.project.update(due_date=due_date.isoformat())
        self.assertEqual(self.project.due_date, due_date.date())
        delta = datetime.timedelta(days=5)
        due_date2 = due_date + delta
        self.project.update(due_date=due_date2)
        self.assertEqual(self.project.due_date, due_date2.date())


class RoomResourceTestCase(APITestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        customer_data = copy.deepcopy(base_customer)
        del customer_data['addresses']
        self.customer = Customer.objects.create(**customer_data)
        self.customer.save()
        self.project = Project.objects.create(codename="Ladawan")
        self.room = Room.objects.create(description="Living Room", project=self.project)
        self.file1 = S3Object(key='test', bucket='test')
        self.file1.save()
        
    def test_create_room(self):
        """
        Tests creating a room
        """
        room = {'description':'family room', 'project':{'id': 1}, 'files':[{'id': 1}]}
        
        resp = self.client.post('/api/v1/room/', data=room, format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        data = resp.data
        self.assertIn('files', data)
        self.assertEqual(data['id'], 2)
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['id'], 1)
    
    def test_update_room(self):
        """
        Tests updating a room
        """
        file2 = S3Object.objects.create(key='file2', bucket='file2')
        file2 = S3Object.objects.create(key='file2', bucket='file2')

        room = {'description': 'Living Room', 'project': {'id': 1}, 'files':[{'id':2}, {'id':3}]}
        self.assertEqual(self.room.files.count(), 0)
        
        resp = self.client.put('/api/v1/room/1/', data=room, format='json')
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        data = resp.data
        self.assertEqual(data['id'], 1)
        self.assertIn('files', data)
        self.assertEqual(len(data['files']), 2)
        self.assertEqual(data['files'][0]['id'], 2)
        self.assertEqual(data['files'][1]['id'], 3)
        

class ItemResourceTestCase(APITestCase):
    def setUp(self):
        """
        Sets up for tests
        """
        customer_data = copy.deepcopy(base_customer)
        del customer_data['addresses']
        self.customer = Customer.objects.create(**customer_data)
        self.customer.save()
        self.project = Project.objects.create(codename="Ladawan")
        self.room = Room.objects.create(description="Living Room", project=self.project)
        self.file1 = S3Object(key='test', bucket='test')
        self.file1.save()
        
        self.item = Item.objects.create(description='Table', room=self.room)
        self.supply1 = Supply.objects.create(description='screw')
        
    def test_post_create_new_item_with_supply(self):
        """
        Test createing a new item, attached with various supplies
        """
        item_data = {'description': 'Kitchen', 
                     'room': {'id': 1},
                     'supplies': [{'id': 1, 
                                   'description': 'screw', 
                                   'quantity': 2}]}

        resp = self.client.post('/api/v1/room-item/', data=item_data, format='json')
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        data = resp.data
        self.assertEqual(data['id'], 2)
        self.assertIn('supplies', data)
        self.assertEqual(len(data['supplies']), 1)
        self.assertEqual(data['supplies'][0]['id'], 1)
        self.assertEqual(data['supplies'][0]['description'], 'screw')
        self.assertEqual(data['supplies'][0]['quantity'], Decimal('2'))
        
    def test_put_add_supplies(self):
        supply2 = Supply.objects.create(description='hinge')
        supply3 = Supply.objects.create(description='handle')
        
        item_data = {'id': 1,
                     'description': 'Living Room',
                     'room': {'id': 1},
                     'supplies': [{'id': 2,
                                   'description': 'hinge',
                                   'quantity': 5},
                                  {'id': 3,
                                   'description': 'handle',
                                   'quantity': 3.99}]}
                                   
        resp = self.client.put('/api/v1/room-item/1/', data=item_data, format='json')
        self.assertEqual(resp.status_code, 200)
        
        data = resp.data
        self.assertEqual(data['id'], 1)
        self.assertIn('supplies', data)
        self.assertEqual(len(data['supplies']), 2)
        self.assertEqual(data['supplies'][0]['id'], 2)
        self.assertEqual(data['supplies'][0]['description'], 'hinge')
        self.assertEqual(data['supplies'][0]['quantity'], Decimal('5'))
        self.assertIn('url', data['supplies'][1])
        self.assertEqual(data['supplies'][1]['id'], 3)
        self.assertEqual(data['supplies'][1]['description'], 'handle')
        self.assertEqual(data['supplies'][1]['quantity'], Decimal('3.99'))
        self.assertIn('url', data['supplies'][1])
        
    def test_put_remove_supplies(self):
        """
        Test disassociating a supply from an item
        """
        ItemSupply.objects.create(item=self.item, supply=self.supply1)
        
        self.assertEqual(self.item.supplies.all().count(), 1)
        self.assertEqual(self.item.supplies.all()[0].id, 1)
        
        item_data = {'description': 'Table',
                     'room': {'id': 1},
                     'supplies': []}
                     
        resp = self.client.put('/api/v1/room-item/1/', data=item_data, format='json')
        self.assertEqual(resp.status_code, 200)
        
        #Test resp
        data = resp.data
        self.assertEqual(data['id'], 1)
        self.assertEqual(data['description'], 'Table')
        self.assertIn('supplies', data)
        self.assertEqual(len(data['supplies']), 0)
        
        #Test database resource
        self.assertEqual(self.item.supplies.all().count(), 0)
        
        










