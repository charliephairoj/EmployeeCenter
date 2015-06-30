#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieves a list of Orders and products to be shipped 
in the 30 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""

import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from decimal import Decimal
from datetime import timedelta, datetime, date
import logging

import boto
from django.template.loader import render_to_string
from django.conf import settings

from django.db.models import Q, Sum
from acknowledgements.models import Acknowledgement

django.setup()


logger = logging.getLogger(__name__)


def sort_orders():
    """
    Sorts all the fabrics in the system in to physical shelves, taking into 
    account maximum capacity, proximity grouping by pattern, and checking
    if there is actually quantity before assigning a shelf
    """
    acknowledged = Acknowledgement.objects.filter(status__icontains='acknowledged')
    shipped = Acknowledgement.objects.filter(status__icontains='shipped')
    invoiced = Acknowledgement.objects.filter(status__icontains='invoiced')
    
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:1em 0.5em;
                 text-align:center;
                 font-size:1;
                 font-family:Tahoma;
                 max-height:5em;
                 """
    header_cell_style = """
                        border-right:1px solid #595959;
                        border-bottom:1px solid #595959;
                        border-top:1px solid #595959;
                        padding:1em;
                        """
    item_cell_style = """
                      padding:0.75em 0.25em;
                      """
    
        
    #return self.message
    return render_to_string('order_summary_email.html', {'header_style': header_cell_style,
                                                         'cell_style': cell_style,
                                                         'item_cell_style': item_cell_style,
                                                         'shipped': shipped,
                                                         'acknowledged': acknowledged,
                                                         'invoiced': invoiced})
        
        
# Run the fabric sort function if calling from command line
if __name__ == "__main__":
    
    message = sort_orders()
    e_conn = boto.ses.connect_to_region('us-east-1')
    e_conn.send_email('noreply@dellarobbiathailand.com',
                      'Fabric Organization',
                      message,
                      ["charliep@dellarobbiathailand.com"],
                      format='html')
    