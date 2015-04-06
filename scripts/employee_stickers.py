#!/usr/local/bin/python
# -*- coding: utf-8 -*-
"""
PDF pages for stickers
"""
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.conf import settings
import logging
from decimal import Decimal
from pytz import timezone
import math

from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.barcode import code128

from hr.models import Employee

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


django.setup()


class StickerDocTemplate(BaseDocTemplate):
    def __init__(self, filename, page_size=A4, **kwargs):
        """
        Constructor
        
        Set the page size in the kwargs then
        Call the parent constructor of the base doc template
        and then apply addition settings
        """
        self.width, self.height = page_size
        kwargs['pagesize'] = page_size
        kwargs['leftMargin'] = 0 * mm
        kwargs['rightMargin'] = 0 * mm
        kwargs['topMargin'] = 0 * mm
        kwargs['bottomMargin'] = 0 * mm
        
        BaseDocTemplate.__init__(self, filename, **kwargs)
        
        self.addPageTemplates(self._create_page_template())

    def _create_page_template(self):
        frame = Frame(mm, 
                      0, 
                      self.width, 
                      self.height, 
                      leftPadding=6 * mm,
                      bottomPadding=1 * mm, 
                      rightPadding=6 * mm,
                      topPadding=13.25 * mm)
        template = PageTemplate('Normal', [frame])
        return template
        
class EmployeeStickerPage(object):
    queryset = Employee.objects.raw("""
    SELECT * FROM hr_employee 
    WHERE last_modified > date('2015-3-24')
    ORDER BY image_id is null, nationality, first_name, last_name
    """)
    sticker_width = 55 * mm
    sticker_height = 29.5 * mm
    barcode_height = 7.5 * mm
    vertical_spacing = 0.5 * mm
    horizontal_spacing = 5 * mm
        
    def create(self, filename):
        """
        Main method to create a sticker page
        """
        doc = StickerDocTemplate('{0}.pdf'.format(filename))
        stories = []
        index = 1
        logger.debug('test')
        for i in xrange(0, int(math.ceil(Employee.objects.all().count()/27))):
            employees = self.queryset[i * 27 : (i + 1) * 27]
            
            print i
            
            stories.append(self._create_sticker_page(employees))
            stories.append(PageBreak())
            
            print '\n\n'
            
        doc.build(stories)
        
        return "{0}.pdf".format(filename)
        
    def _create_sticker_page(self, employees):
        """
        Creates a single sticker page.
        """
        code_index = 0
        
        data = []
        for i in range(17):
            row = []
            for h in range(5):
                if h % 2 == 0 and i % 2 == 0:
                    try:
                        row.append(self._create_sticker_cell(employees[code_index]))
                    except IndexError:
                        row.append('')
                        
                    code_index += 1
                else:
                    row.append('')
            data.append(row)

        table = Table(data,
                      colWidths=tuple([self.sticker_width if i % 2 == 0 else self.horizontal_spacing for i in range(5) ]),
                      rowHeights=tuple([self.sticker_height if i % 2 == 0 else self.vertical_spacing for i in range(17)]))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 12),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(cyan=60)),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER')])
        table.setStyle(style)
        
        return table
    
    def _create_sticker_cell(self, employee):
        """
        Creates the contents for a single cell
        """
        code = "DREM-{0}".format(employee.id)
        logger.debug(employee.id)
        if employee.first_name and employee.last_name:
            description = u"{0} {1}".format(employee.first_name, employee.last_name)
        elif employee.first_name and not employee.last_name:
            description = u"{0}".format(employee.first_name)
        elif not employee.first_name and not employee.last_name:
            description = u"{0}".format(employee.name)

        barcode = code128.Code128(code, barHeight=self.barcode_height, barWidth=0.3 * mm)
                
        try:
            data = [[self._get_image(employee.image.generate_url(time=1800000), height=20 * mm), self._format_description(description)],
                    [barcode]]
        except AttributeError:
            data = [["", self._format_description(description)],
                    [barcode]]
        
        table = Table(data, colWidths=(25 * mm, 30 * mm), rowHeights=(self.sticker_height - self.barcode_height, self.barcode_height))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 3 * mm),
                            ('SPAN', (0, 1), (1, 1)), 
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, 0), 1 * mm),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(magenta=60)),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')])
        table.setStyle(style)
        return table
        
    def _get_codes(self):
        """
        Retrieves the codes based on if a single
        value is provided of if an array of values 
        is provide. 
        
        If a single value is provided, it also checks if a description is provide
        """
        #Sets the codes use
        if self.codes and isinstance(self.codes, list):
            codes = self.codes
        elif self.code and isinstance(self.code, str):
            codes = [(self.code, self.description) if self.description else
                     self.code for i in range(30)]
        else:
            raise ValueError('Expecting some codes here')
        
        return codes
    
    def _format_description(self, description):
        """
        Formats the description into a paragraph
        with the paragraph style
        """
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               leading=12,
                               wordWrap=None,
                               allowWidows=0,
                               alignment=1,
                               allowOrphans=0,
                               fontSize=10,
                               textColor=colors.CMYKColor(black=60))
        
        return Paragraph(description, style)
        
    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None):
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
        if width != None and height == None:
            ratio = float(imgHeight) / float(imgWidth)
            newHeight = ratio * width
            newWidth = width
        elif height != None and width == None:
            ratio = float(imgWidth) / float(imgHeight)
            newHeight = height
            newWidth = ratio * height

        return Image(path, width=newWidth, height=newHeight)
        
if __name__ == "__main__":
    
        
        sp = EmployeeStickerPage()
        sp.create("EmployeeStickers")
            
            
    
    
    
    
    
    
    
    
    