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
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.barcode import code128


logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


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
                      leftPadding=0 * mm,
                      bottomPadding=4.5 * mm,
                      rightPadding=0 * mm,
                      topPadding=4.5 * mm)
        template = PageTemplate('Normal', [frame])
        return template


class SingleStickerDocTemplate(BaseDocTemplate):

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
                      leftPadding=1 * mm,
                      bottomPadding=0.5 * mm,
                      rightPadding=1 * mm,
                      topPadding=0.5 * mm)
        template = PageTemplate('Normal', [frame])
        return template


class Sticker(object):

    sticker_width = 62 * mm
    sticker_height = 29 * mm
    barcode_height = (sticker_height / 2) - 1 * mm
    barcode_width = 0.4 * mm

    def __init__(self, code=None, description=None, *args, **kwargs):
        """
        Constructor
        """
        super(Sticker, self).__init__()

        #Set attribute
        self.code = code
        self.description = description

    def create(self, response=None):
        """
        Main method to create a sticker page
        """

        if response is None:
            response = '{0}.pdf'.format(self.code)

        doc = SingleStickerDocTemplate(response, (self.sticker_width,
                                                  self.sticker_height))
        stories = [self._create_sticker()]
        doc.build(stories)

        return "{0}.pdf".format(self.code)

    def _create_sticker(self):
        """
        Creates a single sticker page.
        """
        barcode = code128.Code128(self.code, barHeight=self.barcode_height, barWidth=self.barcode_width)
        data = [[barcode], [self._format_description(self.description)]]
        table = Table(data, colWidths=self.sticker_width, rowHeights=(self.sticker_height / 2) - 1 * mm)
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 12),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER')])
        table.setStyle(style)

        return table

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


class FabricSticker(object):

    sticker_width = 62 * mm
    sticker_height = 62 * mm
    content_width = 58 * mm
    content_height = 58 * mm

    def __init__(self, fabric, *args, **kwargs):
        """
        Constructor
        """
        super(FabricSticker, self).__init__()

        self.fabric = fabric

    def create(self, response=None):
        """
        Main method to create a sticker page
        """

        filename = self.fabric.description.replace(' ', '_')
        if response is None:
            response = '{0}.pdf'.format(filename)

        doc = SingleStickerDocTemplate(response, (self.sticker_width,
                                                  self.sticker_height))
        stories = [self._create_sticker()]
        stories[0].hAlign = 'CENTER'
        doc.build(stories)

        return "{0}.pdf".format(filename)

    def _create_sticker(self):
        """
        Creates a single sticker page.
        """
        data = []

        # Get Logo
        logo = self.get_image("https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg", width=self.content_width - 6 * mm)
        data.append([logo, ''])
        data.append(['Pattern', self.fabric.pattern])
        data.append(['Color', self.fabric.color])
        data.append(['Grade', self.fabric.grade])

        content = self._format_content(self.fabric.content)
        for index, content in enumerate(content.split(' ')):
            if index == 0:
                data.append(['Content', "{0}: {1}".format(*content.split(':'))])
            else:
                data.append(['', "{0}: {1}".format(*content.split(':'))])

        # Create fabric table
        col_widths = ((self.content_width * 0.3) - 1 * mm,
                      (self.content_width * 0.7) - 1 * mm)
        table = Table(data, colWidths=col_widths)

        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 12),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (0, 0), 4 * mm),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (0, 0), 3.5 * mm),
                            ('BOTTOMPADDING', (1, 0), (-1, 0), 3 * mm),
                            ('MARGIN', (0, 0), (-1, -1), 0),
                            ('SPAN', (0, 0), (1, 0)),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(cyan=60)),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                            ('ALIGN', (0, 1), (-1, -1), 'LEFT')])
        table.setStyle(style)

        return table
    def _format_content(self, content):
        formatted_content = ""
        contents = content.split(' ')
        colon_flag = len(content.split(':'))
        space_flag = len(contents)
        logger.debug("{0} : {1}".format(colon_flag, space_flag))
        if colon_flag == 1 and space_flag > 0 and space_flag % 2 == 0:
            for index, item in enumerate(content.split(' ')):
                if index % 2 == 0:
                    formatted_content += "{1}:{0} ".format(contents[index],
                                                           contents[index + 1])
        else:
            formatted_content = content

        return formatted_content.strip()

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


class FabricSticker2(object):

    sticker_width = 62 * mm
    sticker_height = 29 * mm
    barcode_height = (sticker_height / 2) - 1 * mm
    barcode_width = 0.4 * mm

    def __init__(self, fabric, *args, **kwargs):
        """
        Constructor
        """
        super(FabricSticker2, self).__init__()

        #Set attribute
        self.fabric = fabric

    def create(self, response=None):
        """
        Main method to create a sticker page
        """

        if response is None:
            response = '{0}.pdf'.format(self.fabric.description)

        doc = SingleStickerDocTemplate(response, (self.sticker_width,
                                                  self.sticker_height))
        stories = [self._create_sticker()]
        doc.build(stories)

        return "{0}.pdf".format(self.fabric.description)

    def _create_sticker(self):
        """
        Creates a single sticker page.
        """

        data = [['Pattern :', self._format_description(self.fabric.pattern)],
                ['Color :', self._format_description(self.fabric.color)],
                ['Grade :', self._format_description(self.fabric.grade)]]
        table = Table(data, colWidths=(self.sticker_width * 0.34,
                                       self.sticker_width * 0.66),
                            rowHeights=((self.sticker_height - 2 * mm) / 3))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 14),
                            ('LEFTPADDING', (0, 0), (-1, -1), 2),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            #('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(cyan=60)),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONT', (0, 0), (-1, -1), 'Tahoma')])
        table.setStyle(style)

        return table

    def _format_description(self, description):
        """
        Formats the description into a paragraph
        with the paragraph style
        """
        style = ParagraphStyle(name='Normal',
                               fontName='Tahoma',
                               leading=12,
                               wordWrap='CJK',
                               allowWidows=1,
                               alignment=0,
                               allowOrphans=1,
                               fontSize=14,
                               textColor=colors.CMYKColor(black=60))

        return Paragraph(description, style)


class StickerPage(object):

    sticker_width = 70 * mm
    sticker_height = 36 * mm
    barcode_height = 16 * mm
    barcode_width = 0.35 * mm
    vertical_spacing = 0 * mm
    horizontal_spacing = 0 * mm

    def __init__(self, code=None, description=None, codes=None, copy=None, *args, **kwargs):
        """
        Constructor
        """
        super(StickerPage, self).__init__()

        #Set attribute
        self.copy = copy
        self.code = code
        self.description = description
        self.codes = codes

    def create(self, response=None):
        """
        Main method to create a sticker page
        """
        logger.debug(self.code)
        logger.debug(response)
        if response is None:
            response = '{0}.pdf'.format(self.code)

        doc = StickerDocTemplate(response)
        stories = [self._create_sticker_page()]
        doc.build(stories)

        return "{0}.pdf".format(self.code)

    def _create_sticker_page(self):
        """
        Creates a single sticker page.
        """
        codes = self._get_codes()
        code_index = 0

        data = []
        for i in range(15):
            row = []
            for h in range(5):
                if h % 2 == 0 and i % 2 == 0:
                    # Add code and description to sticker. If out of code add empty space
                    try:
                        row.append(self._create_sticker_cell(codes[code_index]))
                    except IndexError:
                        row.append('')

                    code_index += 1
                else:
                    row.append('')
            data.append(row)

        table = Table(data,
                      colWidths=tuple([self.sticker_width if i % 2 == 0 else self.horizontal_spacing for i in range(5) ]),
                      rowHeights=tuple([self.sticker_height if i % 2 == 0 else self.vertical_spacing for i in range(15)]))
        style = TableStyle([('FONTSIZE', (0, 0), (-1, -1), 12),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
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
        barcode = code128.Code128(code, barHeight=self.barcode_height, barWidth=self.barcode_width)
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
                     self.code for i in range(self.copy or 30)]
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
