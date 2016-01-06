#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieves a list of Orders and products to be shipped 
in the 30 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""

import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
import logging
import httplib2

import boto
from django.contrib.auth.models import User, Group
from oauth2client import xsrfutil
from oauth2client.client import flow_from_clientsecrets
from oauth2client.django_orm import Storage
from apiclient import discovery

from administrator.models import AWSUser
from administrator.models import CredentialsModel


django.setup()            
logger = logging.getLogger(__name__)
            
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    
    user = User.objects.get(email="charliep@dellarobbiathailand.com")
    
    for user in users:
        
        try:
            aws_credentials = user.aws_credentials
        except:
            aws_credentials = AWSUser(user=user)
            aws_credentials.save()
            
        try:
            
            iam_user = iam.get_user(user_name=user.email)
        except:
            iam_user = iam.create_user(user_name=user.email)
            
        
        aws_credentials.iam_id = iam_user.user_id
        
        response = iam.get_all_access_keys(user_name=user.email)
        
        keys = [item['access_key_id'] for item in response['list_access_keys_response']['list_access_keys_result']['access_key_metadata']]

        for key in keys:
            iam.delete_access_key(key, user.email)
            
        creds = iam.create_access_key(user_name=user.email)

        aws_credentials.access_key_id = creds.access_key_id
        aws_credentials.secret_access_key = creds.secret_access_key
        aws_credentials.save()

    


