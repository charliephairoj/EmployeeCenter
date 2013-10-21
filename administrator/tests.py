"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.contrib.auth.models import User
from tastypie.test import ResourceTestCase


class UserResourceTest(ResourceTestCase):
    def setUp(self):
        self.username = 'test-basic'
        self.password = 'password'
        print dir(self)
        
    def get_credentials(self):
        return self.create_basic(username=self.username, password=self.password)
    
    def test_post(self):
        """
        Tests creating a user via POST
        """
        resp = self.api_client.post('/api/v1/user', format='json',
                                    data={'username': 'test',
                                          'password': 'yay',
                                          'email': 'test@yahoo.com'},
                                    authentication=self.get_credentials())
