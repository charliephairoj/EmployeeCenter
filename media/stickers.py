#!/usr/local/bin/python
# -*- coding: utf-8 -*-
"""
PDF pages for stickers
"""
import logging
from decimal import Decimal
from pytz import timezone

from django.conf import settings
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


logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class StickerDocTemplate(BaseDocTemplate):
    def __init__(self, filename, page_size=(168 * mm, 221.5 * mm), **kwargs):
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
                      topPadding=1.5 * mm)
        template = PageTemplate('Normal', [frame])
        return template
        
class StickerPage(object):
    
    sticker_width = 50 * mm
    sticker_height = 19 * mm
    barcode_height = 10 * mm
    vertical_spacing = 3 * mm
    horizontal_spacing = 2.5 * mm
    
    def __init__(self, code=None, description=None, codes=None, *args, **kwargs):
        """
        Constructor
        """
        super(StickerPage, self).__init__()
        
        #Set attribute
        self.code = code
        self.description = description
        self.codes = codes
        
    def create(self, filename):
        """
        Main method to create a sticker page
        """
        doc = StickerDocTemplate('{0}.pdf'.format(filename))
        stories = [self._create_sticker_page()]
        doc.build(stories)
        
        return "{0}.pdf".format(filename)
        
    def _create_sticker_page(self):
        """
        Creates a single sticker page.
        """
        codes = self._get_codes()
        code_index = 0
        
        data = []
        for i in range(19):
            row = []
            for h in range(5):
                if h % 2 == 0 and i % 2 == 0:
                    row.append(self._create_sticker_cell(codes[code_index]))
                    code_index += 1
                else:
                    row.append('')
            data.append(row)
            
        table = Table(data,
                      colWidths=tuple([self.sticker_width if i % 2 == 0 else self.horizontal_spacing for i in range(5) ]),
                      rowHeights=tuple([self.sticker_height if i % 2 == 0 else self.vertical_spacing for i in range(19)]))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 12),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER')])
        table.setStyle(style)
        
        return table
    
    def _create_sticker_cell(self, code):
        """
        Creates the contents for a single cell
        """
        if isinstance(code, tuple):
            code, description = code
        else:
            code, description = code, code
        barcode = code128.Code128(code, barHeight=self.barcode_height)
        data = [[barcode],
                [self._format_description(description)]]
        
        table = Table(data, colWidths=(50 * mm), rowHeights=(self.barcode_height - 1, 8 * mm))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 3 * mm),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, 0), 1 * mm),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, -1), (-1, -1), 'MIDDLE')])
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
                               wordWrap='CJK',
                               allowWidows=1,
                               alignment=1,
                               allowOrphans=1,
                               fontSize=10,
                               textColor=colors.CMYKColor(black=60))
        
        return Paragraph(description, style)
        