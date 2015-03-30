#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from decimal import *

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q, Sum
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from hr.models import Employee
from projects.models import Project, ItemSupply
from contacts.models import Supplier
from po.models import PurchaseOrder as PO
from acknowledgements.models import Item as AckItem


django.setup()

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class ProjectPDF(object):
    project = Project.objects.get(codename__icontains="mc house")
    
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
     
    def create(self):
        doc = SimpleDocTemplate('Project-Summary({0}).pdf'.format(self.project.codename), 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        # Create the document title
        title_text = u"{0}: Project Summary".format(self.project.codename)
        style = ParagraphStyle(name='Normal',
                               alignment=TA_CENTER,
                               fontName='Garuda',
                               fontSize=20,
                               textColor=colors.CMYKColor(black=60))
        title = Paragraph(title_text, style)
        title.hAlign = "CENTER"
        stories.append(title)
        stories.append(Spacer(0, 50))
        
        # Create the summary of the project
        summary = self._create_and_append_summary_section()
        summary.hAlign = "LEFT"
        stories.append(summary)
            
        #Create room details section
        stories = self._create_and_append_room_details_section(stories)
        
        doc.build(stories)
        
    def _create_and_append_summary_section(self, stories=None):
        """
        Creates a summary of the project
        
        -name of project
        -customer of the project
        -total units
        -total phases
        -total room
        -total purchase orders
        -total acknowledgeents
        -total parts
        -total items

        """
        data = []
        data.append(["Project Name:", self.project.codename])
        data.append(["Number of Units:", self.project.quantity])
        if self.project.customer:
            data.append(["Customer:", self.project.customer.name])
        data.append(["Rooms:", ''])
        data.append([self._create_room_summary(self.project), ''])
        data.append(["Phases:", ''])
        data.append([self._create_phase_summary(self.project), ''])
        data.append(["Suppliers:", ''])
        data.append([self._create_supplier_summary(self.project), ''])
        
        items = AckItem.objects.filter(acknowledgement__project=self.project).count()
        
        data.append(['Acknowledgements:', items])
        data.append(['Purchase Orders:', self.project.purchase_orders.all().count()])
        total_dict = self.project.purchase_orders.aggregate(Sum('grand_total'))
        total = total_dict['grand_total__sum']
        data.append(['', "{0:,.2f}".format(total)])
        
        table = Table(data, colWidths=(200, 000))
        
        return table
        
    def _create_and_append_room_details_section(self, stories=None):
        
        stories.append(PageBreak())
        for room in self.project.rooms.all():
                stories.append(self._create_room_details(room))
                stories.append(PageBreak())
                    
        return stories
    
    def _create_room_summary(self, project):
        data = []
        
        for index, room in enumerate(project.rooms.all()):
            index += 1
            data.append([index, room.description])
            
        table = Table(data, colWidths=(200, 200))
        
        return table
        
    def _create_phase_summary(self, project):
        data = [['', '']]
        
        for index, phase in enumerate(project.phases.all()):
            index += 1
            data.append([index, phase.description])
            
        table = Table(data, colWidths=(200, 200))
        
        return table
    
    def _create_supplier_summary(self, project):
        data = []
        
        for supplier in Supplier.objects.filter(purchaseorder__project=project).distinct():
            total = PO.objects.filter(project=project, supplier=supplier).aggregate(Sum('grand_total'))
            total = total['grand_total__sum']
            data.append([supplier.name, "{0:,.2f}".format(total)])
        table = Table(data, colWidths=(200, 200))
        
        return table
        
    def _create_room_details(self, room):
        data = [["Room:", room.description]]
        data.append(['', self._create_room_items(room)])
        table = Table(data, colWidths=(200, 200))
        
        return table
        
    def _create_room_items(self, room):
        data = [['', '']]
        
        for item in room.items.all():
            data.append([item.description, item.quantity])
            
            for part in item.parts.all():
                data.append([part.description, part.quantity])
            data.append(['', ''])
            
            for supply in item.supplies.all():
                quantity = ItemSupply.objects.get(supply=supply, item=item).quantity
                data.append([supply.description, "{0:,.2f}".format(quantity)])
        for item in AckItem.objects.filter(acknowledgement__project=self.project):
            data.append([item.description, item.quantity])
            data.append(['', ''])
            
        return Table(data, colWidths=(200, 200))
        
    def _prepare_text(self, description, font_size=8):
        
        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               alignment=TA_LEFT,
                               fontName='Garuda',
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
        
    
if __name__ == "__main__":
    pdf = ProjectPDF()
    pdf.create()