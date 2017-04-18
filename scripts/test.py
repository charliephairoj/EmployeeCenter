#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieves a list of Orders and products to be shipped 
in the 30 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""

import sys
import os
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')
from datetime import date

import boto
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from django.core.wsgi import get_wsgi_application
from django.conf import settings
import gdata.contacts.client
import gdata.contacts.data



os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()

from contacts.models import Customer, Contact
from django.contrib.auth.models import User
            
            
if __name__ == "__main__":
    
    u = User.objects.get(pk=1)
    s = Customer.get_google_contacts_service(u)
    
    service = Customer.get_google_contacts_service(u)
    query = gdata.contacts.client.ContactsQuery()
    query.max_results = 10000
    feed = service.GetContacts(q = query)
    for contact in feed.entry:
        try:
            print contact.id.text, contact.email[0].address
            print '\n'
        except:
            pass
    
