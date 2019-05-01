"""
Retrieves a list of Orders and products to be shipped 
in the 14 day period starting today, and creates an 
html message. This email message is then sent to 
the email address
"""


import sys, os
sys.path.append('/Users/charliephairojmahakij/Sites/EmployeeCenter')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
from decimal import Decimal
from datetime import timedelta, datetime

from pytz import timezone
import boto.ses

from acknowledgements.models import Acknowledgement


class AcknowledgementScheduleHTML(object):
    queryset = Acknowledgement.objects.all()
    message = "<div style='font-family:Tahoma;font-size:3mm;color:#595959;width:190mm'>"
    status_width = "18mm"
    customer_width = "auto"
    cell_style = """
                 border-bottom:1px solid #595959;
                 border-right:1px solid #595959;
                 padding:1em 0;
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
        
        self.start_date = datetime.today()
        self.end_date = self.start_date + timedelta(days=31)
        self.queryset = self.queryset.filter(delivery_date__range=[self.start_date,
                                                                   self.end_date])
        self.queryset = self.queryset.order_by('delivery_date')
        
    def create(self):
        self.message = self._create_order_section(self.queryset) + "</div>"
    
    def get_message(self):
        return """
               <script>window.print()</script>
               """+self.message
    
    def _create_order_section(self, orders):
        """
        Creates a table of orders
        """
        heading = "Acknowledgements ({0} - {1})".format(self.start_date.strftime('%B %d, %Y'),
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
                            colspan="8">
                        {heading}</th>
                        </tr>
                        <tr>
                        <th style="{cell_style}border-left:1px solid #595959;padding:1em 0.25em; width:45em;">Ack #</th>
                        
                        <th style="{cell_style}">Project</th>
                        <th style="{cell_style}width:{status_width};font-size:0.6em;">Status</th>
                        <th style="{cell_style}">Delivery Date</th>
                        <th style="{cell_style}width:15em;padding:1em 0.1em">Description</th>
                        <th style="{cell_style}width:5em;padding:1em 0">Qty</th>
                        </tr>
                        </thead>
                        """.format(cell_style=self.header_cell_style,
                                   status_width=self.status_width,
                                   customer_width=self.customer_width,
                                   heading=heading)
        for order in orders:
        
            #Set the project name
            if order.project:
                project_name = order.project.codename
            else:
                project_name = ""
                
            self.message += "<tr>"
            self.message += u"""
                            <td style="{cell_style}border-left:1px solid #595959;padding:1em 0.25em; width:45em; text-align:left;">
                                Order #: {id}
                                <br />
                                Customer: {customer}
                            </td>
                            
                            <td style="{cell_style}">{project}</td>
                            <td style="{cell_style}width:{status_width};">{status}</td>
                            <td style="{cell_style}">{dd}</td>
                            <td style="width:20em;" colspan='2'>{items}</td>
                            """.format(id=order.id, 
                                       customer=order.customer.name,
                                       comments=order.remarks,
                                       project=project_name,
                                       status=order.status,
                                       dd=order.delivery_date.strftime('%b %d, %Y'),
                                       items=self._create_item_section(order.items.all()),
                                       cell_style=self.cell_style,
                                       status_width=self.status_width,
                                       customer_width=self.customer_width)
            self.message += "</tr>"
            
        self.message += "</table>"
        
        return self.message
    
    def _create_item_section(self, items):
        table = "<table cellpadding='0' cellspacing='0' style='width:100%;'>"
        for item in items:
            table += "<tr>"
            table += u"""
                     <td style="{cell_style}width:75%;padding:1em 0 1em 1em;">{description}</td>
                     <td style="{cell_style}width:25%;padding:1em 0; text-align:center;">{quantity}</td>
                     """.format(description=item.description,
                                quantity=item.quantity,
                                cell_style=self.item_cell_style)
            table += "</tr>"
            
        table += "</table>"
        
        return table         
            








