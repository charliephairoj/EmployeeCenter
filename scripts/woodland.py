#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import csv
import os
import requests
import json
import hashlib
import time
import math
import subprocess
import pprint
import logging
from datetime import datetime, timedelta, date

sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()
pp = pprint.PrettyPrinter(width=1, indent=1)
logger = logging.getLogger(__name__)

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import boto
from contacts.models import Customer
from acknowledgements.models import Acknowledgement as A
from trcloud.models import TRSalesOrder as SO
from estimates.models import Estimate as E
from po.models import PurchaseOrder as PO
from hr.models import Attendance, Employee
from hr.PDF import AttendancePDF
from supplies.models import Log

from django.contrib.auth.models import User as U


if __name__ == '__main__':
    logs = Log.objects.filter(timestamp__gte='2018-01-01').exclude(action='PRICE CHANGE').order_by('-timestamp')
    for l in logs:
        print l.id, l.action, l.message, l.timestamp

    with open('supply_transaction.csv', 'wb') as file:
        writer = csv.writer(file, delimiter=',')

        for l in logs:
            data = [str(l.id), l.action, l.message, l.timestamp.strftime('%H:%M:%S %d-%m-%Y')]
            encoded_data = [d.encode('utf-8') for d in data]
            writer.writerow(encoded_data)

       