#!/usr/local/bin/python
# -*- coding: utf-8 -*-
"""Collection of the classes that create pdf files
for an Acnowledgement. The Receipt creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing
production
"""

from decimal import Decimal
import logging
from pytz import timezone

from django.conf import settings
from django.db import models
from administrator.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT, TA_CENTER


logger = logging.getLogger(__name__)


pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))

logo_height = 70

class AckDocTemplate(BaseDocTemplate):
    id = 0
    top_padding = 150

    def __init__(self, filename, **kwargs):
        if "id" in kwargs:
            self.id = kwargs["id"]
            
        try:
            self.company = kwargs['company']
        except KeyError:
            pass
            
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self.addPageTemplates(self._create_page_template())

    def _create_page_template(self):
        frame = Frame(0, 0, 210 * mm, 297 * mm, leftPadding=36,
                      bottomPadding=30, rightPadding=36,
                      topPadding=self.top_padding)
        template = PageTemplate('Normal', [frame])
        template.beforeDrawPage = self._create_header
        return template

    def _create_header(self, canvas, doc):
        #Draw the logo in the upper left
        if self.company.lower() == 'dellarobbia thailand':
            path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"
        else:
            path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"
    
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * logo_height) / img_height
        canvas.drawImage(path, 42, 760, height=logo_height, width=new_width)

        #Add Company Information in under the logo
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 1)

        #Add Company Information in under the logo if dellarobbia
        if self.company.lower() == 'dellarobbia thailand':
            canvas.drawString(42, 760,
                            "78/448 Moo.6 Lam Lukka Rd. Bueng Kham Phroi, Lam Lukka")
            canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
            canvas.drawString(42, 740, "+66 2 508 8681")
        else:
            canvas.drawString(42, 760,
                            "78/448 Moo.6 Lam Lukka Rd. Bueng Kham Phroi, Lam Lukka")
            canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
            canvas.drawString(42, 740, "+66 2 508 8681")
            canvas.drawString(42, 730, "Tax ID: 0105560020175")
        
        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'RECEIPT')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Receipt#: {0}'.format(self.id))
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = "A-{0}".format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)
        


class ReceiptPDF(object):
    """Class to create Receipt PDF"""
    #attributes
    document_type = "Receipt"

    def __init__(self, customer=None, products=None,
                 receipt=None, connection=None):
       
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer
        self.products = products
        self.receipt = receipt
        self.employee = self.receipt.employee

    #create method
    def create(self):
        self.filename = u"{0}-{1}.pdf".format(self.document_type, self.receipt.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT, self.filename)
        #create the doc template
        doc = AckDocTemplate(self.location, id=self.receipt.id, company=self.receipt.company, pagesize=A4,
                             leftMargin=36, rightMargin=36, topMargin=36)
        #Build the document with stories
        stories = self._get_stories()
        doc.build(stories)
        #return the filename
        return self.location

    def firstPage(self, canvas, doc):
        path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * 30) / img_height
        canvas.drawImage(path, 45, 780, height=30, width=new_width)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 100)
        canvas.drawString(45, 760,
                          "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(45, 750, "Pathum Thani, Thailand, 12150")
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 790, 'Receipt')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 770, 'Receipt#: {0}'.format(self.receipt.id))

    def _get_stories(self):
        #initialize story array
        Story = []
        #create table for supplier and recipient data
        Story.append(self._create_contact_section())
        Story.append(Spacer(0, 20))
        #Create table for po data
        Story.append(self._create_order_section())
        Story.append(Spacer(0, 40))
        #Alignes the header and supplier to the left
        for a_story in Story:
            a_story.hAlign = 'LEFT'
        #creates the data to hold the product information
        Story.append(self._create_products_section())
        #spacer
        Story.append(Spacer(0, 50))
        Story.append(self._create_signature_section())
        return Story

    def _create_customer_section(self):
        #Create data array
        data = []
        #Add supplier name
        data.append(['Customer:', self.customer.name])
        try:
            #extract supplier address
            address = self.customer.addresses.all()[0]
            #Extract address
            addr = address.address1 if address.address1 != None else ''
            city = address.city if address.city != None else ''
            territory = address.territory if address.territory != None else ''
            country = address.country if address.country != None else ''
            zipcode = address.zipcode if address.zipcode != None else ''
            #add supplier address data
            data.append(['', addr])
            data.append(['', u'{0}, {1}'.format(city, territory)])
            data.append(['', u"{0} {1}".format(country, zipcode)])
        except IndexError:
            pass
        
        if self.customer.telephone:
            data.append(['Tel:', u'{0}'.format(self.customer.telephone)])

        if self.customer.email:
            data.append(['Email:', u'{0}'.format(self.customer.email)])

        # Add Tax ID
        if self.customer.tax_id:
            data.append(['Tax ID:', u'{0}'.format(self.customer.tax_id)])

        #Create Table
        table = Table(data, colWidths=(80, 440))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.black),
                            ('FONT', (0, 0), (-1, -1), 'Garuda')])
        table.setStyle(style)
        #Return the Recipient Table
        return table

    def _create_contact_section(self):
        """Create the Contact Table."""
        t1 = self._create_customer_section()
        #t2 = self._create_recipient_section()
        #create table for supplier and recipient data
        contact = Table([[t1]])
        #Create Style and apply
        style = TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), 
                            ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT')])
        contact.setStyle(style)
        #Return table
        return contact
 
    def _create_order_section(self):
        data = [[self._create_ack_section(), []]]
        table = Table(data, colWidths=(290, 285))
        style = TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')])
        table.setStyle(style)
        
        return table
        
    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        order_date, odObj = self.outputBKKTime(self.receipt.time_created, '%B %d, %Y')
        paid_date, ddObj = self.outputBKKTime(self.receipt.paid_date, '%B %d, %Y')
        data.append(['Currency:', self._get_currency()])
        data.append(['Order Date:', order_date])
        data.append(['Paid Date:', paid_date])
            
        if self.receipt.remarks is not None and self.receipt.remarks != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.black)
            paragraph = Paragraph(self.receipt.remarks.replace('\n', '<br/>'),
                                  style)
            data.append(['Remarks', paragraph])
        #Create table
        table = Table(data, colWidths=(80, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                            ('FONT', (0,0), (-1, -1), 'Garuda')])
                            #('GRID', (0,0), (-1,-1), 1, colors.black)])
        table.setStyle(style)
        #Return Table
        return table
        
    def _create_products_section(self):
        #Create data and index array
        data = []
        #Add Column titles
        data.append([self._create_products_title_section()])
        #iterate through the array
        for product in self.products:
            data.append([self._create_products_item_section(product)])

        data.append([self._create_totals_section()])
        table = Table(data, colWidths=(535), repeatRows=1)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.black),
                      ('TOPPADDING', (0, 0), (-1, -1), 0),
                      ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER')]
        table.setStyle(TableStyle(style_data))
        #loop through index to add line below item
        #Return the table
        return table

    def _create_products_title_section(self):
        titles = ['Product ID', 'Description', 'Unit Price', 'Qty', 'Total']
        table = Table([titles], colWidths=(80, 300, 60, 40, 65))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.black),
                      ('GRID', (0, 0), (-1, 0), 1, colors.black),
                      #General alignment
                      ('ALIGNMENT', (0, 0), (1, -1), 'CENTER'),
                      #Align description
                      ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
                      #Align Quantity
                      ('ALIGNMENT', (-3, 0), (-2, -1), 'CENTER'),
                      #align totals to the right
                      ('ALIGNMENT', (-1, 1), (-1, -1), 'RIGHT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _create_products_item_section(self, product):
        data = []
        #add the data
        data.append([code128.Code128("DRAI-{0}".format(product.id), barHeight=20), 
                     product.description,
                     product.unit_price, 
                     product.quantity, 
                     product.total])
  
        #Add comments if they exists
        if product.comments:
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   leading=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   fontSize=10,
                                   textColor=colors.black)
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'),
                                  style)
            comments = Table([['  Comments:', paragraph]], colWidths=(60, 235))
            comments.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.black)]))
            data.append(['', comments, ''])
        
        #Create table
        table = Table(data, colWidths=(80, 300, 60, 40, 65))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                            #Lines around content
                            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0, 0), (-1, -1), 1, colors.black),
                            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.black),
                            ('FONT', (0, 0), (-1, -1), 'Garuda'),
                            #General alignment
                            ('ALIGNMENT', (0, 0), (1, -1), 'CENTER'),
                            #Align description
                            ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
                            #Align Unit Price
                            ('ALIGNMENT', (-3, 0), (-3, -1), 'RIGHT'),
                            #Align Quantity
                            ('ALIGNMENT', (-2, 0), (-2, -1), 'CENTER'),
                            #align totals to the right
                            ('ALIGNMENT', (-1, 0), (-1, -1), 'RIGHT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _get_payment_terms(self):
        #determine Terms String
        # based on term length
        if self.supplier.terms == 0:
            terms = "Payment Before Delivery"
        else:
            terms = "{0} Days".format(self.supplier.terms)
        #return term
        return terms

    def _get_currency(self):
        #Determine currency string
        # based on currency
        """
        if self.po.currency == "EUR":
            currency = "Euro(EUR)"
        elif self.po.currency == "THB":
            currency = "Thai Baht(THB)"
        elif self.po.currency == "USD":
            currency = "US Dollar(USD)"
        #return currency"""
        return self.customer.currency

    def _get_description(self, supply):
        #Set description
        description = supply.description
        #If there is a discount then append
        # original price string
        if supply.discount > 0:
            description += " (discounted {0}% from {1})".format(supply.discount,
                                                                supply.cost)
        #return description
        return description

    def _create_totals_section(self):
        #Create data and style array
        data = []
        
        # Adding Totals to the data container

        # Add Subtotal
        if self.receipt.vat or self.receipt.discount or self.receipt.second_discount:
            data.append(['',
                        u'Subtotal',
                        "{0:,.2f}".format(self.receipt.subtotal)])
        # Add Discount if greater than 0
        if self.receipt.discount_amount > 0:
            data.append(['',
                         u'Discount {0}%'.format(self.receipt.discount),
                         u"-{:,.2f}".format(self.receipt.discount_amount)])
        # Add Second Discount if greater than 0
        if self.receipt.second_discount_amount > 0:
            data.append(['',
                         u'Additional Discount {0}%'.format(self.receipt.second_discount),
                         u"-{:,.2f}".format(self.receipt.second_discount_amount)])
        if (self.receipt.second_discount > 0 or self.receipt.discount > 0) and self.receipt.vat:
            data.append(['',
                         'Total',
                         "{0:,.2f}".format(self.receipt.total)])

        if self.receipt.vat_amount:
            data.append(['',
                         'Vat {0:.0f}%'.format(self.receipt.vat),
                         "{0:,.2f}".format(self.receipt.vat_amount)])

        final_total_title = u"Grand Total" if (self.receipt.discount or self.receipt.second_discount) and self.receipt.vat else u"Total"
        data.append(['',
                     final_total_title,
                     "{0:,.2f}".format(self.receipt.grand_total)])

        table = Table(data, colWidths=(80, 300, 165))
        style = TableStyle([('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                            #Lines around content
                            ('LINEBELOW', (-2, -1), (-1, -1), 1,
                             colors.CMYKColor(black=80)),
                            ('LINEAFTER', (-2, 0), (-1, -1), 1,
                             colors.black),
                            ('LINEBEFORE', (-2, 0), (-2, -1), 1,
                             colors.black),
                            #General alignment
                            ('ALIGNMENT', (-2, 0), (-2, -1), 'LEFT'),
                            #Align description
                            ('ALIGNMENT', (-1, 0), (-1, -1), 'RIGHT')])
        table.setStyle(style)
        style = TableStyle()

        return table

    def _create_signature_section(self):
        #create the signature
        signature = Table([['x', '', 'x'],['Received By', '', 'Authorized By']],
                          colWidths=(200, 100, 200))
        style = TableStyle([
                             ('TEXTCOLOR', (0,0), (-1,-1),
                              colors.black),
                             ('LINEBELOW', (0,0), (0,0), 1,
                              colors.black),
                             ('LINEBELOW', (-1,0), (-1,0), 1,
                              colors.black),
                             ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                             ('ALIGNMENT', (0,0), (-1,0), 'LEFT')])
        signature.setStyle(style)
        return signature

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

    def outputBKKTime(self, dateTimeObj, fmt):
        """
        The function accepts the datetime object
        and the preferred output str format to return
        the datetime as. This function then converts
        from the current utc(preferred) to the 'Asia/Bangkok'
        timezone
        """
        bkkTz = timezone('Asia/Bangkok')
        bkkDateTime = dateTimeObj.astimezone(bkkTz)
        return bkkDateTime.strftime(fmt), bkkDateTime
        











