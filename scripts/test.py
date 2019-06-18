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
import logging

from django.db import connections
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
            

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


if __name__ == "__main__":

    with connections['trcloud'].cursor() as trcloud_cur:

        trcloud_cur.execute("SELECT invoice_id, invoice_number FROM invoice limit 5")
        row = trcloud_cur.fetchone()
        logger.debug(row)

    
    
    
