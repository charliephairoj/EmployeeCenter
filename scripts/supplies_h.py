"""
Retrieves a list of Orders and products to be shipped 
in the 14 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""


import sys, os
sys.path.append('/Users/apple/Sites/employee/back')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
from decimal import Decimal
from math import ceil
from datetime import timedelta, datetime

from pytz import timezone
import boto.ses
from django.db.models import Avg, Max, Sum

from supplies.models import Supply, Log


class SupplyEmail(object):
    queryset = Supply.objects.all()
    message = ""
    status_width = "18mm"
    customer_width = "auto"
    section_style = """
                    display: block; 
                    font-family:Tahoma;
                    font-size:3mm;
                    color:#595959;
                    width:190mm;
                    """
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:0.5em 0.2em;
                 text-align:center;
                 font-size:0.8em;
                 font-family:Tahoma;
                 """
    header_cell_style = """
                        border-right:1px solid #595959;
                        border-bottom:1px solid #595959;
                        border-top:1px solid #595959;
                        padding:1em;
                        """
    item_cell_style = """
                      border-bottom:1px solid #595959;
                      border-right:1px solid #595959;
                      """
    
    def __init__(self, *args, **kwargs):
        #super(self, AcknowledgementEmail).__init__(*args, **kwargs)
        
        self.start_date = datetime.today() - timedelta(days=7)
        self.end_date = datetime.today() + timedelta(days=1)
        self.queryset = self.queryset.filter(log__timestamp__range=[self.start_date,
                                                                   self.end_date])
        self.queryset = self.queryset.distinct()
        self.queryset = self.queryset.order_by('description')
        self.logs = Log.objects.filter(timestamp__gte=self.start_date, 
                                       timestamp__lte=self.end_date)
        print self.logs.count()
    def create(self):
        self.message = """<div style='{section_style}'>
                              {log}
                          </div>
                          <div style='{section_style}page-break-before: always;'>
                              {buying_guide}
                          </div>
                       """.format(log=self._create_log_section(self.logs),
                                  buying_guide=self._create_buy_section(self.queryset),
                                  section_style=self.section_style)
    
    def get_message(self):
        return self.message
    
    def _create_log_section(self, logs):
        """
        Creates a table of orders
        """
        heading = "Supply Log ({0} - {1})".format(self.start_date.strftime('%B %d, %Y'),
                                                  self.end_date.strftime('%B %d, %Y')) 
        self.message += """
                        <table border='0' cellpadding='0' cellspacing='0'>
                        <thead>
                        <tr>
                        <th style="text-align:center; 
                                   border-top:1px solid #595959;
                                   border-left:1px solid #595959;
                                   border-right:1px solid #595959;
                                   padding:1em 0;
                                   font-size:1.2em;"
                            colspan="4">
                        {heading}</th>
                        </tr>
                        <tr>
                        <th style="{cell_style}border-left:1px solid #595959;">Description</th>
                        <th style="{cell_style}">Action</th>
                        <th style="{cell_style}">Quantity</th>
                        <th style="{cell_style}">Timestamp</th>
                        </tr>
                        </thead>
                        """.format(cell_style=self.header_cell_style,
                                   status_width=self.status_width,
                                   customer_width=self.customer_width,
                                   heading=heading)
        for log in logs:
            self.message += "<tr>"
            self.message += u"""
                            <td style="{cell_style}border-left:1px solid #595959;text-align:left;">{description}</td>
                            <td style="{cell_style}">{action}</td>
                            <td style="{cell_style}">{quantity}</td>
                            <td style="{cell_style}">{timestamp}</td>
                            """.format(id=log.id, 
                                       description=log.message,
                                       action=log.action,
                                       quantity=log.quantity,
                                       timestamp=log.timestamp.strftime('%B %d, %Y %H:%M'),
                                       cell_style=self.cell_style)
            self.message += "</tr>"
            
        self.message += "</table>"
        
        return self.message
    
    def _create_buy_section(self, supplies):
        """
        Creates a buying guide for the supplies
        who's quantities have changed recently
        """
        #Filter to supplies that have reduced quantities down
        supplies = supplies.filter(log__timestamp__range=[self.start_date, self.end_date], 
                                   log__action='SUBTRACT')
        
        table = "<table cellpadding='0' cellspacing='0' style='width:100%;'>"
        table += """<thead>
                        <tr>
                        <th style="text-align:center; 
                                   border-top:1px solid #595959;
                                   border-left:1px solid #595959;
                                   border-right:1px solid #595959;
                                   padding:1em 0;
                                   font-size:1.2em;"
                            colspan="5">
                        {heading}</th>
                        </tr>
                        <tr>
                        <th style="{cell_style}border-left:1px solid #595959;">Description</th>
                        <th style="{cell_style}">Current Quantity</th>
                        <th style="{cell_style}">Average/Day</th>
                        <th style="{cell_style}">Max/Day</th>
                        <th style="{cell_style}">Total/Week</th>
                        </tr>
                    </thead>
                 """.format(heading="Purchasing Guide",
                            cell_style=self.header_cell_style)
        for supply in supplies:
            stats = self._get_stats(supply)
            table += """<tr>
                            <td style="{cell_style}border-left:1px solid #595959;">{description}</td>
                            <td style="{cell_style}">{quantity}</td>
                            <td style="{cell_style}">{avg_quantity}</td>
                            <td style="{cell_style}">{max_quantity}</td>
                            <td style="{cell_style}">{total}</td>
                        </tr>
                     """.format(description=supply.description,
                                quantity=supply.quantity,
                                avg_quantity=ceil(stats['avg']),
                                max_quantity=stats['max'],
                                total=stats['sum'],
                                cell_style=self.cell_style)
        
        table += "</table>"
        return table         
        
    def _get_stats(self, supply):
        pre_aggregate = supply.log_set.filter(timestamp__range=[self.start_date, self.end_date], action='SUBTRACT')
        
        if len(pre_aggregate) == 0:
            return False
        
        max = pre_aggregate.aggregate(Max('quantity'))['quantity__max']
        sum = pre_aggregate.aggregate(Sum('quantity'))['quantity__sum']
        print supply.description, max, sum, pre_aggregate

        avg = sum/7
        return {'sum': sum,
                'max': max,
                'avg': avg}
            
if __name__ == "__main__":
    email = SupplyEmail()
    email.create()
    message = email.get_message()
    with open('test.html', 'w') as file:
        file.write(message)
    """
    e_conn = boto.ses.connect_to_region('us-east-1')
    e_conn.send_email('noreply@dellarobbiathailand.com',
                      'Delivery Schedule',
                      message,
                      ['charliep@dellarobbiathailand.com'],#["deliveries@dellarobbiathailand.com"],
                      format='html')
    """








