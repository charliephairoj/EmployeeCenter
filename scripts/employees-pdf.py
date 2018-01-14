#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, django
import logging
from decimal import *


sys.path.append('/Users/Charlie/Sites/employee/backend')
sys.path.append('/home/django_worker/backend')

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
application = get_wsgi_application()

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT

from hr.models import Employee



logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class SupplyPDF(object):
    queryset = Employee.objects.filter(status='active').order_by('image')
    
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
     
    def create(self):
        doc = SimpleDocTemplate('Employees.pdf', 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        logger.debug("Processing {0} employees".format(self.queryset.count()))
        
        stories.append(self._create_employee_section())
        
        for story in stories:
            story.hAlign = "CENTER"
            
        doc.build(stories)
        
    def _create_employee_section(self):
        """
        Creates the higher level order section
        
        This section will also contain a subsection of 
        the items for this order
        """     
        data = [["PREVIEW", 'ID', "Barcode", 
                "Card #",
                self._prepare_text(u"First Name/ชื่อแรก"),#"/ឈ្មោះដំបូង"), 
                self._prepare_text(u"Last Name/นามสกุล"),#/ឈ្មោះចុងក្រោយ"), 
                self._prepare_text(u"Nickname/ชื่อเล่น"),#/ឈ្មោះហៅក្រៅ"),
                self._prepare_text(u"Nationality/สัญชาติ"),#/សញ្ជាតិ"),
                self._prepare_text(u"Department/แผนก")]]#/នាយកដ្ឋាន")]]   
        
        for employee in self.queryset:
            
            try:
                image = self.get_image(employee.image.generate_url(), width=65)
            except AttributeError:
                image = ""
            except IOError:
                image = "Image NA"
                
            data.append([image,
                         employee.id,
                         code128.Code128("DREM-{0}".format(employee.id), 
                                         barHeight=20),
                         '',
                         employee.first_name, 
                         employee.last_name, 
                         employee.nickname,
                         employee.nationality,
                         employee.department])
       
            
        table = Table(data, colWidths=[80, 60, 90, 110, 125, 100, 100, 60, 75], repeatRows=1)
        table.setStyle(TableStyle(self.table_style))
            
        return table
    

    def _prepare_text(self, description, font_size=8):
        
        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               alignment=TA_LEFT,
                               fontName='Garuda',
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
    
    #helps change the size and maintain ratio
    def get_image(self, path, width=None, height=None, max_width=0, max_height=0):
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
    pdf = SupplyPDF()
    pdf.create()