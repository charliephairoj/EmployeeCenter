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
from django.db.models import Count
from contacts.models import Customer
from acknowledgements.models import Acknowledgement as A
from trcloud.models import TRSalesOrder as SO
from estimates.models import Estimate as E
from po.models import PurchaseOrder as PO
from hr.models import Attendance, Employee
from hr.PDF import AttendancePDF
from supplies.models import Log, Supply, Product
from administrator.models import User 


if __name__ == '__main__':
    
    supplies = Supply.objects.annotate(dup=Count('products__supplier_id'), tot=Count('products__supply_id')).order_by('-dup', 'id').filter(dup__gt=1)
    for s in supplies:
        products = s.products.all().order_by('id')
    """

    products = Product.objects.annotate(num=Count('supply_id', 'supplier')).order_by('-num')[0:20]
    for p in products:
        print p.supply.id, p.supplier_id, p.supply.description

    """