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
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

import boto
from django.contrib.auth.models import User

from administrator.models import AWSUser


django.setup()            
            
if __name__ == "__main__":
    
    users = User.objects.all()
    iam = boto.connect_iam()
    
    for user in users:

       
        
        response = iam.add_user_to_group('S3-Users', user.email)







