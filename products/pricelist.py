#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
import logging
import math
from decimal import *
import re
import csv
import multiprocessing
from threading import Thread
from time import sleep

from svglib.svglib import svg2rlg
#if you want to see the box around the image
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
from reportlab.graphics import renderPDF, renderPM

from reportlab.lib.enums import TA_LEFT, TA_CENTER

from products.models import Model, Upholstery, Supply as ProductSupply
from supplies.models import Fabric
from contacts.models import Supplier
from media.models import S3Object


django.setup()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))
pdfmetrics.registerFont(TTFont('Raleway', settings.FONT_ROOT + 'raleway_thin-webfont.ttf'))

class PricelistDocTemplate(BaseDocTemplate):
    id = 0
    top_padding = 12 #150


    def __init__(self, filename, **kwargs):

        BaseDocTemplate.__init__(self, filename, **kwargs)
        self.addPageTemplates(self._create_page_template())

    def _create_page_template(self):
        frame = Frame(0, 0, 210 * mm, 297 * mm, leftPadding=36,
                      bottomPadding=12, rightPadding=36,
                      topPadding=self.top_padding)
        template = PageTemplate('Normal', [frame])
        template.beforeDrawPage = self._create_header
        return template

    def _create_header(self, canvas, doc):
        #Draw the logo in the upper left
        path = """form_logo.jpg"""

        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * 50) / img_height
        #canvas.drawImage(path, 42, 780, height=30, width=new_width)

        canvas.setFont('Times-Roman', 5)
        canvas.drawString(565, 4, "Page {0}".format(doc.page))


class PricelistPDF(object):
    models = [
        'AC-2005',
        'AC-2008',
        'AC-2015',
        'AC-2021',
        #'AC-2023',
        'AC-2027',
        'AC-2029',
        'AC-2033',
        'AC-2042',
        'AC-2043',
        'AC-2051',
        'AC-2055',
        #'AC-2080',
        'AC-2082',
        'AC-2086',
        'AC-2090',
        'AC-2091',
        #'AC-2093',
        'AC-2106',
        'AC-2108',
        'AC-2110',
        'AC-2118',
        #'AC-2123',
        'AC-2137',
        'AC-2142',
        'AC-2157',
        'AC-2159',
        'PS-905',
        'PS-605',
        'PS-1019',
        'PS-1024',
        'PS-1028',
        'PS-1029',
        'PS-1031'
    ]


    queryset = Model.objects.filter(Q(model__istartswith='dw-') | Q(model__in=models))
    #queryset = Model.objects.filter(Q(model__istartswith='ac-'))
    #queryset = queryset.filter(upholstery__id__gt=0).distinct('model').order_by('model')
    queryset = queryset.exclude(model__icontains="DA-")
    queryset = queryset.exclude(model='DW-1217').exclude(model='DW-1212')
    data = [m for m in queryset.filter(model__istartswith='dw-')]
    data += [m for m in queryset.exclude(model__istartswith='dw-').order_by('model')]

    # Testing
    #data = data[0:15]

    _display_retail_price = False
    _overhead_percent = 30
    _profit_percent = 35
    _forex_rate = 36 #Forex rate for THB per USD
    _preface = {'General Information': {'Conditions of Sale': 'conditions_of_sale.txt',
                                        'Terms': 'terms.txt',
                                        'Order Processing': 'order_processing.txt',
                                        'Acknowledging': 'acknowledging.txt',
                                        'Delivery': 'delivery.txt'},
                 'Warranty': {'Warranty': 'warranty.txt',
                              'Fabrics': 'fabrics.txt'},
                 'Product Information': {'Custom Sizes': 'custom_sizes.txt'}}
    max_row_height = 20
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
    _files_to_delete = []

    def __init__(self, export=False, *args, **kwargs):

        self.export = export
        self.fabrics = fabrics

    def create(self, filename='Pricelist.pdf'):
        filename = filename if not self.export else "Pricelist_Export.pdf"

        doc = PricelistDocTemplate(filename,
                                   pagesize=A4,
                                   leftMargin=12,
                                   rightMargin=12,
                                   topMargin=12,
                                   bottomMargin=12)
        stories = []


        stories.append(Spacer(0, 200))
        link = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"
        stories.append(self._get_image(link, width=200))
        stories.append(PageBreak())

        logger.debug("\n\nProcessing Terms and Conditions\n\n")

        for category in ['General Information', 'Warranty', 'Product Information']:

            stories.append(self._prepare_text("<u>" + category + "</u>", alignment=TA_LEFT, font_size=18, fontname="Helvetica-Bold"))
            stories.append(Spacer(0, 20))

            for key in self._preface[category]:

                text = self._extract_text('texts/' + self._preface[category][key])
                stories.append(self._prepare_text(key, alignment=TA_LEFT, font_size=16, fontname="Helvetica-Bold", left_indent=20))
                stories.append(Spacer(0, 10))
                stories.append(self._prepare_text(text, alignment=TA_LEFT, font_size=14, left_indent=40, leading=20))
                stories.append(Spacer(0, 25))

            stories.append(PageBreak())

        logger.debug("\n\nProcessing {0} Models\n\n\n\n".format(self.queryset.count()))

        models = self._prepare_data(self.queryset)

        #models_name = [model for model in sorted(models.keys(), key=lambda model: model.model) if "DW-" in model.model]
        #models_name += [model for model in sorted(models.keys(), key=lambda model: model.model) if "DW-" not in model.model]

        for model in models.keys():

            assert len(models[model]) == model.upholsteries.all().count(), "Only {0} of {1} return from prepare data for model {2}".format(len(models[model]),
                                                                                                                                       model.upholsteries.all().count(),
                                                                                                                                       model.model)
            stories.append(self._create_model_section(model, models[model]))
            stories.append(PageBreak())

        for story in stories:
            try:
                story.hAlign = "CENTER"
            except AttributeError:
                pass


        doc.build(stories)

    def _prepare_data(self, models):

        data = {}
        threads = []
        for model in models:
            data[model] = []

            t = Thread(target=self._add_upholstery_data, args=(model, data))
            threads.append(t)
            t.start()

        while len([t for t in threads if t.isAlive()]) > 0:
            sleep(1)

        else:
            for model in data.keys():
                msg = "Prepared {0} of {1} for model {2}"
                assert len(data[model]) == model.upholsteries.all().count(), msg.format(len(data[model]), 
                                                                                        model.upholsteries.all().count(),
                                                                                        model.model)
            return data

    def _add_upholstery_data(self, model, data):
        for upholstery in model.upholsteries.all().order_by('-width'):

            uphol_data = {'id': upholstery.id,
                          'configuration': upholstery.configuration.configuration,
                          'description': upholstery.description,
                          'width': upholstery.width,
                          'depth': upholstery.depth,
                          'height': upholstery.height,
                          'price': upholstery.price,
                          'export_price': upholstery.export_price}

            download_switch = True
            filename = "{0}.svg".format(upholstery.description)

            while download_switch:
                try:
                    upholstery.schematic.download(filename)
                    uphol_data['schematic'] = filename
                    self._files_to_delete.append(filename)
                    download_switch = False
                except AttributeError as e:
                    download_switch = False
                except Exception as e:
                    logger.warn(e)
                    msg = "Will try to download schemetic for {0} again in 15 seconds"
                    logger.info(msg.format(upholstery.description))
                    sleep(5)


            """
            if upholstery.supplies.count() > 0:
                uphol_data = {'id': upholstery.id,
                              'configuration': upholstery.configuration.configuration,
                              'description': upholstery.description,
                              'width': upholstery.width,
                              'depth': upholstery.depth,
                              'height': upholstery.height,
                              'price': upholstery.price,
                              'export_price': upholstery.export_price}
                prices = upholstery.get_prices()

                if "DW" in upholstery.model.model:
                    upholstery.price = prices['A3']
                    upholstery.save()
                uphol_data['prices'] = prices
            else:
                uphol_data = {'id': upholstery.id,
                              'configuration': upholstery.configuration.configuration,
                              'description': upholstery.description,
                              'width': upholstery.width,
                              'depth': upholstery.depth,
                              'height': upholstery.height,
                              'price': upholstery.price,
                              'export_price': upholstery.export_price,
                              'prices': []}
            """

            data[model].append(uphol_data)
        
        uphol_count = model.upholsteries.all().count()
        logger.debug("Model {0} has {1} upholsteries.".format(model.model, uphol_count ))
        assert len(data[model]) == model.upholsteries.all().count()


    def _create_model_section(self, model, products):
        """
        Create a table of prices for all the products in this model
        """
        # Products for this model
        #products = Upholstery.objects.filter(model=model, supplies__id__gt=0).distinct('description').order_by('description')

        # Initial array and image of product
        images = model.images.all().order_by('-primary')

        try:
            product_description = u"{0} {1}"
            product_description = product_description.format(model.name, model.model)
            data = [[self._prepare_text(product_description,
                                        fontname='Raleway',
                                        alignment=TA_LEFT,
                                        font_size=24,
                                        left_indent=12)],[self._get_image(images[0].generate_url(), height=150)]]
        except (IndexError, AttributeError) as e:
            logger.debug(e)
            product_description = u"{0} {1}"
            product_description = product_description.format(model.name, model.model)
            data = [[self._prepare_text(product_description,
                                        fontname='Raleway',
                                        alignment=TA_LEFT,
                                        font_size=24,
                                        left_indent=12)],[]]

        #data = [[self._prepare_text(model.model, font_size=24, alignment=TA_LEFT)]]

        assert len(products) == model.upholsteries.all().count(), "Only {0} of {1} products in create model section for model {2}".format(len(products),
                                                                                                                                          model.upholsteries.all().count(),
                                                                                                                                          model.model)
        # Var to keep track of number of products priced
        count = 0
        priced_count = 0

        # Get Max row height
        logger.info(u"{0}".format(model.model))
        if "PS-905" in model.model:
            self.max_row_height = 110
            logger.info("\n\n905\n")
        try:
            self.max_row_height = max([self._get_drawing(p['schematic'])[2] for p in products])     

            logger.info([self._get_drawing(p['schematic'])[2] for p in products])

            if len([p for p in products if 'schematic' in p]) > 0:

                assert self.max_row_height > 40, products

            logger.info("\n\nMax row height for {0} is {1}\n".format(model.model, self.max_row_height))


        except (KeyError, ValueError) as e:
            logger.debug("No schematics:")
            logger.debug(model.model)
            logger.debug(model.name)
            logger.debug(e)
            print "\n\n"

        # Denotes number of products per line by 
        product_tables = []
        for p in products:
            p1, w = self._create_product_price_table(p)
            product_tables.append((p1, p, w))


        assert len(product_tables) == model.upholsteries.all().count(), "Only {0} for {1} product tables for model {2}".format(len(product_tables),
                                                                                                                             model.upholsteries.all().count(),
                                                                                                                             model.model)


        col_widths = 0
        page_width = 550
        section_products = []
        for index, x in enumerate(product_tables):
            # If the width and is less than preset width limit
            # and it is not the last product
            if col_widths + x[2] <= page_width and (index + 1) != len(products):
                section_products.append(x)
                col_widths += x[2]
                priced_count += 1
                count += 1
            # If the width and is greater than preset width limit
            # and it is not the last product
            elif col_widths + x[2] >= page_width and (index + 1) != len(products): 
                # Create full section first 
                section = self._create_section(section_products)
                data.append([section])

                # Then start next row
                col_widths = x[2]
                section_products = [x]
                priced_count += 1
                count = 1

            # If the width and is greater than preset width limit
            # and it is the last product
            elif col_widths + x[2] >= page_width and (index + 1) == len(products): 
                # Create full section first 
                section = self._create_section(section_products)
                data.append([section])
                

                # Then start next row
                col_widths = x[2]
                section_products = [x]
                priced_count += 1
                count = 1

                # Create final row
                section = self._create_section(section_products)
                data.append([section])

            elif col_widths + x[2] <= page_width and (index + 1) == len(products):
                section_products.append(x)
                col_widths += x[2]
                priced_count += 1
                count += 1

                # Create final row
                section = self._create_section(section_products)
                data.append([section])

            else:
                logger.debug("price count: {0}".format(priced_count))
                logger.debug("col widths: {0}".format(col_widths))
                logger.debug("product width: {0}".format(x[2]))
                logger.debug(x)
                raise ValueError("Missing a test here")
                        

        # Denotes number of products per line
        # by pre set number
        """
        for index in xrange(0, int(math.ceil(len(products) / float(4)))):

            # Create indexes used to pull products set from array
            i1 = index * 4 if index * 4 < len(products) else products.count()
            i2 = ((index + 1) * 4) if ((index + 1) * 4) < len(products) else len(products)
            section_products = products[i1:i2]
            # Count number of products priced
            count += len(section_products)

            section = self._create_section(section_products, index)
            data.append([section])
        """
        # Check that all products for this model have been priced
        assert priced_count == len(products), "Only {0} of {1} price".format(priced_count, len(products))

        assert priced_count == model.upholsteries.all().count(), "Only added {0} of {1} for model {2}".format(priced_count, 
                                                                                                              model.upholsteries.all().count(),
                                                                                                              model.model)
        assert len(data) != 0 

        table_style = [('ALIGNMENT', (0,0), (0, 0), 'CENTER'),
                       ('ALIGNMENT', (0, 1), (0, -1), 'LEFT'),
                       ('PADDING', (0, 1), (-1, -1), 0),
                       ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                       ('LEFTPADDING', (0, 1), (0, -1), 15)]

        table = Table(data, colWidths=(550), repeatRows=2)
        table.setStyle(TableStyle(table_style))

        # Reset max row height
        self.max_row_height = 20

        return table

    def _create_section(self, products, row_height=20):

        header = []#[self._prepare_text('Grade', font_size=12)]
        col_widths = []
        titles = Table([[i] for i in ['', 'A1']], colWidths=50) #, 'A2', 'A3', 'A4', 'A5', 'A6']], colWidths=50)
        titles.setStyle(TableStyle([('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        if self.export:
            data = [Table([[], ["Price"], ["Export Price"]])]#[titles]
        else:
            data = []#Table([[], ["Price"]])]#[titles]

        for product_table, product, widths in products:

            header.append(self._prepare_text(product['configuration'], font_size=12))

            #t, w = self._create_product_price_table(product)
            data.append(product_table)
            col_widths.append(widths)

        row_heights = [40, (20 * 4)]
        self.max_row_height
        if self.max_row_height > 20:
            row_heights[1] = row_heights[1] + self.max_row_height
        
        table = Table([header, data], colWidths=col_widths, rowHeights=row_heights)
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                                   ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                   ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

        return table

    def _create_product_price_table(self, product):
        """
        Calculate price list for each product
        """
        col_width = 150
        row_height = 20 
        data = []

        try:
            drawing, drawing_width, drawing_height = self._get_drawing(product['schematic'],
                                                       filename="{0}.png".format(product['description']),
                                                       max_height=150)
            data.append([drawing])
            col_width = drawing_width if drawing_width >= 120 else 120
            assert drawing_height > row_height, "Height of {0} shoul be greather a {1}".format(drawing_height, row_height)
            row_height = drawing_height
        except KeyError as e:
            logger.debug(e)
            
        data.append(["Width:  {0}".format(product['width'])])
        data.append(["Depth:  {0}".format(product['depth'])])
        data.append(["Height: {0}".format(product['height'])])


        #data  = []
        #prices = product['prices']

        if "dw-" in product['configuration'].lower():
            price = product['price']
            data.append(["Price: {0:,.2f}".format(price)])
            """

            for grade in sorted(prices.keys()):
                price_modifier = Decimal('1') if self._display_retail_price else Decimal('0.5')
                data.append(["{0:,.2f}".format(math.ceil((prices[grade] * price_modifier) / 10) * 10)])
            """
        else:

            price = "Price: {0:,.2f}".format(product['price'])
            #price = math.ceil(price / Decimal('35'))
            data.append([price])
            #new_price = "{0:,.2f}".format(Decimal(str(price)) * Decimal('0.6'))
            #data.append([new_price])

            """
            if self.export:
                price = product['export_price']
                msrp = "{0:,.2f}".format(math.ceil(Decimal(str(price)) / Decimal('0.6')))
                data.append([msrp])
                new_price = "{0:,.2f}".format(price)
                data.append([new_price])
            else:
                price = product['price']
                price = math.ceil(price / Decimal('35'))
                data.append([price])
                new_price = "{0:,.2f}".format(Decimal(str(price)) * Decimal('0.6'))
                data.append([new_price])
             """

        row_heights = (20, 20, 20, 20)
        table_style = [('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                ]

        

        if len(data) > 4 :
            row_heights = (self.max_row_height, 20, 20, 20, 20)

        
            table_style.append(('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'))
            table_style.append(('VALIGN', (0, 1), (-1, 1), 'TOP'))
            table_style.append(('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)))
        elif re.compile('(.+)?905(.+)?').search(product['description']):
            row_heights = (self.max_row_height, 20, 20, 20, 20)

        
            table_style.append(('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'))
            table_style.append(('VALIGN', (0, 1), (-1, 1), 'TOP'))
            table_style.append(('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)))
            if len(data) == 4:
                data = [[]] + data

        logger.info("{1} {0}".format(row_heights, product['description']))

        table = Table(data, colWidths=col_width, rowHeights=row_heights)
        table.setStyle(TableStyle(table_style))

        return table, col_width

    def _prepare_text(self, description, font_size=12, alignment=TA_CENTER, left_indent=0, fontname='Garuda', leading=12):

        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               alignment=alignment,
                               fontName=fontname,
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60),
                               leftIndent=left_indent,
                               leading=leading)
        return Paragraph(text, style)

    def _extract_text(self, filename):

        file = open(filename)
        txt = file.read()

        return txt

    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None, max_width=0, max_height=0):
        """Retrieves the image via the link and gets the
        size from the image. The correct dimensions for
        image are calculated based on the desired with or
        height"""

        try:
            #Read image from link
            img = utils.ImageReader(path)
        except Exception as e:
            logger.debug(e)
            return ''

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

    def _get_drawing(self, path, filename=None, width=None, height=None, max_width=None, max_height=None):
        try:
            drawing = svg2rlg(path)
            sx=sy=1
            drawing.width,drawing.height = drawing.minWidth()*sx, drawing.height*sy

            if max_height: 
                sy= max_height/drawing.height if  drawing.height > max_height else 1
                sx = sy
            elif max_width:
                sx= max_width/drawing.width if  drawing.width > max_width else 1
                sy = sx
        except (AttributeError) as e:
            logger.debug(e)
            logger.debug(path)
            logger.debug(svg2rlg(path))
        
        drawing.scale(sx,sy)
        
    
        return drawing, drawing.width, drawing.height
        #renderPM.drawToFile(drawing, filename)
        #return self._get_image(filename, width=width)


class FabricPDF(object):

    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]

    def __init__(self, fabrics=None, *args, **kwargs):

        if fabrics:
            self.fabrics = fabrics
        else:
            fabrics = Fabric.objects.filter(status='current')

            self.fabrics = {}

            for fabric in fabrics:
                fabric.supplier = fabric.suppliers.all()[0]

                try:
                    self.fabrics[fabric.pattern.lower()].append(fabric)
                except (AttributeError, KeyError):
                    self.fabrics[fabric.pattern.lower()] = [fabric]

    def create(self, filename="Fabrics.pdf"):
        doc = SimpleDocTemplate(filename,
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
            fabric.status = 'current'
            fabric.save()

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
        data = [[self._prepare_text('Pattern'), self._prepare_text('Color')]]

        keys = fabrics.keys()
        keys.sort()

        for pattern in keys:
            supplier = fabrics[pattern][0].supplier
            data.append([self._prepare_text(pattern.title(), alignment=TA_LEFT),
                         self._create_color_section(fabrics[pattern])])




        table = Table(data, colWidths=(200, 300), repeatRows=1)
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                                   ('ALIGNMENT', (0, 1), (0, -1), 'LEFT')]))

        return table

    def _create_color_section(self, fabrics):

        data = []

        for fabric in fabrics:

            try:
                data.append([self._get_image(fabric.image.generate_url(), width=100) if fabric.image else '',
                             fabric.color.title(),
                             self._calculate_grade(fabric)])
            except ValueError as e:
                logger.warn(e)
                raise ValueError("{0} : {1}".format(fabric.description, fabric.supplier.name))

        table = Table(data, colWidths=(125, 125, 50))
        table.setStyle(TableStyle([('ALIGNMENT', (-1, 0), (-1, -1), 'CENTER'),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('ALIGNMENT', (0, 0), (0, -1), 'LEFT')]))

        return table

    def _calculate_grade(self, fabric):
        cost = fabric.cost

        if 'Dellarobbia' in fabric.supplier.name:

            if cost > 0:
                cost += Decimal('10')

                cost = math.ceil(cost)
        elif 'crevin' in fabric.supplier.name.lower():

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
        elif cost <= 45:
            grade = 'A7'
        elif cost <= 50:
            grade = 'A8'
        else:
            raise ValueError("cost is {0} for {1}".format(cost, fabric.description))


        fabric.grade = grade
        fabric.save()

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
        except Exception as e:
            logger.debug(e)
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

    try:
        directory = sys.argv[1]
    except IndexError:
        directory = ''

    try:
        export = sys.argv[2].replace('--', "")
        export = True
        print export
    except IndexError as e:
        export = False
        logger.warn(e)

    fabrics = {}
    data = {}
    f_list = []

    if not os.path.exists(directory):
        os.makedirs(directory)

    def create_pricelist(filename):
        pdf = PricelistPDF()
        pdf.create(filename)
        regexp = re.compile('(.+)?\.svg$')

        # Delete svg files saved from S3
        for f in pdf._files_to_delete:
            if regexp.search(f):
                os.remove(f)
            else: 
                logger.debug("Did not remove {0}".format(f))
                logger.debug("Result of regexp: {0}".format(regexp.search(f)))
                logger.debug(regexp.pattern)

    def create_fabriclist(filename, fabrics):
        f_pdf = FabricPDF(fabrics=None)
        f_pdf.create(filename)

    p1 = multiprocessing.Process(target=create_pricelist, args=(directory + '/Pricelist.pdf', ))
    p1.start()
    #p2 = multiprocessing.Process(target=create_fabriclist, args=(directory + '/Fabrics.pdf', fabrics ))
    #p2.start()
