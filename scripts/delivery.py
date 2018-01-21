#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Retrieves a list of Orders and products to be shipped 
in the 30 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""

import sys, os, django
from decimal import Decimal
from datetime import timedelta, datetime
import logging
import pprint

sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()
pp = pprint.PrettyPrinter(width=1, indent=1)
logger = logging.getLogger(__name__)

from django.template.loader import render_to_string
from django.conf import settings
import boto
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from pytz import timezone
import boto.ses
from django.db.models import Avg, Max, Sum
from reportlab.lib import colors, utils
from reportlab.pdfbase import pdfdoc
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from acknowledgements.models import Acknowledgement


django.setup()
        

class AcknowledgementEmail(object):
    queryset = Acknowledgement.objects.exclude(status="cancelled").exclude(status="shipped").exclude(status="paid")
    message = "<div style='font-family:Tahoma;font-size:3mm;color:#595959;width:190mm'>"
    status_width = "18mm"
    customer_width = "auto"
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:1em 0em;
                 text-align:center;
                 font-family:Tahoma;
                 """
    header_cell_style = """
                        border-right:1px solid #595959;
                        border-bottom:1px solid #595959;
                        border-top:1px solid #595959;
                        padding:1em 0;
                        """
    item_cell_style = """
                      padding:0.75em 0em;
                      border-bottom: 1px solid rgba(0,0,0,0.3);
                      """
                      
    status_cell = """
                  color: #DDD;
                  text-align:center;
                  """
    
    def __init__(self, *args, **kwargs):
        #super(self, AcknowledgementEmail).__init__(*args, **kwargs)
        
        date = datetime.today()
        self.start_date = date - timedelta(days=4)
        self.end_date = self.start_date + timedelta(days=45)
        logger.debug(self.start_date)
        logger.debug(self.end_date)
        self.queryset = self.queryset.filter(_delivery_date__range=[self.start_date,
                                                                    self.end_date])

        self.queryset = self.queryset.order_by('_delivery_date')

        #self.queryset = Acknowledgement.objects.raw("""
        #SELECT id, delivery_date, status from acknowledgements_acknowledgement
        #where (delivery_date <= now() + interval '31 days' AND delivery_date >= now() - interval '31 days')
        #OR (delivery_date > now() - interval '14 days' AND 
        #(lower(status) = 'acknowledged' OR lower(status) = 'deposit received' OR lower(status) = 'in production' OR lower(status) = 'ready to ship'))
        #ORDER BY delivery_date""")
        
        self.acks = []
        

        for ack in self.queryset:
            for status in ['opened', 'deposit received', 'in production', 'ready to ship', 'shipped', 'invoiced', 'paid']:
                if ack.logs.filter(message__icontains=status).exists(): 
                    setattr(ack, '_'.join(status.split(' ')), True) 
                else:
                    setattr(ack, '_'.join(status.split(' ')), False)
                  
            ack.inspection_date = ack.delivery_date - timedelta(days=3)

            self.acks.append(ack)
            
    def get_message(self):
        #return self.message
        return render_to_string('delivery_email.html', {'acknowledgements': self.acks,
                                                        'header_style': self.header_cell_style,
                                                        'cell_style': self.cell_style,
                                                        'item_cell_style': self.item_cell_style,
                                                        'status_cell': self.status_cell,
                                                        'start_date': self.start_date,
                                                        'end_date': self.end_date})       
            
            
if __name__ == "__main__":
    email = AcknowledgementEmail()
    message = email.get_message()
    
    e_conn = boto.ses.connect_to_region('us-east-1')
    e_conn.send_email('noreply@dellarobbiathailand.com',
                      'Delivery Schedule',
                      message,
                      ["deliveries@dellarobbiathailand.com"],
                      format='html')
   







