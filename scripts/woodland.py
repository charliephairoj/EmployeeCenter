#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import requests
import json
import hashlib
import time
import math
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()

from po.models import PurchaseOrder as PO

po = PO.objects.all()[0]

po.create_and_upload_pdf()
print po.pdf.generate_url()

