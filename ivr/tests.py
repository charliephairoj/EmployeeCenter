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


from django.test import TestCase
from twilio.rest import Client
from django.conf import settings



client = Client(settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN)

call = client.calls.create(url="https://e8ae2222.ngrok.io/api/v1/ivr/test/",
                           to="+6625088681",
                           from_="+15005550006")

logger.debug(call)
logger.debug(call.sid)
logger.debug(call.__dict__)