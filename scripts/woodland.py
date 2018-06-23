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
    # Remove duplicate products
    """
    supplies = Supply.objects.annotate(dup=Count('products__supplier_id'), tot=Count('products__supply_id')).order_by('-dup', 'id').filter(dup__gt=1)[0:1]
    for s in supplies:
        products = s.products.all().order_by('id')
        dd = {}
        logger.debug(u"{0} {1}".format(s.id, s.description))
        for p in products:
            print "\n"
            logger.debug(u"    {0} {1}".format(p.supplier_id, p.supplier.name))

            if p.supplier_id in dd:
                dd[p.supplier_id].append(p)
            else:
                dd[p.supplier_id] = [p,]

        for k in dd:
            if len(dd[k]) > 1:
                for i, sp in enumerate(dd[k]):
                    if i == 0:
                        logger.debug(sp.__dict__)
                        main = sp
                    else:
                        logger.debug(u"        {0} {1} {2}".format(sp.id, sp.supplier_id, sp.supplier.name))
                        #s.products.filter(pk=sp.id).delete()

                assert s.products.filter(pk=sp.id).count() <= 0

        print '\n\n\n'
    """
    
    dup_customers = Customer.objects.values('name').annotate(num=Count('name')).order_by('name')

    for c in dup_customers:
        #logger.debug(u'{0}  {1}'.format(c['num'], c['name']))


        cs = Customer.objects.filter(name=c['name'].strip())
        if cs.count() > 1:

            for cc in cs:
            
                a = [f for f in cc._meta.get_fields()
                if (f.one_to_many or f.one_to_one)
                and f.auto_created and not f.concrete]


                logger.debug(a)

                for f in a:
                    logger.debug(f.name)
                    logger.debug(f.related_model)

