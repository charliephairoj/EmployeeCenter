"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import logging

from django.test import TestCase
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User

from contacts.models import Address, Customer, Supplier, SupplierContact


logger = logging.getLogger(__name__)

base_address = {"address1": "22471 Sunbrook",
                "city": "Mission Viejo",
                "territory": "CA",
                "country": "USA",
                "zipcode": 92692}
base_contact = {"name": "Charlie Brown",
                'first_name': 'Charlie',
                'last_name': 'Brown',
                "currency": "USD",
                "email": "charliep@dellarobbiathailand.com",
                "fax": "0224223423",
                "telephone": "08348229383",
                'notes': 'woohoo'}
base_supplier_contact = {"contacts": [{"first_name": "Charlie",
                         "last_name": "Smith",
                         "email": "test@yahoo.com",
                         "telephone": "123456789"}]}
customer_data = base_contact.copy()
customer_data['type'] = 'Retail'
supplier_data = base_contact.copy()
supplier_data['name'] = 'Zipper World Co., Ltd.'
supplier_data['terms'] = 30
supplier_data['discount'] = 0
del supplier_data['first_name']
del supplier_data['last_name']

class CustomerResourceTest(ResourceTestCase):
    
    def setUp(self):
        super(CustomerResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        

        self.customer = Customer(**base_contact)
        self.customer.is_customer = True
        self.customer.save()
        
        self.address = Address(**base_address)
        self.address.contact = self.customer
        self.address.save()
                
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get_json_list(self):
        """
        Test GET of list 
        """
        #Retrieve and validate GET response
        resp = self.api_client.get('/api/v1/customer', format='json')
        self.assertValidJSONResponse(resp)
        
        #test deserialized response
        resp_obj = self.deserialize(resp)
        self.assertEqual(len(resp_obj['objects']), 1)
        customer = resp_obj['objects'][0]
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")
        
    def test_post(self):
        """
        Test creating customer via POST
        """
        #Validate resource creation
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.api_client.post('/api/v1/customer', 
                                    format='json',
                                    data=customer_data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Customer.objects.count(), 2)
        
        #Validated response to resource creation
        customer = self.deserialize(resp)
        self.assertEqual(customer['id'], 2)
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")

    def test_put(self):
        """
        Test updating a customer resource via PUT
        """
        #Validate resource update instead of creation
        modified_customer = customer_data
        modified_customer['first_name'] = 'Charles'
        modified_customer['type'] = 'Dealer'
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.api_client.put('/api/v1/customer/1',
                                   format='json',
                                   data=modified_customer, 
                                   authentication=self.get_credentials())
        self.assertEqual(Customer.objects.count(), 1)
        obj = Customer.objects.all()[0]
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.first_name, 'Charles')
        self.assertEqual(obj.type, 'Dealer')
    
    def test_get(self):
        """
        TEst getting a customer resource via GET
        """
        resp = self.api_client.get('/api/v1/customer/1',
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        customer = self.deserialize(resp)
        self.assertEqual(customer['id'], 1)
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")
        
    def test_delete(self):
        """
        Test delete a customer resource via get
        """
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/customer/1',
                                      authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Customer.objects.count(), 0)
        

class SupplierResourceTest(ResourceTestCase):
    
    def setUp(self):
        super(SupplierResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        
        self.supplier_data = supplier_data
        self.supplier = Supplier(**self.supplier_data)
        self.supplier.is_supplier = True
        self.supplier.save()
        
        self.address = Address(**base_address)
        self.address.contact = self.supplier
        self.address.save()
                
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get_json_list(self):
        """
        Test GET of list 
        """
        #Retrieve and validate GET response
        resp = self.api_client.get('/api/v1/supplier', format='json')
        self.assertValidJSONResponse(resp)
        
        #test deserialized response
        resp_obj = self.deserialize(resp)
        self.assertEqual(len(resp_obj['objects']), 1)
        supplier = resp_obj['objects'][0]
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        
    def test_post(self):
        """
        Test creating supplier via POST
        """
        #Validate resource creation
        self.assertEqual(Supplier.objects.count(), 1)
        resp = self.api_client.post('/api/v1/supplier', 
                                    format='json',
                                    data=self.supplier_data,
                                    authentication=self.get_credentials())
        self.assertHttpCreated(resp)
        self.assertEqual(Supplier.objects.count(), 2)
        
        #Validated response to resource creation
        supplier = self.deserialize(resp)
        self.assertEqual(supplier['id'], 2)
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['notes'], "woohoo")
        
        #Validate the created supplier instance
        supp = Supplier.objects.order_by('-id').all()[0]
        self.assertEqual(supp.notes, 'woohoo')
        self.assertEqual(supp.telephone, "08348229383")
        self.assertEqual(supp.fax, "0224223423")
        self.assertEqual(supp.name, "Zipper World Co., Ltd.")

    def test_put(self):
        """
        Test updating a supplier resource via PUT
        """
        #Validate resource update instead of creation
        modified_supplier = self.supplier_data.copy()
        modified_supplier['name'] = 'Zipper Land Ltd.'
        modified_supplier['terms'] = 120
        self.assertEqual(Supplier.objects.count(), 1)
        resp = self.api_client.put('/api/v1/supplier/1',
                                   format='json',
                                   data=modified_supplier, 
                                   authentication=self.get_credentials())
        self.assertEqual(Supplier.objects.count(), 1)
        obj = Supplier.objects.all()[0]
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.name, 'Zipper Land Ltd.')
        self.assertEqual(obj.terms, 120)
    
    def test_get(self):
        """
        TEst getting a supplier resource via GET
        """
        resp = self.api_client.get('/api/v1/supplier/1',
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertHttpOK(resp)
        supplier = self.deserialize(resp)
        self.assertEqual(supplier['id'], 1)
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        
    def test_delete(self):
        """
        Test delete a supplier resource via get
        """
        self.assertEqual(Supplier.objects.count(), 1)
        resp = self.api_client.delete('/api/v1/supplier/1',
                                      authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Supplier.objects.count(), 0)
        
        
        


        
  


        
