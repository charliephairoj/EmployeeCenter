"""
Retrieves a list of Orders and products to be shipped 
in the 14 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""


import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
import json
from decimal import Decimal
import re
import csv
from threading import Thread
from time import sleep
import multiprocessing

from supplies.models import Supply
from products.models import Upholstery, Model, Configuration, Supply as ProductSupply


django.setup()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


if __name__ == '__main__': 
    
    upholstery = Upholstery.objects.get(description='DW-1201 Chair')
    print upholstery.calculate_lumber_quantity()
    