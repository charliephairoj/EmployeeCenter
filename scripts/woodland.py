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


if __name__ == "__main__":
    
    user = User.objects.get(email="charliep@dellarobbiathailand.com")
    
    storage = Storage(CredentialsModel, 'id', user, 'credential')
    credentials = storage.get()
    
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    response = service.calendarList().list().execute()
    
    calendar_summaries = [cal['summary'].lower() for cal in response['items']]
    
    
    if 'account payables' not in calendar_summaries:
        calendar = {
            'summary': 'Account Payables',
            'timeZone': 'Asia/Bangkok'
        }
        ap_cal = service.calendars().insert(body=calendar).execute()
        
        service.calendarList().insert(body={
            'id': ap_cal['id']
        }).execute()
    else:
        for cal in response['items']:
            if cal['summary'].lower() == 'account payables':
                ap_cal = cal
        
    
    response = service.acl().list(calendarId=ap_cal['id']).execute()
    acl_users = [acl['scope']['value'] for acl in response['items']]
    
    group = Group.objects.get(name="Accountant")
    
    for user in group.user_set.all():
        if user.email not in acl_users:
            acl = {
                'scope': {
                    'type': 'user',
                    'value': user.email
                },
                'role': 'owner'
            }
            response = service.acl().insert(body=acl, calendarId=ap_cal['id']).execute()
            
    logger.debug(service.acl().list(calendarId=ap_cal['id']).execute())
    
    evt = {
        'summary': 'tes23t',
        'start': {
            'date': '2016-1-6'
        },
        'end': {
            'date': '2016-1-6'
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'email', 'minutes': 24 * 60},
              {'method': 'email', 'minutes': 10},
            ]
        }
    }
    response = service.events().insert(calendarId=ap_cal['id'], body=evt).execute()
    
    


