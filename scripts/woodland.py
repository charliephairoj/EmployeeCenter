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
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()

from contacts.models import Customer
from acknowledgements.models import Acknowledgement as A
from trcloud.models import TRSalesOrder as SO

a = A.objects.all().order_by('-id')[0]
a.company = "alinea group"
a.save()
a.create_and_upload_pdfs()

print "\n"+a.acknowledgement_pdf.generate_url()
print "\n"+a.production_pdf.generate_url()
print "\n"+a.label_pdf.generate_url()


#subprocess.call(cmd, shell=True)

#data = SO.search('holbrook')
#for i in data:
#    print i['id']



