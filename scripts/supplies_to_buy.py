#!/usr/bin/python

import sys, os, django
sys.path.append('/home/django_worker/backend')
sys.path.append('/Users/Charlie/Sites/employee/backend')

from django.conf import settings
from django.core.wsgi import get_wsgi_application
import logging
from decimal import *
import decimal
from math import ceil
from datetime import timedelta, datetime, date
from copy import deepcopy

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

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()


from supplies.models import Supply, Log, Product

getcontext().prec = 2
logger = logging.getLogger(__name__)


#pdfdoc.PDFCatalog.OpenAction = '<</S/JavaScript/JS(this.print\({bUI:false,bSilent:true,bShrinkToFit:true}\);)>>'

class SupplyPDF():
    name_map = {'id': 'id',
                'description': 'description',
                'quantity': 'quantity',
                'to_buy': 'to_buy'}
    supplies = None
    layout_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                    ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                    ('ALIGNMENT', (-3,0), (-1,-1), 'RIGHT'),
                    ('TOPPADDING', (0,0), (-2,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-2,-1), 3),
                    ('LEFTPADDING', (0,0), (-2,-1), 6),
                    ('RIGHTPADDING', (0,0), (-2,-1), 6),
                    ('TOPPADDING', (-1,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (-1,0), (-1,-1), 0),
                    ('LEFTPADDING', (-1,0), (-1,-1), 0),
                    ('RIGHTPADDING', (-1,0), (-1,-1), 0),
                    ('FONTSIZE', (0,0), (-1,-1), 10)]
                    
    details_style = [#('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGNMENT', (0,0), (0,-1), 'LEFT'),
                    ('ALIGNMENT', (-3,0), (-1,-1), 'RIGHT'),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3 ),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('FONTSIZE', (0,0), (-1,-1), 10)]
                    
    running_total = 0
    
    def __init__(self, *args, **kwargs):
        self.supplies = Supply.objects.raw("""WITH weekly_average as (
                        SELECT s.id as id, sum(sl.quantity) as week_total
                        FROM supplies_log as sl
                        INNER JOIN supplies_supply as s
                        ON s.id = sl.supply_id
                        GROUP BY s.id, sl.action, date_trunc('week', log_timestamp)
                        HAVING (date_trunc('week', log_timestamp) > NOW() - interval '4 weeks'
                        AND sl.action = 'SUBTRACT'))
                        SELECT s.id, s.description, s.quantity, 
                        (SELECT round(avg(week_total), 2) FROM weekly_average WHERE id = s.id) as to_buy
                        FROM supplies_supply as s
                        WHERE (id in (SELECT id from weekly_average WHERE id = s.id)
                        OR id in (SELECT supply_id FROM supplies_log))
                        AND s.quantity < ((SELECT avg(week_total) FROM weekly_average WHERE id = s.id) * 2)
                        ORDER BY s.quantity, s.description""", translations=self.name_map)

    def create(self):
        doc = SimpleDocTemplate('Supplies_to_Buy.pdf', 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        stories.append(self._create_supply_table())
        doc.build(stories)
        
    def _create_supply_table(self):
        subtable = Table([['Supplier',
                          'Cost', 
                          'Units',
                          'Total']], colWidths=(175, 55, 55, 115))
        subtable.setStyle(TableStyle(self.details_style))
        data = [['ID', 'Description', 'Qty', 'Qty to Buy', subtable]]
        for supply in self.supplies:
            
            style = ParagraphStyle(name='Normal',
                                   fontName='Tahoma',
                                   leading=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            description = Paragraph(supply.description,
                                  style)
                                  
            data.append([supply.id,
                         description,
                         supply.quantity,
                         u"{0} {1}".format(supply.to_buy, supply.units),
                         self._create_suppliers_table(supply, supply.to_buy)])
        data.append(['', '', '', 'Total', "{0:f}".format(self.running_total)])
        table = Table(data, colWidths=(50, 225, 55, 75, 405))
        table.setStyle(TableStyle(self.layout_style))
        return table
    
    def _create_suppliers_table(self, supply, quantity):
        data = []
        best = ()
        for index, product in enumerate(Product.objects.filter(supply=supply)):
            unit_cost = self._get_unit_cost(product)
            
            if best == ():
                best = (unit_cost, index, product)
            elif unit_cost < best[0]:
                best = (unit_cost, index, product)
                                           
            data.append([product.supplier.name,
                         product.cost,
                         product.purchasing_units,
                         self._get_total_str(supply, product, quantity)])
        
        if len(data) == 0:
            data = [['NA', 'NA', 'NA', 'NA']]
            
        table = Table(data, colWidths=(180, 55, 55, 115))
        
        #Append style for best price
        style = deepcopy(self.details_style)
        if best:
            style.append(('FONTNAME', (0,best[1]), (-1,best[1]), 'Helvetica-Bold'))
        table.setStyle(TableStyle(style))
        
        #calculate total
        try:
            self.running_total += (quantity // best[2].quantity_per_purchasing_unit) * best[2].cost
        except Exception:
            pass
            
        return table
        
    def _get_total_str(self, supply, product, quantity):
        if product.purchasing_units != supply.units:
            if quantity <= product.quantity_per_purchasing_unit:
                total_cost = product.cost
            else:
                try:
                    total_cost = (quantity / product.quantity_per_purchasing_unit) * product.cost
                except Exception as e:
                    print product.quantity_per_purchasing_unit
                    print ""
        else: 
            total_cost = quantity * product.cost
        
        if not product.quantity_per_purchasing_unit:
            product.quantity_per_purchasing_unit = 1
            product.save()
            #raise ValueError("Value should not be {0}".format(product.quantity_per_purchasing_unit))
        
        
        logger.debug(u"{2} {0} : {1}".format(quantity, product.quantity_per_purchasing_unit, product.supply.description))
        try:
            buying_qty = (quantity // product.quantity_per_purchasing_unit)
        except decimal.InvalidOperation:
            buying_qty = quantity
            
        buying_qty = buying_qty if buying_qty > 0 else 1
        total_str = "{0:f} for {1} {2}".format(total_cost, 
                                       buying_qty,
                                       product.purchasing_units)
        return total_str
        
    def _get_unit_cost(self, product):
        try:
            unit_cost =  product.cost / product.quantity_per_purchasing_unit
        except TypeError as e:
            unit_cost = product.cost
            
        try:
            if product.supplier.discount:
                unit_cost = unit_cost - ((product.supplier.discount/Decimal('100')) * unit_cost)
        except Exception as e:
            print e
            print "\n"
            
        return unit_cost

if __name__ == "__main__":
    supplyPDF = SupplyPDF()
    supplyPDF.create()
    
    msg = MIMEMultipart()
    msg['Subject'] = 'Supply Shopping List'
    msg['From'] = 'noreply@dellarobbiathailand.com'
    msg['To'] = 'charliep@dellarobbiathailand.com'
    
    part = MIMEApplication(open('Supplies_to_Buy.pdf', 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename='shopping-list.pdf')
    msg.attach(part)
    connection = boto.connect_ses()
    result = connection.send_raw_email(msg.as_string(), source=msg['From'], destinations=[msg['To']])
    print result
    
    
