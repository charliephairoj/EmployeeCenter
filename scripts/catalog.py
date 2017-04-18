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


os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()

from products.models import Model
from products.PDF import CatalogPDF
            
            
if __name__ == "__main__":
    model_str = "PS-905"
    
    model = Model.objects.get(model=model_str)
    
    pdf = CatalogPDF(model=model)
    pdf.create()

    """
    msg = MIMEMultipart()
    msg['Subject'] = 'Payroll: {0} - {1}'.format(start_date, end_date)
    msg['From'] = 'noreply@dellarobbiathailand.com'
    msg['To'] = 'charliep@dellarobbiathailand.com'
    
    part = MIMEApplication(open(payroll.pdf.filename, 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename=payroll.pdf.filename)
    msg.attach(part)
    connection = boto.connect_ses()
    result = connection.send_raw_email(msg.as_string(), source=msg['From'], destinations=[msg['To']])
    """
    




