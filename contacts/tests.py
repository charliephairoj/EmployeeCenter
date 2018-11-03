"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import copy
import logging

from django.test import TestCase
from administrator.models import User
from rest_framework.test import APITestCase
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
                'discount': 20,
                'notes': 'woohoo'}
base_supplier_contact = [{"name": "Charlie P",
                          "email": "test@yahoo.com",
                          "telephone": "123456789",
                          "primary": True}]
customer_data = base_contact.copy()
customer_data['type'] = 'Retail'
supplier_data = base_contact.copy()
supplier_data['name'] = 'Zipper World Co., Ltd.'
supplier_data['terms'] = 30
supplier_data['contacts'] = base_supplier_contact
del supplier_data['first_name']
del supplier_data['last_name']

class CustomerResourceTest(APITestCase):
    
    def setUp(self):
        super(CustomerResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        self.client.force_authenticate(self.user)    

        self.customer = Customer(**base_contact)
        self.customer.is_customer = True
        self.customer.save()
        
        self.address = Address(**base_address)
        self.address.contact = self.customer
        self.address.save()
                
    def get_credentials(self):
        return self.user #self.create_basic(username=self.username, password=self.password)
    
    def test_get_json_list(self):
        """
        Test GET of list 
        """
        #Retrieve and validate GET response
        resp = self.client.get('/api/v1/customer/', format='json')
        self.assertEqual(resp.status_code, 200)
        
        #test deserialized response
        resp_obj = resp.data
        self.assertEqual(len(resp_obj), 1)
        customer = resp_obj[0]
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")
        self.assertEqual(customer['discount'], 20)
        
    def test_post(self):
        """
        Test creating customer via POST
        """
        #Validate resource creation
        m_customer_data = customer_data.copy()
        addr_data = base_address.copy()
        m_customer_data['addresses'] = [addr_data]

        self.assertEqual(Customer.objects.count(), 1)
        resp = self.client.post('/api/v1/customer/', 
                                    format='json',
                                    data=m_customer_data,
                                    authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Customer.objects.count(), 2)
        
        #Validated response to resource creation
        customer = resp.data
        self.assertEqual(customer['id'], 2)
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")
        self.assertEqual(customer['discount'], 20)
        self.assertEqual(len(customer['addresses']), 1)

    def test_post_with_incomplete_address(self):
        """
        Test creating customer via POST with incomplete
        address data
        """
        def test_sub_post(c_data, missing_key):
            #Validate resource creation
            resp = self.client.post('/api/v1/customer/', 
                                        format='json',
                                        data=c_data,
                                        authentication=self.get_credentials())
            self.assertEqual(resp.status_code, 201, msg=resp)
            
            #Validated response to resource creation
            customer = resp.data
            self.assertIsNotNone(customer['id'])
            self.assertEqual(customer["name"], 'Charlie Brown')
            self.assertEqual(customer["first_name"], 'Charlie')
            self.assertEqual(customer["last_name"], 'Brown')
            self.assertEqual(customer["currency"], 'USD')
            self.assertTrue(customer["is_customer"])
            self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
            self.assertEqual(customer["telephone"], "08348229383")
            self.assertEqual(customer["fax"], "0224223423")
            self.assertEqual(customer['discount'], 20)

            self.assertIsNotNone(customer['addresses'])
            
            addrs = customer['addresses']
            self.assertEqual(len(addrs), 1)
            addr = addrs[0]
            self.assertIsNotNone(addr['id'])

            for k in [h for h in addr.keys() if h not in ['id', missing_key]]:
                #self.assertIsNotNone(addr[k], "{0}: {1}".format(k, addr[k]))
                msg = 'Error with property {0}'.format(k)
                self.assertEqual(addr[k], str(c_data['addresses'][0][k]), msg)

            # Test missing key is None
            self.assertEqual(addr[missing_key], None)

        m_customer_data = customer_data.copy()
        addr_data = base_address.copy()

        for key in addr_data.keys():
            m_addr_data = addr_data.copy()
            del m_addr_data[key]
            m_customer_data['addresses'] = [m_addr_data]
            test_sub_post(m_customer_data, key)
        

    def test_put(self):
        """
        Test updating a customer resource via PUT
        """
        logger.debug('\n\n Test PUT for customer \n\n')
        
        #Validate resource update instead of creation
        modified_customer = customer_data.copy()
        modified_customer['first_name'] = 'Charles'
        modified_customer['discount'] = 50
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.client.put('/api/v1/customer/1/',
                                   format='json',
                                   data=modified_customer, 
                                   authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 200)
        
        self.assertEqual(Customer.objects.count(), 1)
        obj = Customer.objects.all()[0]
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.first_name, 'Charles')
        self.assertEqual(obj.discount, 50)
    
    def test_get(self):
        """
        TEst getting a customer resource via GET
        """
        resp = self.client.get('/api/v1/customer/1/',
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 200)
        
        customer = resp.data
        self.assertEqual(customer['id'], 1)
        self.assertEqual(customer["name"], 'Charlie Brown')
        self.assertEqual(customer["first_name"], 'Charlie')
        self.assertEqual(customer["last_name"], 'Brown')
        self.assertEqual(customer["currency"], 'USD')
        self.assertTrue(customer["is_customer"])
        self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(customer["telephone"], "08348229383")
        self.assertEqual(customer["fax"], "0224223423")
        self.assertEqual(customer['discount'], 20)
        
    def test_delete(self):
        """
        Test delete a customer resource via get
        """
        self.assertEqual(Customer.objects.count(), 1)
        resp = self.client.delete('/api/v1/customer/1/',
                                      authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Customer.objects.count(), 0)
        

class SupplierResourceTest(APITestCase):
    
    def setUp(self):
        super(SupplierResourceTest, self).setUp()
        
        #Create the user
        self.username = 'tester'
        self.password = 'pass'
        self.user = User.objects.create_user(self.username, 'test@yahoo.com', self.password)
        self.client.force_authenticate(self.user)

        self.supplier_data = supplier_data
        self.supplier_data['addresses'] = [base_address]
        self.mod_supplier_data = self.supplier_data.copy()
        del self.mod_supplier_data['addresses']
        try:
            del self.mod_supplier_data['contacts']
        except KeyError:
            pass
        self.supplier = Supplier(**self.mod_supplier_data)
        self.supplier.is_supplier = True
        self.supplier.save()
        
        self.address = Address(**base_address)
        self.address.contact = self.supplier
        self.address.save()
        
        self.contact = SupplierContact(**base_supplier_contact[0])
        self.contact.supplier = self.supplier
        self.contact.save()
                
    def get_credentials(self):
        return None #self.create_basic(username=self.username, password=self.password)
    
    def test_get_list(self):
        """
        Test GET of list 
        """
        logger.debug("\n\n Test GET request for a list of suppliers \n")
        #Retrieve and validate GET response
        resp = self.client.get('/api/v1/supplier/', format='json')
        self.assertEqual(resp.status_code, 200)
        
        #test deserialized response
        resp_obj = resp.data
        self.assertEqual(len(resp_obj), 1)
        supplier = resp_obj[0]
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['discount'], 20)
        #Tests the contacts
        self.assertNotIn('contacts', supplier)
        """
        self.assertEqual(len(supplier['contacts']), 1)
        contact = supplier['contacts'][0]
        self.assertIn('id', contact)
        self.assertEqual(contact['id'], 1)
        self.assertEqual(contact['name'], 'Charlie P')
        self.assertEqual(contact['email'], 'test@yahoo.com')
        self.assertEqual(contact['telephone'], '123456789')
        """
        
    def test_post(self):
        """
        Test creating supplier via POST
        """
        logger.debug("\n\nTesting POST for Supplier \n\n")

        #Validate resource creation
        self.assertEqual(Supplier.objects.count(), 1)
        resp = self.client.post('/api/v1/supplier/', 
                                    format='json',
                                    data=self.supplier_data)

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Supplier.objects.count(), 2)
        
        #Validated response to resource creation
        supplier = resp.data
        self.assertEqual(supplier['id'], 2)
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['notes'], "woohoo")
        self.assertEqual(supplier['discount'], 20)
        #Validate the the supplier contact was created
        """
        self.assertIn("contacts", supplier)
        self.assertEqual(len(supplier['contacts']), 1)
        contact = supplier['contacts'][0]
        self.assertEqual(contact['id'], 2)
        self.assertEqual(contact['name'], 'Charlie P')
        self.assertEqual(contact['email'], 'test@yahoo.com')
        self.assertEqual(contact['telephone'], '123456789')
        self.assertTrue(contact['primary'])
        """

        #Verify address
        self.assertIn('addresses', supplier)
        self.assertEqual(len(supplier['addresses']), 1)
        
        #Validate the created supplier instance
        supp = Supplier.objects.order_by('-id').all()[0]
        self.assertEqual(supp.notes, 'woohoo')
        self.assertEqual(supp.telephone, "08348229383")
        self.assertEqual(supp.fax, "0224223423")
        self.assertEqual(supp.name, "Zipper World Co., Ltd.")
        self.assertEqual(supp.discount, 20)
        
    def test_post_with_single_address(self):
        """
        Test creating supplier via POST
        """
        logger.debug("\n\nTesting POST for Supplier with Single Address \n\n")

        #Validate resource creation
        self.assertEqual(Supplier.objects.count(), 1)
        mod_data = copy.deepcopy(self.supplier_data)
        del mod_data['addresses']
        mod_data['address'] = base_address
        resp = self.client.post('/api/v1/supplier/', 
                                    format='json',
                                    data=self.supplier_data)

        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(Supplier.objects.count(), 2)
        
        #Validated response to resource creation
        supplier = resp.data
        self.assertEqual(supplier['id'], 2)
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['notes'], "woohoo")
        self.assertEqual(supplier['discount'], 20)
        #Validate the the supplier contact was created
        """
        self.assertIn("contacts", supplier)
        self.assertEqual(len(supplier['contacts']), 1)
        contact = supplier['contacts'][0]
        self.assertEqual(contact['id'], 2)
        self.assertEqual(contact['name'], 'Charlie P')
        self.assertEqual(contact['email'], 'test@yahoo.com')
        self.assertEqual(contact['telephone'], '123456789')
        self.assertTrue(contact['primary'])
        """

        #Verify address
        self.assertIn('addresses', supplier)
        self.assertEqual(len(supplier['addresses']), 1)
        
        #Validate the created supplier instance
        supp = Supplier.objects.order_by('-id').all()[0]
        self.assertEqual(supp.notes, 'woohoo')
        self.assertEqual(supp.telephone, "08348229383")
        self.assertEqual(supp.fax, "0224223423")
        self.assertEqual(supp.name, "Zipper World Co., Ltd.")
        self.assertEqual(supp.discount, 20)
    
    def test_post_with_incomplete_address(self):
        """
        Test creating customer via POST with incomplete
        address data
        """
        def test_sub_post(c_data, missing_key):
            #Validate resource creation
            resp = self.client.post('/api/v1/customer/', 
                                        format='json',
                                        data=c_data,
                                        authentication=self.get_credentials())
            self.assertEqual(resp.status_code, 201, msg=resp)
            
            #Validated response to resource creation
            customer = resp.data
            self.assertIsNotNone(customer['id'])
            self.assertEqual(customer["name"], 'Charlie Brown')
            self.assertEqual(customer["first_name"], 'Charlie')
            self.assertEqual(customer["last_name"], 'Brown')
            self.assertEqual(customer["currency"], 'USD')
            self.assertTrue(customer["is_customer"])
            self.assertEqual(customer["email"], "charliep@dellarobbiathailand.com")
            self.assertEqual(customer["telephone"], "08348229383")
            self.assertEqual(customer["fax"], "0224223423")
            self.assertEqual(customer['discount'], 20)

            self.assertIsNotNone(customer['addresses'])
            
            addrs = customer['addresses']
            self.assertEqual(len(addrs), 1)
            addr = addrs[0]
            self.assertIsNotNone(addr['id'])

            for k in [h for h in addr.keys() if h not in ['id', missing_key]]:
                #self.assertIsNotNone(addr[k], "{0}: {1}".format(k, addr[k]))
                msg = 'Error with property {0}'.format(k)
                self.assertEqual(addr[k], str(c_data['addresses'][0][k]), msg)

            # Test missing key is None
            self.assertEqual(addr[missing_key], None)

        m_customer_data = customer_data.copy()
        addr_data = base_address.copy()

        for key in addr_data.keys():
            m_addr_data = addr_data.copy()
            del m_addr_data[key]
            m_customer_data['addresses'] = [m_addr_data]
            test_sub_post(m_customer_data, key)

    def test_put(self):
        """
        Test updating a supplier resource via PUT
        """
        logger.debug("\n\nTesting PUT for Supplier \n\n")
        
        #Validate resource update instead of creation
        modified_supplier = copy.deepcopy(self.supplier_data)
        modified_supplier['name'] = 'Zipper Land Ltd.'
        modified_supplier['terms'] = 120
        modified_supplier['discount'] = 75

        """
        modified_supplier['contacts'][0]['email'] = 'woohoo@yahoo.com'
        modified_supplier['contacts'][0]['id'] = 1
        del modified_supplier['contacts'][0]['primary']
        modified_supplier['contacts'].append({'name': 'test',
                                              'email': 'test@gmail.com',
                                              'telephone': 'ok',
                                              'primary': True})
        """

        self.assertEqual(Supplier.objects.count(), 1)

        """
        self.assertEqual(Supplier.objects.all()[0].contacts.count(), 1)
        self.assertEqual(len(modified_supplier['contacts']), 2)
        """
        
        resp = self.client.put('/api/v1/supplier/1/',
                               format='json',
                               data=modified_supplier)

        self.assertEqual(resp.status_code, 200)
        
        #Tests database state
        self.assertEqual(Supplier.objects.count(), 1)
        obj = Supplier.objects.all()[0]
        self.assertEqual(obj.id, 1)
        self.assertEqual(obj.name, 'Zipper Land Ltd.')
        self.assertEqual(obj.terms, 120)
        self.assertEqual(obj.discount, 75)

        """
        self.assertEqual(obj.contacts.count(), 2)
        contacts = obj.contacts.order_by('id').all()
        self.assertEqual(contacts[0].id, 1)
        self.assertEqual(contacts[0].email, 'woohoo@yahoo.com')
        self.assertEqual(contacts[0].name, 'Charlie P')
        self.assertEqual(contacts[0].telephone, '123456789')
        self.assertEqual(contacts[1].id, 2)
        self.assertEqual(contacts[1].name, 'test')
        self.assertEqual(contacts[1].email, 'test@gmail.com')
        self.assertEqual(contacts[1].telephone, 'ok')
        """
        
        #Tests the response
        supplier = resp.data
        self.assertEqual(supplier['id'], 1)
        self.assertEqual(supplier["name"], 'Zipper Land Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['discount'], 75)
        self.assertEqual(supplier['terms'], 120)

        """
        #Tests contacts in response
        self.assertIn('contacts', supplier)
        self.assertEqual(len(supplier['contacts']), 2)
        contacts = supplier['contacts']
        self.assertEqual(contacts[0]['id'], 1)
        self.assertEqual(contacts[0]['name'], 'Charlie P')
        self.assertEqual(contacts[0]['email'], 'woohoo@yahoo.com')
        self.assertEqual(contacts[0]['telephone'], '123456789')
        self.assertEqual(contacts[1]['id'], 2)
        self.assertEqual(contacts[1]['name'], 'test')
        self.assertEqual(contacts[1]['email'], 'test@gmail.com')
        self.assertEqual(contacts[1]['telephone'], 'ok')
        self.assertTrue(contacts[1]['primary'])
        """
    
    def test_get(self):
        """
        TEst getting a supplier resource via GET
        """
        resp = self.client.get('/api/v1/supplier/1/',
                                   format='json',
                                   authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 200)
        
        supplier = resp.data
        self.assertEqual(supplier['id'], 1)
        self.assertEqual(supplier["name"], 'Zipper World Co., Ltd.')
        self.assertEqual(supplier["currency"], 'USD')
        self.assertTrue(supplier["is_supplier"])
        self.assertEqual(supplier["email"], "charliep@dellarobbiathailand.com")
        self.assertEqual(supplier["telephone"], "08348229383")
        self.assertEqual(supplier["fax"], "0224223423")
        self.assertEqual(supplier['discount'], 20)
        
    def test_delete(self):
        """
        Test delete a supplier resource via get
        """
        self.assertEqual(Supplier.objects.count(), 1)
        resp = self.client.delete('/api/v1/supplier/1/',
                                      authentication=self.get_credentials())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Supplier.objects.count(), 0)
        
        
        


        
  


        
