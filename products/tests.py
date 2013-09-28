"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import random
import logging

from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.conf import settings
from tastypie.test import ResourceTestCase

from products.models import Product, Model, Configuration, Upholstery, Table, Pillow
from auth.models import S3Object

base_product = {"width": 1000, 
                "depth": 500,
                "height": 400,
                "wholesale_price": 100000,
                "retail_price": 250000,
                "manufacture_price": 50000,
                "export_price": 100000,
                "back_pillow": 1,
                "accent_pillow": 2,
                "lumbar_pillow": 3,
                "corner_pillow": 4}
base_model = {"model": "AC-1",
              "name": "Susie",
              "collection": "Dellarobbia Thailand"}
base_configuration = {"configuration": "Sofa"}
base_upholstery = {"model": {"id": 1},
                   "configuration": {"id": 1}}
base_upholstery.update(base_product)
base_table = {"model": {"id": 1},
              "configuration": {"id": 1}}
base_table.update(base_product)




class ModelResourceTest(ResourceTestCase):
    def setUp(self):
        super(ModelResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        #Create a model to be used for testing
        self.model = Model(**base_model)
        self.model.save()
                
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.api_client.get('/api/v1/model/', format='json')
        
        #Validate resp
        self.assertValidJSONResponse(resp)
        self.assertHttpOK(resp)
        
        #Validate data
        resp_obj = self.deserialize(resp)
        self.assertEqual(len(resp_obj['objects']), 1)
        
        #Validate the first resource
        model = resp_obj['objects'][0]
        self.assertEqual(model['id'], 1)
        self.assertEqual(model['model'], 'AC-1')
        self.assertEqual(model['name'], 'Susie')
        self.assertEqual(model['collection'], 'Dellarobbia Thailand')
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.api_client.get('/api/v1/model/1/', format='json')
        
        #Validate resp
        self.assertValidJSONResponse(resp)
        self.assertHttpOK(resp)
        
        #Validate the resource
        model = self.deserialize(resp)
        self.assertEqual(model['id'], 1)
        self.assertEqual(model['model'], 'AC-1')
        self.assertEqual(model['name'], 'Susie')
        self.assertEqual(model['collection'], 'Dellarobbia Thailand')
        
    def test_post(self):
        """
        Test creating a resource via POST
        """
        #Validate object creation
        self.assertEqual(Model.objects.count(), 1)
        resp = self.api_client.post('/api/v1/model/', 
                                    format='json',
                                    data=base_model,
                                    authorization=self.get_credentials())
        self.assertEqual(Model.objects.count(), 2)
        
        #Validate response
        self.assertHttpCreated(resp)
       
        #Validate the resource
        model = self.deserialize(resp)
        self.assertEqual(model['id'], 2)
        self.assertEqual(model['model'], 'AC-1')
        self.assertEqual(model['name'], 'Susie')
        self.assertEqual(model['collection'], 'Dellarobbia Thailand')
        
    def test_put(self):
        """
        Test updating a resource via POST
        
        The first part of the test will validate that an object
        is neither created or deleted
        """
        #Update data
        updated_model = base_model.copy()
        updated_model['name'] = 'Patsy'
        
        #Validate object update
        self.assertEqual(Model.objects.count(), 1)
        resp = self.api_client.put('/api/v1/model/1', 
                                   format='json',
                                   data=updated_model,
                                   authorization=self.get_credentials())
        self.assertEqual(Model.objects.count(), 1)
        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Model.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/model/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        self.assertEqual(Model.objects.count(), 0)
        
        #Validate the response
        self.assertHttpAccepted(resp)
        
    
class ConfigurationResourceTest(ResourceTestCase):
    def setUp(self):
        super(ConfigurationResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        #Create a model to be used for testing
        self.configuration = Configuration(**base_configuration)
        self.configuration.save()
                
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.api_client.get('/api/v1/configuration/', format='json')
        
        #Validate resp
        self.assertValidJSONResponse(resp)
        self.assertHttpOK(resp)
        
        #Validate data
        resp_obj = self.deserialize(resp)
        self.assertEqual(len(resp_obj['objects']), 1)
        
        #Validate the first resource
        configuration = resp_obj['objects'][0]
        self.assertEqual(configuration['id'], 1)
        self.assertEqual(configuration['configuration'], 'Sofa')
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.api_client.get('/api/v1/configuration/1/', format='json')
        
        #Validate resp
        self.assertValidJSONResponse(resp)
        self.assertHttpOK(resp)
        
        #Validate the resource
        model = self.deserialize(resp)
        self.assertEqual(model['id'], 1)
        self.assertEqual(model['configuration'], 'Sofa')
        
    def test_post(self):
        """
        Test creating a resource via POST
        """
        #Validate object creation
        self.assertEqual(Configuration.objects.count(), 1)
        resp = self.api_client.post('/api/v1/configuration/', 
                                    format='json',
                                    data=base_configuration,
                                    authorization=self.get_credentials())
        self.assertEqual(Configuration.objects.count(), 2)
        
        #Validate response
        self.assertHttpCreated(resp)
       
        #Validate the resource
        model = self.deserialize(resp)
        self.assertEqual(model['id'], 2)
        self.assertEqual(model['configuration'], 'Sofa')
        
    def test_put(self):
        """
        Test updating a resource via POST
        
        The first part of the test will validate that an object
        is neither created or deleted
        """
        #Update data
        updated_config = base_configuration.copy()
        updated_config['configuration'] = 'Chair'
        
        #Validate object update
        self.assertEqual(Configuration.objects.count(), 1)
        resp = self.api_client.put('/api/v1/configuration/1', 
                                   format='json',
                                   data=updated_config,
                                   authorization=self.get_credentials())
        self.assertEqual(Configuration.objects.count(), 1)
        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Configuration.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/configuration/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        self.assertEqual(Configuration.objects.count(), 0)
        
        #Validate the response
        self.assertHttpAccepted(resp)
        
        
        
    
    