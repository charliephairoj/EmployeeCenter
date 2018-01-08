#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import requests
import json
import hashlib
import time
import math
import subprocess
import pprint
import logging
from datetime import datetime, timedelta

sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()
pp = pprint.PrettyPrinter(width=1, indent=1)
logger = logging.getLogger(__name__)


from contacts.models import Customer
from acknowledgements.models import Acknowledgement as A
from trcloud.models import TRSalesOrder as SO
from estimates.models import Estimate as E
from po.models import PurchaseOrder as PO
from administrator.models import User as U

acks = A.objects.all().order_by('-_delivery_date')[0:100]

for a in acks:
    try:
        a.update_calendar_event(user=U.objects.get(pk=1))
        a.save()
    except Exception as e:
        logger.debug(e)
