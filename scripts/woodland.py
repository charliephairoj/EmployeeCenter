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

d = datetime.now() - timedelta(days=34)
po = PO.objects.filter(order_date__gte=d).order_by('-id')[1]
po.email_approver()

"""

a = A.objects.all().order_by('-id')[0]

logger.debug(pp.pformat(a.__dict__))
a.trcloud_id = None

a.create_in_trcloud()


a.update_in_trcloud()
"""