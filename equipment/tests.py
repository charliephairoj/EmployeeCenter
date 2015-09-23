"""
TEsting for equipment
"""
import logging

from rest_framework.test import APITestCase

from equipment.models import Equipment
from hr.models import Employee
from media.models import S3Object


logger = logging.getLogger(__name__)

base_equipment = {'description': 'F-50',
                  'brand': 'Red King',
                  'status': 'Checked In'}
                  
                  
class EquipmentTestCase(APITestCase):
    
    def setUp(self):
        
        self.equipment = Equipment(**base_equipment)
        self.equipment.save()
        
        self.employee = Employee(first_name="John",
                                 last_name="Smith",
                                 department="Carpentry")
        self.employee.save()
        
        self.image = S3Object()
        self.image.save()
        
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
                'status': 'Checked In',
                'image': {
                    'id': 1
                }}
        
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
        self.assertIn('image', obj)
        self.assertIn('id', obj['image'])
        self.assertEqual(obj['image']['id'], 1)
        
        #Test that resource saved to database
        self.assertEqual(Equipment.objects.all().count(), 2)
        
        obj = Equipment.objects.all().order_by('id')[1]
        
        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.id, 2)
        self.assertEqual(obj.description, 'Jigsaw')
        self.assertEqual(obj.brand, "Makita")
        self.assertEqual(obj.status, "Checked In")
        self.assertIsNotNone(obj.image)
        
    def test_post_empty_equipment(self):
        """
        Test creating resource via POST where the equipment only has an image
        """
        data = {'image': {'id': 1}}
        
        resp = self.client.post("/api/v1/equipment/", data=data, format='json')
        
        self.assertEqual(resp.status_code, 201, msg=resp)
        
        obj = resp.data
        
        self.assertIsInstance(obj, dict)
        self.assertIn('id', obj)
        self.assertEqual(obj['id'], 2)
        self.assertIn('description', obj)
        self.assertIsNone(obj['description'])
        self.assertIn('brand', obj)
        self.assertIsNone(obj['brand'])
        self.assertIn('status', obj)
        self.assertIsNone(obj['status'])
        self.assertIn('image', obj)
        self.assertIn('id', obj['image'])
        self.assertEqual(obj['image']['id'], 1)
        
        #Test that resource saved to database
        self.assertEqual(Equipment.objects.all().count(), 2)
        
        obj = Equipment.objects.all().order_by('id')[1]
        
        self.assertIsNotNone(obj.id)
        self.assertEqual(obj.id, 2)
        self.assertIsNone(obj.description, )
        self.assertIsNone(obj.brand)
        self.assertIsNone(obj.status)
        self.assertIsNotNone(obj.image)
        
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
        modified_data['employee'] = {'id': 1}
        modified_data['status'] = "Checked Out"
        
        resp = self.client.put("/api/v1/equipment/1/",
                               data=modified_data,
                               format="json")
        
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        obj = resp.data
        
        #Test response
        self.assertIn('id', obj)
        self.assertEqual(obj['id'], 1)
        self.assertIn('description', obj)
        self.assertEqual(obj['description'], "F-50")
        self.assertIn('brand', obj)
        self.assertEqual(obj['brand'], "Red King")
        self.assertIn('status', obj)
        self.assertEqual(obj['status'], 'Checked Out')
        self.assertIn('employee', obj)
        self.assertIsInstance(obj['employee'], dict)
        self.assertIn('id', obj['employee'])
        self.assertEqual(obj['employee']['id'], 1)
        
        #Test server response
        equipment = Equipment.objects.get(pk=1)
        
        self.assertEqual(equipment.id, 1)
        self.assertEqual(equipment.description, "F-50")
        self.assertEqual(equipment.brand, "Red King")
        self.assertEqual(equipment.status, "Checked Out")
        self.assertIsNotNone(equipment.employee)
        self.assertEqual(equipment.employee.id, 1)
        self.assertEqual(equipment.employee.first_name, "John")
        
    def test_update_bulk_with_employee(self):
        """
        Test updating multiple equipments with employee
        """
        equipment2 = Equipment(description="Jigsaw",
                               brand="Makita",
                               status="Checked Out",
                               employee=self.employee)
        equipment2.save()
        
        data = [{'id': 1,
                 'description': "F-50",
                 'brand': 'Red King',
                 'status': 'Checked Out',
                 'employee': {'id': 1}},
                {'id': 2,
                 'description': 'Jigsaw',
                 'brand': 'Makita',
                 'status': 'Checked In',
                 'employee': {'id': 1}}]
                 
        resp = self.client.put("/api/v1/equipment/",
                               data=data,
                               format="json")
                               
        self.assertEqual(resp.status_code, 200)
        
        #Test the response
        data = resp.data
        self.assertIsInstance(data, list)
        equip1 = data[0]
        self.assertEqual(equip1['id'], 1)
        self.assertEqual(equip1['description'], "F-50")
        self.assertEqual(equip1['brand'], 'Red King')
        self.assertEqual(equip1['status'], 'Checked Out')
        self.assertIn('employee', equip1)
        self.assertIsInstance(equip1['employee'], dict)
        self.assertIn('id', equip1['employee'])
        self.assertEqual(equip1['employee']['id'], 1)
        equip2 = data[1]
        self.assertEqual(equip2['id'], 2)
        self.assertEqual(equip2['description'], "Jigsaw")
        self.assertEqual(equip2['brand'], 'Makita')
        self.assertEqual(equip2['status'], 'Checked In')
        self.assertNotIn('employee', equip2)
        
        #Test instances in database
        equip1 = Equipment.objects.get(pk=1)
        self.assertEqual(equip1.id, 1)
        self.assertEqual(equip1.description, "F-50")
        self.assertEqual(equip1.brand, "Red King")
        self.assertEqual(equip1.status, "Checked Out")
        self.assertIsNotNone(equip1.employee)
        self.assertEqual(equip1.employee.id, 1)
        equip2 = Equipment.objects.get(pk=2)
        self.assertEqual(equip2.id, 2)
        self.assertEqual(equip2.description, "Jigsaw")
        self.assertEqual(equip2.brand, "Makita")
        self.assertEqual(equip2.status, "Checked In")
        self.assertIsNone(equip2.employee)
        
    def test_updating_bulk_with_different_data(self):
        """
        Test updating list of equipment with varying amounts of information
        """
        
        # Create new equipment to test
        equip1 = Equipment.objects.create(pk=188)
        equip2 = Equipment.objects.create(pk=189)
        equip3 = Equipment.objects.create(pk=190)
        
        # Data to submit via PUT
        data = [
            {'id': 188},
            {'id': 189,
             'description': 'saw'},
            {'id': 190,
             'description': 'jigsaw',
             'brand': 'Makita'}
        ]
        
        resp = self.client.put('/api/v1/equipment/', data=data, format='json')
        
        
                               
                               
                               
                               
                               
                               
                               
                               
        
        
        
        
        
        
        
        
        
        
        
        