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
from rest_framework.test import APITestCase

from products.models import Product, Model, Configuration, Upholstery, Table, Pillow
from auth.models import S3Object

base_product = {"width": 1000, 
                "depth": 500,
                "height": 400,
                "price": 250000,
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
              "collection": "Dellarobbia Thailand",
              'images': [{'key':'image/1.jpg',
                          'bucket': 'media.dellarobbiathailand.com'}]}
base_configuration = {"configuration": "Sofa"}
base_upholstery = {"model": {"id": 1},
                   "configuration": {"id": 1},
                   'category': 'Chair'}
base_upholstery.update(base_product)
base_table = {"model": {"id": 1},
              "configuration": {"id": 1},
              'finish': 'high gloss'}
base_table.update(base_product)


logger = logging.getLogger(__name__)


class ModelResourceTest(APITestCase):
    def setUp(self):
        super(ModelResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        #Create a model to be used for testing
        model_data = base_model.copy()
        del model_data['images']
        self.model = Model(**model_data)
        self.model.save()
                
    def get_credentials(self):
        return None#self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.client.get('/api/v1/model/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate data
        resp_obj = resp.data
        self.assertEqual(len(resp_obj['results']), 1)
        
        #Validate the first resource
        model = resp_obj['results'][0]
        self.assertEqual(model['id'], 1)
        self.assertEqual(model['model'], 'AC-1')
        self.assertEqual(model['name'], 'Susie')
        self.assertEqual(model['collection'], 'Dellarobbia Thailand')
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.client.get('/api/v1/model/1/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate the resource
        model = resp.data
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
        resp = self.client.post('/api/v1/model/', 
                                    format='json',
                                    data=base_model,
                                    authorization=self.get_credentials())
        self.assertEqual(Model.objects.count(), 2)
        
        #Validate response
        self.assertEqual(resp.status_code, 201)
       
        #Validate the resource
        model = resp.data
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
        resp = self.client.put('/api/v1/model/1/', 
                                   format='json',
                                   data=updated_model,
                                   authorization=self.get_credentials())
        self.assertEqual(Model.objects.count(), 1)
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate resource
        model = resp.data
        self.assertEqual(model['name'], 'Patsy')

        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Model.objects.count(), 1)
        resp = self.client.delete('/api/v1/model/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        self.assertEqual(Model.objects.count(), 0)
        
        #Validate the response
        self.assertEqual(resp.status_code, 204)
        
    
class ConfigurationResourceTest(APITestCase):
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
        return None#self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.client.get('/api/v1/configuration/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        #Validate data
        resp_obj = resp.data
        self.assertEqual(len(resp_obj['results']), 1)
        
        #Validate the first resource
        configuration = resp_obj['results'][0]
        self.assertEqual(configuration['id'], 1)
        self.assertEqual(configuration['configuration'], 'Sofa')
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.client.get('/api/v1/configuration/1/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate the resource
        configuration = resp.data
        self.assertEqual(configuration['id'], 1)
        self.assertEqual(configuration['configuration'], 'Sofa')
        
    def test_post(self):
        """
        Test creating a resource via POST
        """
        #Validate object creation
        self.assertEqual(Configuration.objects.count(), 1)
        resp = self.client.post('/api/v1/configuration/', 
                                    format='json',
                                    data=base_configuration,
                                    authorization=self.get_credentials())
        self.assertEqual(Configuration.objects.count(), 2)
        
        #Validate response
        self.assertEqual(resp.status_code, 201)
       
        #Validate the resource
        configuration = resp.data
        self.assertEqual(configuration['id'], 2)
        self.assertEqual(configuration['configuration'], 'Sofa')
        
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
        resp = self.client.put('/api/v1/configuration/1/', 
                                   format='json',
                                   data=updated_config,
                                   authorization=self.get_credentials())
                                   
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Configuration.objects.count(), 1)
        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Configuration.objects.count(), 1)
        resp = self.client.delete('/api/v1/configuration/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        
        self.assertEqual(Configuration.objects.count(), 0)
        #Validate the response
        self.assertEqual(resp.status_code, 204)
        
        
class UpholsteryResourceTest(APITestCase):
    def setUp(self):
        super(UpholsteryResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        #Create a model to be used for testing
        model_data = base_model.copy()
        del model_data['images']
        self.model = Model(**model_data)
        self.model.save()
        
        #Create configuration for testing
        self.configuration = Configuration(**base_configuration)
        self.configuration.save()
        
        #Strip pillows and make pillows separately
        uphol_data = base_product.copy()
        del uphol_data['corner_pillow']
        del uphol_data['accent_pillow']
        del uphol_data['back_pillow']
        del uphol_data['lumbar_pillow']
        self.product = Upholstery(**uphol_data)
        self.product.description = 'AC-1 Sofa'
        self.product.model = self.model
        self.product.configuration = self.configuration
        self.product.save()
                
    def get_credentials(self):
        return None#self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.client.get('/api/v1/upholstery/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate data
        resp_obj = resp.data
        self.assertEqual(len(resp_obj['results']), 1)
        
        #Validate the first resource
        upholstery = resp_obj['results'][0]
        self.assertEqual(upholstery['id'], 1)
        self.assertEqual(upholstery['type'], 'upholstery')
        self.assertEqual(upholstery['description'], 'AC-1 Sofa')
        self.assertEqual(upholstery['model']['id'], 1)
        self.assertEqual(upholstery['configuration']['id'], 1)
        self.assertEqual(upholstery['width'], 1000)
        self.assertEqual(upholstery['depth'], 500)
        self.assertEqual(upholstery['height'], 400)
        self.assertEqual(int(upholstery['manufacture_price']), 50000)
        self.assertEqual(int(upholstery['export_price']), 100000)
        self.assertEqual(int(upholstery['wholesale_price']), 100000)
        self.assertEqual(int(upholstery['price']), 250000)
        #self.assertEqual(upholstery['configuration']['id'], 1)
        
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.client.get('/api/v1/upholstery/1/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate the resource
        configuration = resp.data
        
        self.assertEqual(configuration['id'], 1)
        
        #Validate the first resource
        upholstery = resp.data
        self.assertEqual(upholstery['id'], 1)
        self.assertEqual(upholstery['type'], 'upholstery')
        self.assertEqual(upholstery['description'], 'AC-1 Sofa')
        self.assertEqual(upholstery['model']['id'], 1)
        self.assertEqual(upholstery['configuration']['id'], 1)
        self.assertEqual(upholstery['width'], 1000)
        self.assertEqual(upholstery['depth'], 500)
        self.assertEqual(upholstery['height'], 400)
        self.assertEqual(int(upholstery['manufacture_price']), 50000)
        self.assertEqual(int(upholstery['export_price']), 100000)
        self.assertEqual(int(upholstery['wholesale_price']), 100000)
        self.assertEqual(int(upholstery['price']), 250000)
        
    def test_post(self):
        """
        Test creating a resource via POST
        """
        #Validate object creation
        self.assertEqual(Upholstery.objects.count(), 1)
        resp = self.client.post('/api/v1/upholstery/', 
                                    format='json',
                                    data=base_upholstery,
                                    authorization=self.get_credentials())
        self.assertEqual(Upholstery.objects.count(), 2)
        
        #Validate response
        self.assertEqual(resp.status_code, 201)
       
        #Validate the first resource
        upholstery = resp.data
        self.assertEqual(upholstery['id'], 2)
        self.assertEqual(upholstery['type'], 'upholstery')
        self.assertEqual(upholstery['description'], 'AC-1 Sofa')
        self.assertEqual(upholstery['model']['id'], 1)
        self.assertEqual(upholstery['configuration']['id'], 1)
        self.assertEqual(upholstery['width'], 1000)
        self.assertEqual(upholstery['depth'], 500)
        self.assertEqual(upholstery['height'], 400)
        self.assertEqual(int(upholstery['manufacture_price']), 50000)
        self.assertEqual(int(upholstery['export_price']), 100000)
        self.assertEqual(int(upholstery['wholesale_price']), 100000)
        self.assertEqual(int(upholstery['price']), 250000)
        
    def test_put(self):
        """
        Test updating a resource via POST
        
        The first part of the test will validate that an object
        is neither created or deleted
        """
        #Update data
        updated_uphol = base_upholstery.copy()
        updated_uphol['price'] = 350000
        
        #Validate object update
        self.assertEqual(Upholstery.objects.count(), 1)
        resp = self.client.put('/api/v1/upholstery/1/', 
                                   format='json',
                                   data=updated_uphol,
                                   authorization=self.get_credentials())
        self.assertEqual(Upholstery.objects.count(), 1)
        
        self.assertEqual(resp.status_code, 200)
        
        #Validate the first resource
        upholstery = resp.data
        self.assertEqual(upholstery['id'], 1)
        self.assertEqual(upholstery['type'], 'upholstery')
        self.assertEqual(upholstery['description'], 'AC-1 Sofa')
        self.assertEqual(upholstery['model']['id'], 1)
        self.assertEqual(upholstery['configuration']['id'], 1)
        self.assertEqual(upholstery['width'], 1000)
        self.assertEqual(upholstery['depth'], 500)
        self.assertEqual(upholstery['height'], 400)
        self.assertEqual(int(upholstery['manufacture_price']), 50000)
        self.assertEqual(int(upholstery['export_price']), 100000)
        self.assertEqual(int(upholstery['price']), 350000)
        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Upholstery.objects.count(), 1)
        resp = self.client.delete('/api/v1/upholstery/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        self.assertEqual(Upholstery.objects.count(), 0)
        
        #Validate the response
        self.assertEqual(resp.status_code, 204)
        
    
class TableResourceTest(APITestCase):
    def setUp(self):
        super(TableResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        #Create a model to be used for testing
        model_data = base_model.copy()
        del model_data['images']
        self.model = Model(**model_data)
        self.model.save()
        
        #Create configuration for testing
        self.configuration = Configuration(configuration='Coffee Table')
        self.configuration.save()
        
        #Strip pillows and make pillows separately
        table_data = base_product.copy()
        del table_data['corner_pillow']
        del table_data['accent_pillow']
        del table_data['back_pillow']
        del table_data['lumbar_pillow']
        self.product = Table(**table_data)
        self.product.description = 'AC-1 Coffee Table'
        self.product.type = 'table'
        self.product.model = self.model
        self.product.configuration = self.configuration
        self.product.save()
                
    def get_credentials(self):
        return None#self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test getting a list of models via GET
        """
        resp = self.client.get('/api/v1/table/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate data
        resp_obj = resp.data
        self.assertEqual(len(resp_obj['results']), 1)
        
        #Validate the first resource
        table = resp_obj['results'][0]
        self.assertEqual(table['id'], 1)
        self.assertEqual(table['type'], 'table')
        self.assertEqual(table['description'], 'AC-1 Coffee Table')
        self.assertEqual(table['model']['id'], 1)
        self.assertEqual(table['configuration']['id'], 1)
        self.assertEqual(table['width'], 1000)
        self.assertEqual(table['depth'], 500)
        self.assertEqual(table['height'], 400)
        self.assertEqual(int(table['manufacture_price']), 50000)
        self.assertEqual(int(table['export_price']), 100000)
        self.assertEqual(int(table['wholesale_price']), 100000)
        
        
    def test_get(self):
        """
        Test retrieving a resource via GET
        """
        resp = self.client.get('/api/v1/table/1/', format='json')
        
        #Validate resp
        self.assertEqual(resp.status_code, 200)
        
        #Validate the first resource
        table = resp.data
        self.assertEqual(table['id'], 1)
        self.assertEqual(table['type'], 'table')
        self.assertEqual(table['description'], 'AC-1 Coffee Table')
        self.assertEqual(table['model']['id'], 1)
        self.assertEqual(table['configuration']['id'], 1)
        self.assertEqual(table['width'], 1000)
        self.assertEqual(table['depth'], 500)
        self.assertEqual(table['height'], 400)
        self.assertEqual(int(table['manufacture_price']), 50000)
        self.assertEqual(int(table['export_price']), 100000)
        self.assertEqual(int(table['wholesale_price']), 100000)
        
    def test_post(self):
        """
        Test creating a resource via POST
        """
        #Validate object creation
        self.assertEqual(Table.objects.count(), 1)
        resp = self.client.post('/api/v1/table/', 
                                    format='json',
                                    data=base_table,
                                    authorization=self.get_credentials())
        self.assertEqual(Table.objects.count(), 2)
        #Validate response
        self.assertEqual(resp.status_code, 201)
       
        #Validate the first resource
        table = resp.data
        self.assertEqual(table['id'], 2)
        self.assertEqual(table['type'], 'table')
        self.assertEqual(table['description'], 'AC-1 Coffee Table')
        self.assertEqual(table['model']['id'], 1)
        self.assertEqual(table['configuration']['id'], 1)
        self.assertEqual(table['width'], 1000)
        self.assertEqual(table['depth'], 500)
        self.assertEqual(table['height'], 400)
        self.assertEqual(int(table['manufacture_price']), 50000)
        self.assertEqual(int(table['export_price']), 100000)
        self.assertEqual(int(table['wholesale_price']), 100000)
        
    def test_put(self):
        """
        Test updating a resource via POST
        
        The first part of the test will validate that an object
        is neither created or deleted
        """
        #Update data
        updated_table = base_table.copy()
        updated_table['wholesale_price'] = 120000
        
        #Validate object update
        self.assertEqual(Table.objects.count(), 1)
        resp = self.client.put('/api/v1/table/1/', 
                                   format='json',
                                   data=updated_table,
                                   authorization=self.get_credentials())
        self.assertEqual(Table.objects.count(), 1)
        self.assertEqual(resp.status_code, 200)
        
        #Validate the first resource
        table = resp.data
        self.assertEqual(table['id'], 1)
        self.assertEqual(table['type'], 'table')
        self.assertEqual(table['description'], 'AC-1 Coffee Table')
        self.assertEqual(table['model']['id'], 1)
        self.assertEqual(table['configuration']['id'], 1)
        self.assertEqual(table['width'], 1000)
        self.assertEqual(table['depth'], 500)
        self.assertEqual(table['height'], 400)
        self.assertEqual(int(table['manufacture_price']), 50000)
        self.assertEqual(int(table['export_price']), 100000)
        self.assertEqual(int(table['wholesale_price']), 120000)
        
    def test_delete(self):
        """
        Test deleting a resource via DELETE
        """
        #Validate resource deleted
        self.assertEqual(Table.objects.count(), 1)
        resp = self.client.delete('/api/v1/table/1/', 
                                      format='json', 
                                      authentication=self.get_credentials())
        self.assertEqual(Table.objects.count(), 0)
        
        #Validate the response
        self.assertEqual(resp.status_code, 204)
    
    