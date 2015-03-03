"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import unittest
import logging

from django.contrib.auth.models import User, Permission, Group, ContentType
from tastypie.test import ResourceTestCase
from rest_framework.test import APITestCase

from auth.models import Employee, S3Object


logger = logging.getLogger(__name__)


class UserResourceTest(APITestCase):
    def setUp(self):
        """
        Set up the environment for the test cases
        """
        super(UserResourceTest, self).setUp()
        self.username = 'test-basic'
        self.password = 'password'
        self.user = User.objects.create_superuser('tester', 'testing@yahoo.com', 'test')
        self.user.user_permissions.add(Permission.objects.get(codename="add_user"))
        self.client.login(username='tester', password='test')
        profile = Employee()
        profile.user = self.user
        profile.save()
        self.img = S3Object()
        self.img.save()
        
    def get_credentials(self):
        """
        Creates basic credentials
        """
    
    def test_get_list(self):
        """
        Tests getting a list
        """
        #Validate the response
        resp = self.client.get('/api/v1/user/', format='json')
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        #Validate the obj
        user = resp.data['results'][0]
        self.assertIsNotNone(user)
        self.assertEqual(user['id'], 1)
        self.assertEqual(user['username'], 'tester')
        self.assertEqual(user['email'], 'testing@yahoo.com')
        self.assertIn("groups", user)

    def test_get(self):
        """
        Tests getting a single resource via GET
        """
        #Validate the response
        resp = self.client.get('/api/v1/user/1/', format='json')
        self.assertEqual(resp.status_code, 200, msg=resp)
        
        #Validate the obj
        user = resp.data
        self.assertEqual(user['id'], 1)
        self.assertEqual(user['username'], 'tester')
        self.assertEqual(user['email'], 'testing@yahoo.com')
        self.assertIn("groups", user)
        
    def test_post(self):
        """
        Tests creating a user via POST
        """
        self.assertEqual(User.objects.count(), 1)
        
        resp = self.client.post('/api/v1/user/', format='json',
                                    data={'username': 'test',
                                          'password': 'yay',
                                          'email': 'test@yahoo.com',
                                          'first_name': 'Charlie',
                                          'last_name': 'P',
                                          'image': {'id': self.img.id}})
        self.assertEqual(resp.status_code, 201, msg=resp)
        self.assertEqual(User.objects.count(), 2)
        
        #Tests the returned data
        user = resp.data
        self.assertEqual(user['id'], 2)
        self.assertEqual(user['username'], 'test')
        self.assertNotIn('password', user)
        self.assertEqual(user['first_name'], 'Charlie')
        self.assertEqual(user['last_name'], 'P')
        self.assertIn('groups', user)
        
        #Tests the actual model
        user = User.objects.get(pk=2)
        self.assertEqual(user.username, 'test')
        self.assertEqual(user.first_name, 'Charlie')
        self.assertEqual(user.last_name, 'P')
        #self.assertIsNotNone(user.employee)
        #self.assertIsNotNone(user.employee.image)
        #self.assertIsInstance(user.employee.image, S3Object)
    
        
    def test_failed_post(self):
        """
        Tests that an http 401 is return if the user is not authorized
        """
        self.skipTest('skipeed')
        self.client.logout()
        
        #Tests the response
        self.assertEqual(User.objects.count(), 1)
        resp = self.client.post('/api/v1/user/', format='json',
                                data={'username': 'test',
                                      'password': 'yay',
                                      'email': 'test@yahoo.com',
                                      'first_name': 'Charlie',
                                      'last_name': 'P'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(User.objects.count(), 1)
        
    def test_put_change_groups(self):
        """
        Tests adding a group to a user
        """
        #Create groups to be added
        group1 = Group(name="Testing")
        group1.save()
        
        #Create group to be removed
        group2 = Group(name='Bye')
        group2.save()
        self.user.groups.add(group2)
        
        #Create a permission
        ct = ContentType(name='test')
        ct.save()
        perm = Permission(codename='test', name='test',
                          content_type=ct)
        perm.save()
        group1.permissions.add(perm)
        perm = Permission(codename='removed', name='removed',
                          content_type=ct)
        perm.save()
        group2.permissions.add(perm)
        
        #Check that user has group to be removed and the permissions of that group
        self.assertEqual(self.user.groups.count(), 1)
        self.assertEqual(self.user.groups.all()[0].name, 'Bye')
        
        #Test the api and response
        resp = self.client.put('/api/v1/user/1/', format='json',
                                   data={'username':'test',
                                         'email': 'test@yahoo.com',
                                         'first_name': 'Charlie',
                                         'last_name': 'P',
                                         'groups': [{'id': 1, 'name': 'Testing'}]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.user.groups.count(), 1)
        self.assertEqual(self.user.groups.all()[0].name, 'Testing')
        
        #Tests the returned data
        user = resp.data
        self.assertEqual(len(user['groups']), 1)
        self.assertIn('id', user['groups'][0])
        self.assertIn('name', user['groups'][0])
        
    def test_change_password(self):
        """
        Tests creating a new password by posting the credentials
        """
        resp = self.client.put('/api/v1/user/1/change_password/',
                                   format='json', 
                                   data={'new_password':'TEST',
                                         'repeat_new_password': 'TEST'})

        
@unittest.skip("Skip Group Test")
class GroupResourceTest(ResourceTestCase):
    def setUp(self):
        """
        Set up the environment for the test cases
        """
        super(GroupResourceTest, self).setUp()
        self.username = 'test-basic'
        self.password = 'password'
        self.user = User.objects.create_superuser('tester', 'testing@yahoo.com', 'test')
        self.user.user_permissions.add(Permission.objects.get(codename="add_user"))
        self.api_client.client.login(username='tester', password='test')
        
        #Create a group
        self.group = Group(name="God")
        self.group.save()
        
        #Create a permission
        self.ct = ContentType(name='test')
        self.ct.save()
        self.permission = Permission(name='Test', codename='test',
                                     content_type=self.ct)
        self.permission.save()
        
        self.group.permissions.add(self.permission)
        
    def test_get_list(self):
        """
        Tests getting a list of groups via GET
        """
        #Tests the resp
        resp = self.api_client.get('/api/v1/group/')
        self.assertHttpOK(resp)
        
    def test_get(self):
        """
        Tests getting a group via GET
        """
        #Tests the resp
        resp = self.api_client.get('/api/v1/group/1/')
        self.assertHttpOK(resp)
        
        #Tests the return data
        group = self.deserialize(resp)
        self.assertEqual(group['id'], 1)
        self.assertEqual(group['name'], 'God')
        self.assertIn('permissions', group)
        self.assertEqual(len(group['permissions']), 1)
        
    def test_post(self):
        """
        Test creating a new group via POST
        """
        #Test the api and the respose
        self.assertEqual(Group.objects.count(), 1)
        resp = self.api_client.post('/api/v1/group/', format='json',
                                    data={'name': 'Boss',
                                          'group': 'Boss',
                                          'permissions': [{'id': 1}]})
        self.assertHttpCreated(resp)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(Group.objects.order_by('-id').all()[0].permissions.count(), 1)
        
        #Tests the data to be returned
        self.assertEqual(group['id'], 2)
        self.assertEqual(group['name'], 'Boss')
        self.assertIn('permissions', group)
        self.assertEqual(len(group['permissions']), 1)
        self.assertEqual(group['permissions'][0]['name'], Permission.objects.get(pk=1).name)
        
