#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
import math
from decimal import *
import re
import csv

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

from products.models import Model, Product, Upholstery, Supply as ProductSupply
from supplies.models import Fabric, Product as SP
from contacts.models import Supplier


django.setup()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class FabricPDF(object):

    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
                 
    def __init__(self, fabrics, *args, **kwargs):
        
        self.fabrics = fabrics
     
    def create(self):
        doc = SimpleDocTemplate('Fabrics.pdf', 
                                pagesize=A4, 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        stories.append(self._create_section())
        stories.append(PageBreak())
        
        fabrics = {}
        supplier = Supplier.objects.get(name__istartswith='crevin')
        for fabric in Fabric.objects.filter(suppliers__name__istartswith='crevin'):
            fabric.supplier = supplier
            try:
                fabrics[fabric.pattern.lower()].append(fabric)
            except KeyError:
                fabrics[fabric.pattern.lower()] = [fabric]
        
        stories.append(self._create_section(fabrics=fabrics))
        for story in stories:
            story.hAlign = "CENTER"
            
        doc.build(stories)
    
    def _create_section(self, fabrics=None):
        
        fabrics = fabrics or self.fabrics
        data = [['Supplier', 'Pattern', Table([['', 'Fabric', 'Cost', 'Grade']], colWidths=(120, 100, 50, 50))]]
        
        keys = fabrics.keys()
        keys.sort()
        
        for pattern in keys:
            supplier = fabrics[pattern][0].supplier
            data.append([self._prepare_text(supplier.name.title(), alignment=TA_LEFT), 
                         self._prepare_text(pattern.title()), 
                         self._create_color_section(fabrics[pattern])])
            
        table = Table(data, colWidths=(150, 100, 320), repeatRows=1)
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                                   ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER')]))
        
        return table
            
    def _create_color_section(self, fabrics):
        
        data = []
        
        for fabric in fabrics:
            try:
                data.append([self._get_image(fabric.image.generate_url(), width=100) if fabric.image else '',
                             fabric.color, 
                             "{0:.2f}".format(fabric.cost) if fabric.cost else 'NA', 
                             self._calculate_grade(fabric)])
            except ValueError as e:
                logger.error(e)
                raise ValueError("{0} : {1}".format(fabric.description, fabric.supplier.name))
            
        table = Table(data, colWidths=(120, 100, 50, 50))
        table.setStyle(TableStyle([('ALIGNMENT', (0, 0), (0, -1), 'CENTER')]))
        
        return table
        
    def _calculate_grade(self, fabric):
        cost = fabric.cost

        if 'Dellarobbia' in fabric.supplier.name:

            if cost > 0:
                cost += Decimal('10')
            
                cost = math.ceil(cost)
        else:
            
            if cost > 0:
                cost += Decimal('5')
                
                cost = math.ceil(cost)
        
        if cost == 0 or cost == 'NA':
            grade = 'NA'
        elif 0 < cost <= 15 :
            grade = 'A1'
        elif cost <= 20:
            grade = 'A2'
        elif cost <= 25:
            grade = 'A3'
        elif cost <= 30: 
            grade = 'A4'
        elif cost <= 35:
            grade = 'A5'
        elif cost <= 40:
            grade = 'A6'
        else:
            raise ValueError("cost is {0} for {1}".format(cost, fabric.description))
            
        return grade
        
    def _prepare_text(self, description, font_size=9, alignment=TA_CENTER):
        
        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               alignment=alignment,
                               fontName='Garuda',
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
    
    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None, max_width=0, max_height=0):
        """Retrieves the image via the link and gets the
        size from the image. The correct dimensions for
        image are calculated based on the desired with or
        height"""
        try:
            #Read image from link
            img = utils.ImageReader(path)
        except:
            return None
        #Get Size
        imgWidth, imgHeight = img.getSize()
        #Detect if there height or width provided
        if width and height == None:
            ratio = float(imgHeight) / float(imgWidth)
            new_height = ratio * width
            new_width = width
        elif height and width == None:
            ratio = float(imgWidth) / float(imgHeight)
            new_height = height
            new_width = ratio * height
            if max_width != 0 and new_width > max_width:
                new_width = max_width
                new_height = (float(imgHeight) / float(imgWidth)) * max_width

        return Image(path, width=new_width, height=new_height)
        
    
if __name__ == "__main__":
    
    fabrics = {}
    data = {}
    f_list = []
    
    with open('steve_fabric.csv') as file:
        rows = csv.reader(file)
        
        for row in rows:
            try:
                data[row[0].lower().strip()].append(row[1].lower().strip())
            except KeyError:
                data[row[0].lower().strip()] = [row[1].lower().strip()]
                    
    for pattern in data:
        for color in data[pattern]:
            try:
                fabric = Fabric.objects.get(pattern__istartswith=pattern, color__istartswith=color)
                try:
                    fabric.supplier = fabric.suppliers.all()[0]
                except IndexError:
                    logger.warn(fabric.description)
                    supplier = Supplier.objects.filter(supplies__description__istartswith=pattern).distinct()[0]
                    SP.objects.create(supply=fabric, supplier=supplier)
                    fabric.supplier = supplier
                    
            except Fabric.DoesNotExist:
                logger.error("{0} : {1}".format(pattern, color))
                try:
                    supplier = Supplier.objects.get(supplies__description__istartswith=pattern)
                except Supplier.MultipleObjectsReturned:
                    supplier = Supplier.objects.filter(supplies__description__istartswith=pattern).distinct()[0]
                except Supplier.DoesNotExist:
                    supplier = Supplier.objects.get(name__istartswith='dellarobbia')
                    
                    
                fabric = Fabric.objects.create(pattern=pattern.title(), color=color.title())
                SP.objects.create(supply=fabric, supplier=supplier)
                fabric.supplier = supplier
                
            if fabric.description is None:
                fabric.description = "{0} Col: {1}".format(fabric.pattern.title(), fabric.color.title())
                fabric.save()
                
            if not fabric.supplier:
                raise ValueError()
                
            if fabric not in f_list:
                f_list.append(fabric)
                
            else:
                print '\n'
                logger.warn(data[pattern])
                logger.warn(Fabric.objects.filter(pattern=fabric.pattern, color=fabric.color).count())
                logger.warn(fabric.description)
                logger.warn(f_list[f_list.index(fabric)].description)
                logger.warn("{0} : {1}  || {2}, {3}, {4}".format(pattern, color, fabric.description, fabric.pattern, fabric.color))
                print '\n'
            try:
                fabrics[fabric.pattern.lower()].append(fabric)
            except KeyError:
                fabrics[fabric.pattern.lower()] = [fabric]
    
    della = []
    for p in fabrics:
        for f in fabrics[p]:
            if 'Della' in f.supplier.name:
                della.append(f)
    with open('dellarobbia_fabrics.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(['Pattern', 'Color', 'Price'])
        for f in della:
            writer.writerow([f.pattern, f.color, f.cost])
            
    pdf = FabricPDF(fabrics=fabrics)
    pdf.create()
        
    
    
    
    