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
        
        self.post_data = base_contact
        
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_get(self):
        print self.api_client.get('/api/v1/customer/', format='json')



        
