"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from tastypie.test import ResourceTestCase
from django.contrib.auth.models import User

from contacts.models import Address, Contact, Customer, Supplier, SupplierContact


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
                "telephone": "08348229383"}
base_supplier_contact = {"contacts": [{"first_name": "Charlie",
                         "last_name": "Smith",
                         "email": "test@yahoo.com",
                         "telephone": "123456789"}]}

class ContactResourceTest(ResourceTestCase):
    
    def setUp(self):
        super(ContactResourceTest, self).setUp()
        
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
        resp = self.api_client.get('/api/v1/customer/', format='json')
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
        Test creating customer via post
        """
        #Validate resource creation
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.api_client.post('/api/v1/customer/', 
                                    format='json',
                                    data=base_contact,
                                    authentication=self.get_credentials())
        self.assertEqual(Customer.objects.count(), 2)
        
        #Validated response to resource creation
        

        
        


        
