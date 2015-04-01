#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from decimal import *
import math

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q, Sum, Max
from django.contrib.auth.models import AnonymousUser
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
from projects.models import Project, ItemSupply, Part, Room, Phase, Item
from contacts.models import Supplier
from po.models import PurchaseOrder as PO
from acknowledgements.models import Item as AckItem
from supplies.models import Supply


django.setup()

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class ProjectPDF(object):
    user = AnonymousUser()
    
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]

    def __init__(self, project=None, user=None, *args, **kwargs):
        
        if project:
            self.project = project
            
        if user:
            self.user = user
            
        super(ProjectPDF, self).__init__(*args, **kwargs)
        
    def create(self, response=None):
        
        if response is None:
            response = 'Project-Summary({0}).pdf'.format(self.project.codename)
        doc = SimpleDocTemplate(response, 
                                pagesize=A4, 
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
        
        #Create room details section
        stories = self._create_and_append_phase_details_section(stories)
        
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
        data.append([self._create_room_overview(self.project), ''])
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
                self._create_and_append_room_details(stories, room)
                stories.append(PageBreak())
                    
        return stories
        
    def _create_and_append_phase_details_section(self, stories=None):
        
        for phase in self.project.phases.all():
                self._create_and_append_phase_details(stories, phase)
                stories.append(PageBreak())
                    
        return stories
    
    def _create_room_overview(self, project):
        data = [['', '']]
        
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
        data = [['', '']]
        
        for supplier in Supplier.objects.filter(purchaseorder__project=project).distinct():
            total = PO.objects.filter(project=project, supplier=supplier).aggregate(Sum('grand_total'))
            total = total['grand_total__sum']
            data.append([supplier.name, "{0:,.2f}".format(total)])
        table = Table(data, colWidths=(200, 200))
        
        return table
        
    def _create_and_append_room_details(self, stories, room):
        # Create and add Room Header
        title = self._prepare_text(room.description, font_size=16, alignment=TA_CENTER)
        stories.append(title)
        stories.append(Spacer(0, 30))
        
        # Create and add supply summary for room
        stories.append(self._prepare_text("Supplies Summary", font_size=12))
        stories.append(Spacer(0, 10))
        room_supplies = self._create_room_supplies_summary(room)
        room_supplies.hAlign = 'LEFT'
        stories.append(room_supplies)
        stories.append(Spacer(0, 30))
        
        # Create and add item breakdown for room
        stories.append(self._prepare_text("Item Breakdown", font_size=12))
        stories.append(Spacer(0, 10))
        items = self._create_room_items(room)
        items.hAlign = 'LEFT'
        stories.append(items)
        
        return stories
    
    def _create_room_supplies_summary(self, room):
        running_total = 0
        data = [['#', 'Description', 'Qty', 'Unit Cost', 'Total']]
        supplies = ItemSupply.objects.filter(item__room=room)
        supplies = supplies.values('supply__description', 'supply').annotate(quantity=Sum('quantity')).order_by('supply')
        for index, supply in enumerate(supplies):
            supply_dict = Supply.objects.get(pk=supply['supply']).products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
            unit_cost = supply_dict['cost__max']
            purchasing_units = supply_dict['purchasing_units']
            q_per_pu = supply_dict['quantity_per_purchasing_unit']
            
            if Supply.objects.get(pk=supply['supply']).units.lower() != purchasing_units.lower():
                unit_cost = unit_cost / q_per_pu
                
            total = unit_cost * Decimal(supply['quantity'])
            running_total += total
            data.append([index + 1, 
                         self._prepare_text(supply['supply__description']),
                         "{0:,.2f}".format(supply['quantity']), 
                         unit_cost, 
                         "{0:,.2f}".format(total)])
                         
        if len(data) == 1:
            data.append(['No Supplies for this Room'])
        else:
            data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
            
        table = Table(data, colWidths=(20, 350, 30, 70, 90), repeatRows=1)
        
        # Create layout and style
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT'), # Cost and total alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('LINEABOVE', (-3, -1), (-1, -1), 1, colors.CMYKColor(black=60)),
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
        
        # Special style if no supplies
        if len(data) == 1:
            pre_styles.append(('SPAN', (0, 1), (-1, 1)))
            pre_styles.append(('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'))
            
        style = TableStyle(pre_styles)
        table.setStyle(style)
        
        return table
        
    def _create_room_items(self, room):
        special_styles = {'indent': [],
                          'bottom_padding': [],
                          'line_above': []}
                       
        data = [['#', 'Description', 'Qty', 'Unit Cost', 'Total']]
        
        for index, item in enumerate(room.items.all()):
            data.append([index + 1, item.description, item.quantity])
            
            data.append(['', self._prepare_text('Parts', bold=True, font='Helvetica')])
            for part in item.parts.all():
                data.append(['', part.description, part.quantity])
                special_styles['indent'].append(len(data) - 1)
                
            
            data.append(['', self._prepare_text('Supplies', bold=True, font='Helvetica')])
            running_total = 0
            for supply in item.supplies.all():
                supply_dict = supply.products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
                unit_cost = supply_dict['cost__max']
                purchasing_units = supply_dict['purchasing_units']
                q_per_pu = supply_dict['quantity_per_purchasing_unit'] or 0
                
                if supply.units.lower() != purchasing_units.lower():
                    unit_cost = unit_cost / q_per_pu
                    
                quantity = ItemSupply.objects.get(supply=supply, item=item).quantity
                total = unit_cost * Decimal(quantity)
                running_total += total
                data.append(['', 
                             supply.description,
                             "{0:,.2f}".format(quantity),
                             unit_cost, 
                             "{0:,.2f}".format(total)])
                special_styles['indent'].append(len(data) - 1)
                
                             
            #Add Total material cost
            data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
            special_styles['bottom_padding'].append(len(data) - 1)
            special_styles['line_above'].append(len(data) - 1)
        
        # Add Items (Loose Furniture) from the acknowledgements
        init_index = room.items.count()
        for index, item in enumerate(AckItem.objects.filter(acknowledgement__room=self.project)):
            data.append([index + init_index + 1, item.description, item.quantity, '', ''])
        
        if len(data) == 1:
            data.append(["No Items for this Room"])
            
        # Create the table
        table = Table(data, colWidths=(20, 350, 30, 70, 90), repeatRows=1)
        
        # Create the style and layout for item breakdown
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT'), # Cost and total alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=20)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)), # Header separator
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
        for row in special_styles['bottom_padding']:
            pre_styles.append(('BOTTOMPADDING', (0, row), (-1, row), 20))
        for row in special_styles['line_above']:
            pre_styles.append(('LINEABOVE', (-3, row), (-1, row), 1, colors.CMYKColor(black=60)))
        for row in special_styles['indent']:
            pre_styles.append(('LEFTPADDING', (1, row), (1, row), 20))

        style = TableStyle(pre_styles)
        
        table.setStyle(style)
        
        return table
        
    def _create_and_append_phase_details(self, stories, phase):
        # Create and add Room Header
        title = self._prepare_text(phase.description, font_size=16, alignment=TA_CENTER)
        stories.append(title)
        stories.append(Spacer(0, 30))
        
        quantity= self._prepare_text("Quantity of Units: {0}".format(phase.quantity), font_size=12)
        stories.append(quantity)
        stories.append(Spacer(0, 20))
        
        # Create and add supply summary for room
        stories.append(self._prepare_text("Supplies Summary", font_size=12))
        stories.append(Spacer(0, 10))
        room_supplies = self._create_phase_supplies_summary(phase)
        room_supplies.hAlign = 'LEFT'
        stories.append(room_supplies)
        stories.append(Spacer(0, 30))
        
        # Create and add item breakdown for room
        stories.append(self._prepare_text("Item Breakdown", font_size=12))
        stories.append(Spacer(0, 10))
        items = self._create_phase_items(phase)
        items.hAlign = 'LEFT'
        stories.append(items)
        
        return stories
    
    def _create_phase_supplies_summary(self, phase):
        running_total = 0
        data = [['#', 'Description', 'Qty', 'Unit Cost', 'Total']]
        supplies = ItemSupply.objects.filter(item__room__project=self.project)
        supplies = supplies.values('supply__description', 'supply').annotate(quantity=Sum('quantity')).order_by('supply')
        for index, supply in enumerate(supplies):
            supply_dict = Supply.objects.get(pk=supply['supply']).products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
            unit_cost = supply_dict['cost__max']
            purchasing_units = supply_dict['purchasing_units']
            q_per_pu = supply_dict['quantity_per_purchasing_unit']
            
            if Supply.objects.get(pk=supply['supply']).units.lower() != purchasing_units.lower():
                unit_cost = unit_cost / q_per_pu
                
            total = unit_cost * Decimal(supply['quantity']) * phase.quantity
            running_total += total
            data.append([index + 1, 
                         self._prepare_text(supply['supply__description']),
                         "{0:,.2f}".format(Decimal(supply['quantity']) * phase.quantity), 
                         unit_cost, 
                         "{0:,.2f}".format(total)])
                         
        if len(data) == 1:
            data.append(['No Supplies for this Room'])
        else:
            data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
            
        table = Table(data, colWidths=(20, 350, 30, 70, 90), repeatRows=1)
        
        # Create layout and style
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT'), # Cost and total alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('LINEABOVE', (-3, -1), (-1, -1), 1, colors.CMYKColor(black=60)),
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
        
        # Special style if no supplies
        if len(data) == 1:
            pre_styles.append(('SPAN', (0, 1), (-1, 1)))
            pre_styles.append(('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'))
            
        style = TableStyle(pre_styles)
        table.setStyle(style)
        
        return table
        
    def _create_phase_items(self, phase):
        special_styles = {'indent': [],
                          'bottom_padding': [],
                          'line_above': []}
                       
        data = [['#', 'Description', 'Qty', 'Unit Cost', 'Total']]
        
        for index, item in enumerate(Item.objects.filter(room__project=self.project)):
            data.append([index + 1, item.description, item.quantity])
            
            data.append(['', self._prepare_text('Parts', bold=True, font='Helvetica')])
            for part in item.parts.all():
                data.append(['', part.description, part.quantity * phase.quantity])
                special_styles['indent'].append(len(data) - 1)
                
            
            data.append(['', self._prepare_text('Supplies', bold=True, font='Helvetica')])
            running_total = 0
            for supply in item.supplies.all():
                supply_dict = supply.products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
                unit_cost = supply_dict['cost__max']
                purchasing_units = supply_dict['purchasing_units']
                q_per_pu = supply_dict['quantity_per_purchasing_unit']
                
                if supply.units.lower() != purchasing_units.lower():
                    unit_cost = unit_cost / q_per_pu
                    
                quantity = ItemSupply.objects.get(supply=supply, item=item).quantity * phase.quantity
                total = unit_cost * Decimal(quantity)
                running_total += total
                data.append(['', 
                             self._prepare_text(supply.description, font='Garuda'),
                             "{0:,.2f}".format(quantity),
                             unit_cost, 
                             "{0:,.2f}".format(total)])
                special_styles['indent'].append(len(data) - 1)
                
                             
            #Add Total material cost
            data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
            special_styles['bottom_padding'].append(len(data) - 1)
            special_styles['line_above'].append(len(data) - 1)
        
        # Add Items (Loose Furniture) from the acknowledgements
        init_index = Item.objects.filter(room__project=self.project).count()
        for index, item in enumerate(AckItem.objects.filter(acknowledgement__phase=self.phase)):
            data.append([index + init_index + 1, item.description, item.quantity, '', ''])
        
        # Create the table
        table = Table(data, colWidths=(20, 350, 30, 70, 90), repeatRows=1)
        
        # Create the style and layout for item breakdown
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT'), # Cost and total alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=20)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)), # Header separator
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
        for row in special_styles['bottom_padding']:
            pre_styles.append(('BOTTOMPADDING', (0, row), (-1, row), 20))
        for row in special_styles['line_above']:
            pre_styles.append(('LINEABOVE', (-3, row), (-1, row), 1, colors.CMYKColor(black=60)))
        for row in special_styles['indent']:
            pre_styles.append(('LEFTPADDING', (1, row), (1, row), 20))
        style = TableStyle(pre_styles)
        table.setStyle(style)
        
        return table
        
    def _prepare_text(self, description, font_size=10, alignment=TA_LEFT, bold=False, font='Garuda'):
        
        text = description if description else u""
        if bold:
            text = "<b>" + text + "</b>"
        style = ParagraphStyle(name='Normal',
                               alignment=alignment,
                               fontName=font,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
        
        
class PhasePDF(object):
    user = AnonymousUser()
    
    def __init__(self, phase=None, user=None, *args, **kwargs):
        
        if phase:
            self.phase = phase
            self.project = self.phase.project
            
        if user:
            self.user = user
            
        super(PhasePDF, self).__init__()
        
    def create(self, response=None):
        
        if response is None:
            response = 'Phase-Summary({0}).pdf'.format(self.phase.description)
        doc = SimpleDocTemplate(response, 
                                pagesize=A4, 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        # Create the document title
        title_text = u"{0}: Project Summary".format(self.phase.project.codename)
        style = ParagraphStyle(name='Normal',
                               alignment=TA_CENTER,
                               fontName='Garuda',
                               fontSize=20,
                               textColor=colors.CMYKColor(black=60))
        title = Paragraph(title_text, style)
        title.hAlign = "CENTER"
        stories.append(title)
        stories.append(Spacer(0, 50))
        
        #Create room details section
        stories = self._create_and_append_phase_details_section(stories)
        
        doc.build(stories)
    
    def _create_and_append_phase_details_section(self, stories=None):
        
        self._create_and_append_phase_details(stories, self.phase)
        stories.append(PageBreak())
                    
        return stories
        
    def _create_and_append_phase_details(self, stories, phase):
        # Create and add Room Header
        title = self._prepare_text(phase.description, font_size=16, alignment=TA_CENTER)
        stories.append(title)
        stories.append(Spacer(0, 30))
        
        quantity= self._prepare_text("Quantity of Units: {0}".format(phase.quantity), font_size=12)
        stories.append(quantity)
        stories.append(Spacer(0, 20))
        
        # Create and add supply summary for room
        if self.user.has_perm('projects.view_project_supplies'):
            stories.append(self._prepare_text("Supplies Summary", font_size=12))
            stories.append(Spacer(0, 10))
            room_supplies = self._create_phase_supplies_summary(phase)
            room_supplies.hAlign = 'LEFT'
            stories.append(room_supplies)
            stories.append(Spacer(0, 30))
        
        # Create and add item breakdown for room
        stories.append(self._prepare_text("Item Breakdown", font_size=12))
        stories.append(Spacer(0, 10))
        items = self._create_phase_items(phase)
        items.hAlign = 'LEFT'
        stories.append(items)
        
        return stories
    
    def _create_phase_supplies_summary(self, phase):
        running_total = 0
        data = [['#', 'Description', 'Qty']]
        
        if self.user.has_perm('projects.view_project_costs'):
            data[0] += ['Unit Cost', 'Total']
            
        supplies = ItemSupply.objects.filter(item__room__project=self.project)
        supplies = supplies.values('supply__description', 'supply').annotate(quantity=Sum('quantity')).order_by('supply')
        for index, supply in enumerate(supplies):
            
            if self.user.has_perm('projects.view_project_costs'):
            
                supply_dict = Supply.objects.get(pk=supply['supply']).products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
                unit_cost = supply_dict['cost__max']
                purchasing_units = supply_dict['purchasing_units']
                q_per_pu = supply_dict['quantity_per_purchasing_unit']
            
                if Supply.objects.get(pk=supply['supply']).units.lower() != purchasing_units.lower():
                    unit_cost = unit_cost / q_per_pu
                
                total = unit_cost * Decimal(supply['quantity']) * phase.quantity
                running_total += total
            
            
                
            data.append([index + 1, 
                         self._prepare_text(supply['supply__description'], font="Garuda"),
                         "{0:,.2f}".format(Decimal(supply['quantity']) * phase.quantity)])
                         
            if self.user.has_perm('projects.view_project_costs'):
                data[-1] += [unit_cost,  "{0:,.2f}".format(total)]
                
        if len(data) == 1:
            data.append(['No Supplies for this Room'])
        else:
            if self.user.has_perm('projects.view_project_costs'):
                data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
        
        #Determine column widths based on user permission
        if self.user.has_perm('projects.view_project_costs'):
            colWidths = (20, 350, 30, 70, 90)
        else:
            colWidths = (20, 450, 30)
            
        table = Table(data, colWidths=colWidths, repeatRows=1)
        
        # Create layout and style
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT'), # Cost and total alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('LINEABOVE', (-3, -1), (-1, -1), 1, colors.CMYKColor(black=60)),
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
        
        # Special style if no supplies
        if len(data) == 1:
            pre_styles.append(('SPAN', (0, 1), (-1, 1)))
            pre_styles.append(('ALIGNMENT', (0, 1), (-1, 1), 'CENTER'))
            
        style = TableStyle(pre_styles)
        table.setStyle(style)
        
        return table
        
    def _create_phase_items(self, phase):
        special_styles = {'indent': [],
                          'bottom_padding': [],
                          'line_above': []}
                       
        data = [['#', 'Description', 'Qty']]
        
        # Determine whether to show cost headings based on user permissions
        if self.user.has_perm('projects.view_project_costs'):
            data[0] += ['Unit Cost', 'Total']
        
        # Loop though all items in the project
        for index, item in enumerate(Item.objects.filter(room__project=self.project)):
            data.append([index + 1, item.description, item.quantity])
            
            # Add parts for the current item
            data.append(['', self._prepare_text('Parts', bold=True, font='Helvetica')])
            for part in item.parts.all():
                data.append(['', part.description, part.quantity * phase.quantity])
                special_styles['indent'].append(len(data) - 1)
            
            # Add supplies for the item if use has permission
            if self.user.has_perm('projects.view_project_supplies'):
                self._create_and_append_item_supplies(data, special_styles, item)
              
        # Add Items (Loose Furniture) from the acknowledgements
        init_index = Item.objects.filter(room__project=self.project).count()
        for index, item in enumerate(AckItem.objects.filter(acknowledgement__phase=self.phase)):
            data.append([index + init_index + 1, item.description, item.quantity])
        
        #Determine column widths based on user permission
        if self.user.has_perm('projects.view_project_costs'):
            colWidths = (20, 350, 30, 70, 90)
        else:
            colWidths = (20, 450, 30)
        
        # Create the table
        table = Table(data, colWidths=colWidths, repeatRows=1)
        
        # Create the style and layout for item breakdown
        pre_styles = [('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'), # Header alignment
                      ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'), # Qty column alignment
                      ('FONTSIZE', (0, 0), (-1, 0), 12), # Header fontsize
                      
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=20)), # Header grid
                      ('LINEAFTER', (0, 0), (-1, 0), 7, colors.CMYKColor(black=0)), # Header separator
                      ('TOPPADDING', (0, 1), (-1, 1), 15),
                      ('BOTTOMPADDING', (0, 0), (-1, 0), 5), # Header bottompadding
                      ('FONT', (0, 1), (-1, -1), 'Garuda')]
                      
        if self.user.has_perm('projects.view_project_costs'):
            pre_styles.append(('ALIGNMENT', (-2, 1), (-1, -1), 'RIGHT')) # Cost and total alignment
                      
        for row in special_styles['bottom_padding']:
            pre_styles.append(('BOTTOMPADDING', (0, row), (-1, row), 20))
        for row in special_styles['line_above']:
            pre_styles.append(('LINEABOVE', (-3, row), (-1, row), 1, colors.CMYKColor(black=60)))
        for row in special_styles['indent']:
            pre_styles.append(('LEFTPADDING', (1, row), (1, row), 20))
        style = TableStyle(pre_styles)
        table.setStyle(style)
        
        return table
        
    def _create_and_append_item_supplies(self, data, special_styles, item):
        data.append(['', self._prepare_text('Supplies', bold=True, font='Helvetica')])
        running_total = 0
        for supply in item.supplies.all():
            quantity = ItemSupply.objects.get(supply=supply, item=item).quantity * self.phase.quantity
            
            if self.user.has_perm('projects.view_project_costs'):
                supply_dict = supply.products.all().values('purchasing_units', 'quantity_per_purchasing_unit').annotate(Max('cost'))[0]
                unit_cost = supply_dict['cost__max']
                purchasing_units = supply_dict['purchasing_units']
                q_per_pu = supply_dict['quantity_per_purchasing_unit']
            
                if supply.units.lower() != purchasing_units.lower():
                    unit_cost = unit_cost / q_per_pu
                    
                total = unit_cost * Decimal(quantity)
                running_total += total
            
            description = self._prepare_text(supply.description, font='Garuda')
            logger.debug(description)
            logger.debug(description.text)
            data.append(['',
                         description,
                         "{0:,.2f}".format(quantity)])
                         
            if self.user.has_perm('projects.view_project_costs'):
                data[-1] += [unit_cost,  "{0:,.2f}".format(total)]
                
            special_styles['indent'].append(len(data) - 1)
            
                         
        #Add Total material cost
        if self.user.has_perm('projects.view_project_costs'):
            data.append(['', '', '', 'Total', "{0:,.2f}".format(running_total)])
            special_styles['bottom_padding'].append(len(data) - 1)
            special_styles['line_above'].append(len(data) - 1)
        
    def _prepare_text(self, description, font_size=10, alignment=TA_LEFT, bold=False, font='Garuda'):
        
        text = description if description else u""
        if bold:
            text = "<b>" + text + "</b>"
        style = ParagraphStyle(name='Normal',
                               alignment=alignment,
                               fontName=font,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
        
    
if __name__ == "__main__":
    pdf = ProjectPDF()
    pdf.create()