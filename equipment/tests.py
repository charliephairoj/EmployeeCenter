"""
TEsting for equipment
"""
import logging

from rest_framework.test import APITestCase

from equipment.models import Equipment
from hr.models import Employee


logger = logging.getLogger(__name__)

base_equipment = {'description': 'F-50',
                  'brand': 'Red King',
                  'status': 'Checked In'}
                  
                  
class EquipmentTestCase(APITestCase):
    
    def setUp(self):
        
        self.equipment = Equipment(**base_equipment)
        self.equipment.save()
        
        self.employee = Employee(first_name="John",
                                 last_name="Smith"
                                 department="Carpentry")
        
    def test_get_list(self):
        """
        Test GET on api to get a list resources
        """
        resp = self.client.get("/api/v1/equipment/", format='json')
        
        self.assertEqual(resp.status_code, 200)
        
        resp = resp.data

        self.assertIsInstance(resp, dict)
        self.assertIsInstance(resp['results'], list)
        self.assertEqual(len(resp['results']), 1)
        
    def test_get(self):
        """
        Test GET on api to get a resource
        """
        resp = self.client.get("/api/v1/equipment/1/", format='json')
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        obj = resp.data
        
        self.assertIsInstance(obj, dict)
        self.assertIn('id', obj)
        self.assertEqual(obj['id'], 1)
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'F-50')
        self.assertIn('brand', obj)
        self.assertEqual(obj['brand'], 'Red King')
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], 'Checked In')
        
    def test_post(self):
        """
        Test creating resource via POST
        """
        data = {'description': 'Jigsaw',
                'brand': 'Makita',
                'status': 'Checked In'}
        
        resp = self.client.post("/api/v1/equipment/", data=data, format='json')
        
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        obj = resp.data
        
        self.assertIsInstance(obj, dict)
        self.assertIn('id', obj)
        self.assertEqual(obj['id'], 2)
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'Jigsaw')
        self.assertIn('brand', obj)
        self.assertEqual(obj['brand'], 'Makita')
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], 'Checked In')
        
        #Test that resource saved to database
        self.assertEqual(Equipment.objects.all().count(), 2)
        
        obj = Equipment.objects.all().order_by('id')[1]
        
        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.id, 2)
        self.assertEqual(obj.description, 'Jigsaw')
        self.assertEqual(obj.brand, "Makita")
        self.assertEqual(obj.status, "Checked In")
        
    def test_put(self):
        """
        Test updating resource via PUT
        """
        modified_data = base_equipment.copy()
        modified_data['brand'] = 'Maktec'
        modified_data['status'] = "Checked Out"
        
        resp = self.client.put("/api/v1/equipment/1/",
                               data=modified_data,
                               format='json')
                               
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        obj = resp.data
        
        self.assertIn('id', obj)
        self.assertEqual(obj['id'], 1)
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], 'F-50')
        self.assertIn('brand', obj)
        self.assertEqual(obj['brand'], "Maktec")
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], "Checked Out")
        
    def test_update_with_employee_checkout(self):
        """
        Test updating the equipment checkout with
        a particular employee
        """
        modified_data = base_equipment.copy()
        modified_data['employee'] = {'id'}
        
            
        
        
        
        
        
        
        
        
        
        
        
        