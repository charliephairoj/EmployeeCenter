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
from datetime import timedelta, datetime
import logging

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


class DeliveryPDF(object):
    queryset = Acknowledgement.objects.all()
    
    def __init__(self, *args, **kwargs):
        #super(self, AcknowledgementEmail).__init__(*args, **kwargs)
        
        self.start_date = datetime.today()
        self.end_date = self.start_date + timedelta(days=31)
        self.queryset = self.queryset.filter(delivery_date__range=[self.start_date,
                                                                   self.end_date])
        self.queryset = self.queryset.order_by('delivery_date')
        
    def create(self):
        doc = SimpleDocTemplate('delivery.pdf', 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        stories.append(self._create_main_table())
        doc.build(stories)
        
    def _create_main_table(self):
        
        # Create the headings
        data = [["#", "Customer", "Comments", "Status", "Delivery Date", "Description", "Fabric", "Qty"]]
        
        for ack in self.queryset:
            data.append([ack.id,
                         ack.customer.name,
                         u"{0}".format(ack.remarks),
                         ack.status,
                         ack.delivery_date,
                         ""])#self._create_items_table(ack)])
                         
        table = Table(data, colWidths=(50, 100, 100, 75, 100, 100, 100, 50))
        table.setStyle(TableStyle([('SPAN', (-2, 1), (-1, -1))]))
        return table
                         
    def _create_items_table(self, ack):
        
        data = []
        
        if ack.items.count() < 5:
            for item in ack.items.all():
                item_array = [item.description]
            
                if item.fabric:    
                    item_array.append(item.fabric.description)
                else:
                    item_array.append("")
                
                item_array.append(item.quantity)
            
                data.append(item_array)
                """
                for pillow in item.pillows.all():
                    pillow_array = [u"    -{0} pillow".format(pillow.type)]
                
                    if pillow.fabric:
                        pillow_array.append("{0}, Col: {1}".format(pillow.fabric.pattern, pillow.fabric.color))  
                    else:
                        pillow_array.append("")     
        
                    pillow_array.append(pillow.quantity)
                
                    data.append(pillow_array)
                """
        else:
            data.append(["", "", ""])
        table = Table(data, colWidths=(100, 100, 50))

        return table
        
        
class AcknowledgementEmail(object):
    queryset = Acknowledgement.objects.all()
    message = "<div style='font-family:Tahoma;font-size:3mm;color:#595959;width:190mm'>"
    status_width = "18mm"
    customer_width = "auto"
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:1em 0.5em;
                 text-align:center;
                 font-size:0.8;
                 font-family:Tahoma;
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
    
    def __init__(self, *args, **kwargs):
        #super(self, AcknowledgementEmail).__init__(*args, **kwargs)
        
        self.start_date = datetime.today()
        self.end_date = self.start_date + timedelta(days=31)
        self.queryset = self.queryset.filter(delivery_date__range=[self.start_date,
                                                                   self.end_date])
        self.queryset = self.queryset.order_by('delivery_date')
        
    def get_message(self):
        #return self.message
        return render_to_string('delivery_email.html', {'acknowledgements': self.queryset,
                                                        'header_style': self.header_cell_style,
                                                        'cell_style': self.cell_style,
                                                        'item_cell_style': self.item_cell_style,
                                                        'start_date': self.start_date,
                                                        'end_date': self.end_date})       
            
            
if __name__ == "__main__":
    """
    email = AcknowledgementEmail()
    message = email.get_message()
    e_conn = boto.ses.connect_to_region('us-east-1')
    e_conn.send_email('noreply@dellarobbiathailand.com',
                      'Delivery Schedule',
                      message,
                      ["deliveries@dellarobbiathailand.com"],
                      format='html')
    """
    pdf = DeliveryPDF()
    pdf.create()








