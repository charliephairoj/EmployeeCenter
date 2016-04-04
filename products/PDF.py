#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from decimal import *
import math
from StringIO import StringIO
import urllib
import PIL
import io

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q, Sum, Max
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from utilities.svglib import svg2rlg

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class CatalogPDF(object):
    
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]

    def __init__(self, model=None, *args, **kwargs):

        super(CatalogPDF, self).__init__(*args, **kwargs)
        
        self.model = model
        
    def create(self, response=None):
        
        if response is None:
            response = '{0}_{1}.pdf'.format(self.model.name, self.model.model)
            self.filename = response
            
        self.canvas = canvas.Canvas(response)
        
        doc = SimpleDocTemplate(response, 
                                pagesize=A4, 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
                                
        logger.debug(doc.__dict__)
        stories = []
 
        stories.append(self._create_front_page())
        
        stories.append(PageBreak())
        
        stories.append(self._create_configuration_page())
        
        doc.build(stories)
        
    def _create_front_page(self):
        """Create the front page witht the model and name
        """
        data = []
        
        image = self.model.images.all().order_by('-primary')[0]
        logger.debug(image.__dict__)
        
        data.append([Spacer(0, 50)])
        data.append([self.model.name])
        data.append([Spacer(0, 30)])
        data.append([self._get_image(image.generate_url(), width=500)])
        
        table = Table(data, rowHeights=(50, 30, 30, 600))
        
        style_data = [('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                      #('GRID', (0, 0), (-1, -1), 1, 'red'),
                      ('FONTSIZE', (0, 1), (0, 1), 30),
                      ('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=10)),
                      ('VALIGN', (0, -1), (0, -1), 'MIDDLE') # Configuration Image alignment
                  ]
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _create_configuration_page(self):
        """Create the configuration page with specifications
        """
        
        data = []
        
        data.append([self._format_text(self.model.name, font_size=24, alignment=0)])
        data.append([self._format_text(self.model.model, font_size=14, alignment=0)])
        data.append([Spacer(0, 50), ''])
        data += [['SPECIFICATIONS'],
                 ['Frame:', self._format_text(self.model.frame,
                                              alignment=0,
                                              font_size=10)],
                 ['Suspension:', self._format_text(self.model.suspension,
                                                   alignment=0,
                                                   font_size=10)],
                 ['Cushions:', self._format_text(self.model.cushions,
                                                 alignment=0,
                                                 font_size=10)],
                 ['Upholstery:', self._format_text(self.model.upholstery,
                                                   alignment=0,
                                                   font_size=10)],
                 ['Legs:',self._format_text(self.model.legs or '',
                                            alignment=0,
                                            font_size=10)]]
                                   
        config = self.model.images.get(key__icontains=".svg")
        link = config.generate_url()
        logger.debug(link)
        urllib.urlretrieve(link, 'temp.svg')
        drawing = svg2rlg('/Users/Charlie/Sites/employee/backend/temp.svg')
        logger.debug(drawing)
        data.append([drawing, ''])
        
        
        logo_url = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/DR_logo.png"
        data.append(['Specifications are subject to change without notice', self._get_image(logo_url, height=30)])
        data.append(['', 'http://www.dellarobbiathailand.com'])
                 
        table = Table(data, colWidths=(70, 520), rowHeights=(20, 20, 50, 14, 28, 14, 28, 14, 14, 525, 30, 20))
        
        style_data = [('PADDING', (0, 0), (-1, -1), 0),
                      ('BOTTOMPADDING', (0, 0), (0, 0), 10),   
                      ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                      #('GRID', (0, 0), (-1, -1), 1, 'red'),
                      ('SPAN', (0, 0), (1, 0)),
                      ('SPAN', (0, 1), (1, 1)),
                      ('SPAN', (0, 2), (1, 2)),
                      ('SPAN', (0, 3), (1, 3)),
                      ('VALIGN', (0, 4), (-1, -9), 'TOP'),
                      ('TEXTCOLOR', (0,0), (-1, -1), colors.CMYKColor(black=10)),
                      #('FONTSIZE', (0, 0), (0, 0), 24),
                      #('FONTSIZE', (0, 1), (0, 1), 14),
                      ('FONTSIZE', (0, 4), (0, 9), 10),
                      ('ALIGNMENT', (-1, -2), (-1, -1), 'RIGHT'),
                      ('VALIGN', (-1, -2), (-1, -1), 'MIDDLE'),
                      ('VALIGN', (0, -3), (0, -3), 'TOP'),  # Configuration Image alignment
                      ('LEFTPADDING', (0, 0), (-1, -1), 30),
                      ('LEFTPADDING', (0, 9), (-1, 9), 0),
                      ('RIGHTPADDING', (0, 0), (-1, -1), 30),
                      ('RIGHTPADDING', (0, 9), (-1, 9), 0)
                  ]
                      
        style = TableStyle(style_data)
        
        table.setStyle(style)
        
        return table
        
    def _format_text(self, description, font_size=12, font="Garuda", alignment=1):
        """
        Formats the description into a paragraph
        with the paragraph style
        """
        style = ParagraphStyle(name='Normal',
                               fontName=font,
                               leading=12,
                               wordWrap=None,
                               allowWidows=0,
                               alignment=alignment,
                               allowOrphans=0,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        
        return Paragraph(description, style)
        
    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None, max_width=0, max_height=0):
        """Retrieves the image via the link and gets the
        size from the image. The correct dimensions for
        image are calculated based on the desired with or
        height"""
        
        
        
        try:
            #Read image from link
            img = utils.ImageReader(path)
            
        
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
            
        
            return Image(path, new_width, new_height)
            
        except Exception as e:
            logger.debug(path)
            logger.error(e)
                    
        
        
        
        
        
        
        
        
        
        