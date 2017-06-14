#!/usr/local/bin/python
# -*- coding: utf-8 -*-
"""Collection of the classes that create pdf files
for an Acnowledgement. The Acknowledgement creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing
production
"""

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
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT, TA_CENTER



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
            path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"""
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
        canvas.setFillColorCMYK(0, 0, 0, 60)

        #Add Company Information in under the logo if dellarobbia
        if self.company.lower() == 'dellarobbia thailand':
            canvas.drawString(42, 760,
                            "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
            canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
            canvas.drawString(42, 740, "+66 2 998 7490")
        else:
            canvas.drawString(42, 760,
                            "386/2 Hathai Rat Rd., Samwa, Samwa")
            canvas.drawString(42, 750, "Bangkok, Thailand, 10510")
            canvas.drawString(42, 740, "+66 2 998 7490")
        #canvas.drawString(42, 730, "www.dellarobbiathailand.com")
        
        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Acknowledgement')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Order#: {0}'.format(self.id))
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = "A-{0}".format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)
        

class ConfirmationDocTemplate(BaseDocTemplate):
    id = 0
    top_padding = 150

    def __init__(self, filename, **kwargs):
        if "id" in kwargs:
            self.id = kwargs["id"]
            
        try:
            self.company = kwargs['company'] or 'dellarobbia thailand'
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
            path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"""
        else:
            path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"
        
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * logo_height) / img_height
        canvas.drawImage(path, 42, 760, height=logo_height, width=new_width)

        #Add Company Information in under the logo if dellarobbia
        if self.company.lower() == 'dellarobbia thailand':
            canvas.drawString(42, 760,
                            "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
            canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
            canvas.drawString(42, 740, "+66 2 998 7490")
        else:
            canvas.drawString(42, 760,
                            "386/2 Hathai Rat Rd., Samwa, Samwa")
            canvas.drawString(42, 750, "Bangkok, Thailand, 10510")
            canvas.drawString(42, 740, "+66 2 998 7490")
        #canvas.drawString(42, 730, "www.dellarobbiathailand.com")

        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Confirmation')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Order#: {0}'.format(self.id))
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = "A-{0}".format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)


class ProductionDocTemplate(AckDocTemplate):
    id = 0
    top_padding = 120

    def _create_header(self, canvas, doc):
        #Draw the logo in the upper left
        #if self.company.lower() == 'dellarobbia thailand':
        #    path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"""
        #else:
        #    path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/alinea-logo.png"""

        path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"""
        
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * logo_height) / img_height
        canvas.drawImage(path, 42, 760, height=logo_height, width=new_width)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Production')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Order#: {0}'.format(self.id))
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = "A-{0}".format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)


class ShippingLabelDocTemplate(BaseDocTemplate):
    
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.addPageTemplates([self._create_page_template(template_id="labels")])
        
    def _create_page_template(self, template_id):
        """
        Creates a basic page template
        """
        frame = Frame(0, 0, 210 * mm,297 * mm, leftPadding=36, bottomPadding=12, rightPadding=36, topPadding=12)
        template = PageTemplate(id=template_id, frames=[frame])
        
        return template
        

class AcknowledgementPDF(object):
    """Class to create PO PDF"""
    #attributes
    document_type = "Acknowledgement"

    def __init__(self, customer=None, products=None,
                 ack=None, connection=None):
       
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer
        self.products = products
        self.ack = ack
        self.employee = self.ack.employee

    #create method
    def create(self):
        self.filename = "%s-%s.pdf" % (self.document_type, self.ack.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT, self.filename)
        #create the doc template
        doc = AckDocTemplate(self.location, id=self.ack.id, company=self.ack.company, pagesize=A4,
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
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.drawString(45, 760,
                          "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(45, 750, "Pathum Thani, Thailand, 12150")
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 790, 'Acknowledgement')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 770, 'Ack#: {0}'.format(self.ack.id))

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
            
        #Create Table
        table = Table(data, colWidths=(80, 440))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
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
        data = [[self._create_ack_section(), self._create_project_section()]]
        table = Table(data, colWidths=(290, 285))
        style = TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')])
        table.setStyle(style)
        
        return table
        
    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        order_date, odObj = self.outputBKKTime(self.ack.time_created, '%B %d, %Y')
        delivery_date, ddObj = self.outputBKKTime(self.ack.delivery_date, '%B %d, %Y')
        data.append(['Currency:', self._get_currency()])
        data.append(['Order Date:', order_date])
        data.append(['Delivery Date:', delivery_date])
        #Adds po if exists
        if self.ack.po_id != None:
            data.append(['PO #:', self.ack.po_id])
            
        if self.ack.remarks is not None and self.ack.remarks != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(self.ack.remarks.replace('\n', '<br/>'),
                                  style)
            data.append(['Remarks', paragraph])
        #Create table
        table = Table(data, colWidths=(80, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1, -1), 'Garuda')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
        table.setStyle(style)
        #Return Table
        return table
        
    def _create_project_section(self):
        
        if self.ack.project:
            #Create data array
            data = []
            #Add Data
            project = self.ack.project.codename
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            project_paragraph = Paragraph(project, style)
            data.append(['Project:', project_paragraph])
           
            if self.ack.room:
                data.append(['Room:', self.ack.room.description])
                
            if self.ack.phase:
                data.append(['Phase:', self.ack.phase.description])
            
            #Create table
            table = Table(data, colWidths=(50, 225))
            #Create and set table style
            style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                ('TOPPADDING', (0,0), (-1,-1), 1),
                                ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                                ('FONT', (0,0), (-1, -1), 'Garuda')])
                                #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
            table.setStyle(style)
            #Return Table
            return table
        
        else:
            return u""
            
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
                       colors.CMYKColor(black=60)),
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
                       colors.CMYKColor(black=60)),
                      ('GRID', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
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
        try:
            data.append(['', self._get_fabric_table(product.fabric, "   Fabric:"), '', '', ''])
        except Exception as e:
            print e
            
        if product.is_custom_size:
            dimension_str = 'Width: {0}mm Depth: {1}mm Height: {2}mm'.format(product.width, product.depth, product.height)
            data.append(['', dimension_str])
        #increase the item number
        if len(product.pillows.all()) > 0:
            for pillow in product.pillows.all():
                data.append(['', '   {0} Pillow'.format(pillow.type.capitalize()), '', pillow.quantity, ''])
                if pillow.fabric:
                    data.append(['', self._get_fabric_table(pillow.fabric, '       - Fabric:'), '', '', ''])
                else:
                    data.append(['', '       - Fabric: unspecified', '', '', ''])

        #Add comments if they exists
        if product.comments:
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   leading=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'),
                                  style)
            comments = Table([['  Comments:', paragraph]], colWidths=(60, 340))
            comments.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.CMYKColor(black=60))]))
            data.append(['', comments, ''])
        #Get Image url and add image
        if product.image:
            data.append(['', self.get_image(product.image.generate_url('', '', time=3600), height=100, max_width=290)])
        #Create table
        table = Table(data, colWidths=(80, 300, 60, 40, 65))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.CMYKColor(black=60)),
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

    def _get_fabric_table(self, fabric, string="   Fabric:"):
        fabric_str = string + ' {0}'
        try:
            fabric_image = self.get_image(fabric.image.generate_url('', '', time=3600), height=30)
        except AttributeError:
            fabric_image = None
        fabric_table = Table([[fabric_str.format(fabric.description),fabric_image]],
                             colWidths=(200, 50))
        fabric_table.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.CMYKColor(black=60))]))
        return fabric_table

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

    def _get_shipping(self):
        #set the description
        if self.ack.shipping_type == "air":
            description = "Air Freight"
        elif self.ack.shipping_type == "sea":
            description = "Sea Freight"
        elif self.ack.shipping_type == "ground":
            description = "Ground Freight"
        #return descript and amount
        return description, self.ack.shipping_amount

    def _create_totals_section(self):
        #Create data and style array
        data = []
        #calculate the totals
        #what to do if there is vat or discount
        if self.ack.vat > 0 or self.ack.discount > 0:
            #get subtotal and add to pdf
            data.append(['', 'Subtotal', "{0:,.2f}".format(self.ack.subtotal)])
            total = self.ack.subtotal
            #add discount area if discount greater than 0
            if self.ack.discount != 0:
                discount = self.ack.subtotal * (Decimal(self.ack.discount) / Decimal(100))
                data.append(['', 'Discount {0}%'.format(self.ack.discount), "{0:,.2f}".format(discount)])
            #add vat if vat is greater than 0
            if self.ack.vat != 0:
                if self.ack.discount != 0:
                    #append total to pdf
                    discount = self.ack.subtotal * (Decimal(self.ack.discount) / Decimal(100))
                    total -= discount
                    data.append(['', 'Total', "{0:,.2f}".format(total)])
                    
                    prevat_total = total
                else:
                    prevat_total = self.ack.subtotal
                    
                #calculate vat and add to pdf
                vat = Decimal(prevat_total) * (Decimal(self.ack.vat) / Decimal(100))
                data.append(['', 'Vat {0}%'.format(self.ack.vat), "{0:,.2f}".format(vat)])
        data.append(['', 'Grand Total', "{0:,.2f}".format(self.ack.total)])
        table = Table(data, colWidths=(80, 300, 165))
        style = TableStyle([('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (-2, -1), (-1, -1), 1,
                             colors.CMYKColor(black=80)),
                            ('LINEAFTER', (-2, 0), (-1, -1), 1,
                             colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (-2, 0), (-2, -1), 1,
                             colors.CMYKColor(black=60)),
                            #General alignment
                            ('ALIGNMENT', (-2, 0), (-2, -1), 'LEFT'),
                            #Align description
                            ('ALIGNMENT', (-1, 0), (-1, -1), 'RIGHT')])
        table.setStyle(style)
        style = TableStyle()

        return table

    def _create_signature_section(self):
        #create the signature
        signature = Table([['x', '', 'x'],['Office Manager', '', 'Authorized Signature']],
                          colWidths=(200, 100, 200))
        style = TableStyle([
                             ('TEXTCOLOR', (0,0), (-1,-1),
                              colors.CMYKColor(black=60)),
                             ('LINEBELOW', (0,0), (0,0), 1,
                              colors.CMYKColor(black=60)),
                             ('LINEBELOW', (-1,0), (-1,0), 1,
                              colors.CMYKColor(black=60)),
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
        

class ConfirmationPDF(object):
    """Class to create PO PDF"""
    #attributes
    document_type = "Confirmation"

    def __init__(self, customer=None, products=None,
                 ack=None, connection=None):
       
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer
        self.products = products
        self.ack = ack
        self.employee = self.ack.employee

    #create method
    def create(self):
        self.filename = "%s-%s.pdf" % (self.document_type, self.ack.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT, self.filename)
        #create the doc template
        doc = ConfirmationDocTemplate(self.location, id=self.ack.id, company=self.ack.company, pagesize=A4,
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
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.drawString(45, 760,
                          "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(45, 750, "Pathum Thani, Thailand, 12150")
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 790, 'Acknowledgement')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 770, 'Ack#: {0}'.format(self.ack.id))

    def _get_stories(self):
        #initialize story array
        Story = []
        #create table for supplier and recipient data
        Story.append(self._create_contact_section())
        Story.append(Spacer(0, 20))
        #Create table for po data
        Story.append(self._create_ack_section())
        Story.append(Spacer(0, 40))
        #Alignes the header and supplier to the left
        for a_story in Story:
            a_story.hAlign = 'LEFT'
        #creates the data to hold the product information
        Story.append(self._create_products_section())
        #spacer
        Story.append(Spacer(0, 50))
        Story.append(self._create_terms_section())
        
        #Space out and create signature section
        Story.append(Spacer(0, 40))
        signature_section =self._create_signature_section()
        signature_section.hAlign = 'LEFT'
        Story.append(signature_section)
        
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
            data.append(['', '%s, %s' % (city, territory)])
            data.append(['', "%s %s" % (country, zipcode)])
        except IndexError:
            pass
            
        #Create Table
        table = Table(data, colWidths=(80, 440))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
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

    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        order_date, odObj = self.outputBKKTime(self.ack.time_created, '%B %d, %Y')
        delivery_date, ddObj = self.outputBKKTime(self.ack.delivery_date, '%B %d, %Y')
        
        #data.append(['Currency:', self._get_currency()])
        data.append(['Order Date:', order_date])
        data.append(['Delivery Date:', delivery_date])
        #Adds po if exists
        if self.ack.po_id != None:
            data.append(['PO #:', self.ack.po_id])
            
        if self.ack.project:
            data.append(['Project:', self.ack.project.codename])
            
        if self.ack.remarks is not None and self.ack.remarks != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(self.ack.remarks.replace('\n', '<br/>'),
                                  style)
            data.append(['Remarks', paragraph])
        #Create table
        table = Table(data, colWidths=(80, 440))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1, -1), 'Garuda')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
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

        table = Table(data, colWidths=(535), repeatRows=1)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.CMYKColor(black=60)),
                      ('TOPPADDING', (0, 0), (-1, -1), 0),
                      ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER')]
        table.setStyle(TableStyle(style_data))
        #loop through index to add line below item
        #Return the table
        return table

    def _create_products_title_section(self):
        titles = ['Product ID', 'Description', 'Qty']
        table = Table([titles], colWidths=(80, 425, 40))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.CMYKColor(black=60)),
                      ('GRID', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0, 0), (1, -1), 'CENTER'),
                      #Align description
                      ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
                      #Align Quantity
                      ('ALIGNMENT', (-1, 0), (-1, -1), 'CENTER')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _create_products_item_section(self, product):
        data = []
        #add the data
        data.append([code128.Code128("DRAI-{0}".format(product.id), barHeight=20), 
                     product.description,
                     product.quantity])
        try:
            data.append(['', self._get_fabric_table(product.fabric, "   Fabric:"), ''])
        except Exception as e:
            print e
            
        if product.is_custom_size:
            dimension_str = 'Width: {0}mm Depth: {1}mm Height: {2}mm'.format(product.width, product.depth, product.height)
            data.append(['', dimension_str])
        #increase the item number
        if len(product.pillows.all()) > 0:
            for pillow in product.pillows.all():
                data.append(['', '   {0} Pillow'.format(pillow.type.capitalize()), pillow.quantity])
                if pillow.fabric:
                    data.append(['', self._get_fabric_table(pillow.fabric, '       - Fabric:'), '',])
                else:
                    data.append(['', '       - Fabric: unspecified', ''])
        #Add comments if they exists
        if product.comments:
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   leading=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'),
                                  style)
            comments = Table([['  Comments:', paragraph]], colWidths=(60, 340))
            comments.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.CMYKColor(black=60))]))
            data.append(['', comments, ''])
        #Get Image url and add image
        if product.image:
            data.append(['', self.get_image(product.image.generate_url('', '', time=3600), height=75, max_width=290)])
        #Create table
        table = Table(data, colWidths=(80, 425, 40))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0, 0), (0, -1), 1, colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Garuda'),
                            #General alignment
                            ('ALIGNMENT', (0, 0), (1, -1), 'CENTER'),
                            #Align description
                            ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
                            #Align Quantity
                            ('ALIGNMENT', (-1, 0), (-1, -1), 'CENTER'),
                          ]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _get_fabric_table(self, fabric, string="   Fabric:"):
        fabric_str = string + ' {0}'
        try:
            fabric_image = self.get_image(fabric.image.generate_url('', '', time=3600), height=30)
        except AttributeError:
            fabric_image = None
        fabric_table = Table([[fabric_str.format(fabric.description),fabric_image]],
                             colWidths=(200, 50))
        fabric_table.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 10),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.CMYKColor(black=60))]))
        return fabric_table

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
            description += " (discounted %s%% from %s)" %(supply.description,
                                                          supply.discount,
                                                          supply.cost)
        #return description
        return description

    def _get_shipping(self):
        #set the description
        if self.ack.shipping_type == "air":
            description = "Air Freight"
        elif self.ack.shipping_type == "sea":
            description = "Sea Freight"
        elif self.ack.shipping_type == "ground":
            description = "Ground Freight"
        #return descript and amount
        return description, self.ack.shipping_amount
        
    def _create_terms_section(self):
        
        terms_th = u"กรุณาตรวจสอบรายละเอียดข้างต้นให้เรียบร้อยก่อนเซ็นรับทราบเพื่อผลิต มิฉะนั้นถ้าเกิดข้อผิดพลาด ทางบริษัทฯไม่รับผิดชอบ กรุณาตรวจสอบและยืนยันกลับภายใน 48 ชั่วโมง"
        terms_en = u"""By signing this document, the signator hereby acknowledges that the specified items ordered and their respective dimensions, colors, fabrics, construction details are correct. The signator accepts responsibility for any cost associated with changes after authorizing production. Please returned a signed copy within 48 hours."""
        
        terms = u"".join([terms_en, "\n\n", terms_th])
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               leading=12,
                               wordWrap='CJK',
                               allowWidows=1,
                               allowOrphans=1,
                               fontSize=10,
                               textColor=colors.CMYKColor(black=60))
        paragraph = Paragraph(terms.replace('\n', '<br/>'), style)
                           
        return paragraph   
            
        
    def _create_signature_section(self):
        #create the signature
        signature = Table([['Name:', '', '', ''],
                           ['', '', '', ''], 
                           ['Authorized Customer Signature:', '', '', ''],
                           [u'(ผู้รับผิดชอบ)', '', '', '(Date)']],
                          colWidths=(155, 250, 15, 100))
                          
        style = TableStyle([('PADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1),
                             colors.CMYKColor(black=60)),
                            ('LINEBELOW', (-3,0), (-3,0), 1,
                             colors.CMYKColor(black=60)),
                            ('LINEBELOW', (-3,-2), (-3,-2), 1,
                             colors.CMYKColor(black=60)),
                            ('LINEBELOW', (-1,-2), (-1,-2), 1,
                             colors.CMYKColor(black=60)),
                            ('ALIGNMENT', (0,0), (-1,-2), 'LEFT'),
                            #Style for last line
                            ('FONT', (0,-1), (0,-1), 'Garuda'),
                            ('ALIGNMENT', (0,-1), (-1,-1), 'CENTER')])
                             
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
        

class ProductionPDF(AcknowledgementPDF):
    thai_months = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.ิ",
                   "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
    document_type = "Production"

    def __init__(self, **kwargs):
        super(ProductionPDF, self).__init__(customer=kwargs["customer"],
                                            ack=kwargs["ack"],
                                            products=kwargs["products"])

    #create method
    def create(self):
        self.filename = "%s-%s.pdf" % (self.document_type, self.ack.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT, self.filename)
        #create the doc template
        doc = ProductionDocTemplate(self.location, id=self.ack.id, company=self.ack.company, pagesize=A4,
                                    leftMargin=36, rightMargin=36,
                                    topMargin=36)
        #Build the document with stories
        stories = self._get_stories()
        doc.build(stories)
        #return the filename
        return self.location

    def _get_stories(self):
        #initialize story array
        Story = []
        #add heading and spacing
        Story.append(self._create_ack_section())
        Story.append(Spacer(0, 30))
        #Alignes the header and supplier to the left
        for a_story in Story:
            a_story.hAlign = 'LEFT'
        #creates the data to hold the product information
        Story.append(self._create_products_section())
        Story.append(Spacer(0, 50))
        Story.append(self._create_signature_section())
        
        return Story

    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        time_create_str, date_obj = self.outputBKKTime(self.ack.time_created, '%d {0}, %Y')
        order_date_str = time_create_str.format(self.thai_months[date_obj.month-1])
        data.append(['Order Date:', order_date_str])
        delivery_date_str, date_obj = self.outputBKKTime(self.ack.delivery_date, '%d {0}, %Y')
        deliver_date_str = delivery_date_str.format(self.thai_months[date_obj.month-1])
        data.append(['กำหนดส่ง:', deliver_date_str])
        
        if self.ack.project:
            data.append(['Project:', self.ack.project.codename])
        if self.ack.room:
            data.append(['Room:', self.ack.room.description])
            
        if self.ack.remarks is not None and self.ack.remarks != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(self.ack.remarks.replace('\n', '<br/>'),
                                  style)
            data.append(['Remarks', paragraph])
        #Create table
        table = Table(data, colWidths=(80, 440))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Garuda')])
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
        #Create Table
        table = Table(data, colWidths=(535), repeatRows=1, splitByRow=True)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                      ('TOPPADDING', (0, 0), (-1, -1), 0),
                      ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER')]
        table.setStyle(TableStyle(style_data))
        #Return the table
        return table

    def _create_products_title_section(self):
        table = Table([['Product ID', 'Description', 'Qty']],
                      colWidths=(80, 400, 60), rowHeights=48)
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.CMYKColor(black=60)),
                      ('GRID', (0,0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                      ('FONTSIZE', (0,0), (-1,-1), 16),
                      ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                      #Align description
                      ('ALIGNMENT', (1,0), (1,-1), 'LEFT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _create_products_item_section(self, product):
        data = []
        #add the data
        data.append([code128.Code128("DRAI-{0}".format(product.id), barHeight=20), 
                     product.description,
                     product.quantity])
        try:
            data.append(['', self._get_fabric_table(product.fabric, '   Fabric:'), ''])
        except:
            pass

        data.append(['', u'   กว้าง: {0}mm'.format(product.width)])
        data.append(['', u'   ลึก: {0}mm'.format(product.depth)])
        data.append(['', u'   สูง: {0}mm'.format(product.height)])
        
        #increase the item number
        if len(product.pillows.all()) > 0:
            for pillow in product.pillows.all():
                if pillow.type == "back":
                    pillow_type = 'หมอนพิงหลัง'
                elif pillow.type == "accent":
                    pillow_type = 'หมอนโยน'
                elif pillow.type == "lumbar":
                    pillow_type = "Lumbar Pillow"
                else:
                    pillow = "Pillow"
                data.append(['', '   {0}'.format(pillow_type), pillow.quantity])
                try:
                    data.append(['', self._get_fabric_table(pillow.fabric, '       - Fabric:'), ''])
                except:
                    data.append(['', '       - Fabric:unspecified', ''])

        if len(product.components.all()) > 0:
            for component in product.components.all():
                data.append([code128.Code128("DRAIC-{0}".format(component.id), barHeight=15),
                             '   {0}'.format(component.description),
                             '{0}'.format(component.quantity)])


        #Add comments

        if product.comments is not None and product.comments != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   leading=16,
                                   fontSize=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   textColor='red')
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'),
                                  style)
            comments = Table([['  Comments:', paragraph]], colWidths=(100, 300))
            comments.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), 'Garuda'),
                                          ('FONTSIZE', (0, 0), (-1, -1), 16),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TEXTCOLOR', (0, 0), (-1, -1),
                                           colors.CMYKColor(black=60))]))
            data.append(['', comments, ''])
        #Get Image url and add image
        data.append([''])
        if product.image:
            data.append(['', self.get_image(product.image.generate_url('', '', time=3600), height=100, max_width=400)])
        #Create table
        table = Table(data, colWidths=(80, 400, 60), splitByRow=True)
        style_data = [('TEXTCOLOR', (0,0), (-1,-1),
                       colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0,-1), (-1,-1), 1,
                             colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0,0), (-1,-1), 1,
                             colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0,0), (0,-1), 1,
                             colors.CMYKColor(black=60)),
                            #General alignment
                            ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                            #Font
                            ('FONT', (0,0), (-1,-1), 'Garuda'),
                            #Align description
                            ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                            # ALIGN QUANTITY
                            ('ALIGNMENT', (-1,0), (-1,-1), 'RIGHT'),
                            ('FONTSIZE', (0,0), (-1,-1), 12),
                            #('GRID', (0, 0), (-1, -1), 1, 'blue'),
                            #('GRID', (1, 0), (-1, -1), 1, 'red'),
                            ('TOPPADDING', (0, 0), (-1, -1), 5),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table
        
    def _create_signature_section(self):
        #create the signature
        signature = Table([['x', '', 'x'],['Office Manager', '', 'Authorized Signature']],
                          colWidths=(200, 100, 200))
        style = TableStyle([
                             ('TEXTCOLOR', (0,0), (-1,-1),
                              colors.CMYKColor(black=60)),
                             ('LINEBELOW', (0,0), (0,0), 1,
                              colors.CMYKColor(black=60)),
                             ('LINEBELOW', (-1,0), (-1,0), 1,
                              colors.CMYKColor(black=60)),
                             ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                             ('ALIGNMENT', (0,0), (-1,0), 'LEFT')])
        signature.setStyle(style)
        return signature
    

class SingleStickerDocTemplate(BaseDocTemplate):

    def __init__(self, filename, **kwargs):
        """
        Constructor

        Set the page size in the kwargs then
        Call the parent constructor of the base doc template
        and then apply addition settings
        """
        self.width, self.height = (62 * mm, 180 * mm)
        kwargs['pagesize'] = (self.width, self.height)
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
    
class ShippingLabelPDF(object):
    """Class to create PO PDF"""
    
    #attributes
    document_type = "Shipping"
    
    #def methods
    def __init__(self, customer=None, products=None, ack=None):
        
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer  
        self.products = products
        self.ack = ack
        self.employee = self.ack.employee
        self.width = 57 * mm
    
    #create method
    def create(self):
        self.filename = "ShippingLabel-{0}.pdf".format(self.ack.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT,self.filename)
        #create the doc template
        doc = SingleStickerDocTemplate(self.location)
        #Build the document with stories
        stories = self._get_stories()
        doc.build(stories)
        #return the filename
        return self.location
        
    def _get_stories(self):
        #initialize story array
        story = []
        
        story = self._create_packing_labels_section(story)
        for a_story in story:
            a_story.hAlign = 'CENTER'

        return story    
    
    def _create_logo(self):
        """Creates the logo to be used in the labels
        """
        logo_path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Updated.png"
        logo = self.get_image(logo_path, width=150)

        table = Table([[logo]], colWidths=(self.width))
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1,-1), 'MIDDLE'),
                            ('LINEBELOW', (0, 0), (-1, -1),1, colors.CMYKColor(black=100)),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60))])
        table.setStyle(style)

        return table

    def _create_description_section(self, description):
        """Create the primary description for this label
        """
         #Add the product information to the array
        #print product.product.image9
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=24,
                               leading=24,
                               alignment=TA_CENTER,
                               textColor=colors.CMYKColor(black=60))
        paragraph = Paragraph(u"{0}".format(description), style)
        data = [[paragraph]]
        
        table = Table(data, colWidths=(self.width))
        style = TableStyle([('FONTSIZE', (0,0), (-1, -1), 16),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('FONT', (0,0), (-1,-1), 'Garuda'),
                            ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1,-1), 'MIDDLE'),
                            ('LINEBELOW', (-1, -1), (-1, -1),1, colors.CMYKColor(black=100)),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60))])
        table.setStyle(style)

        return table

    def _create_quantity_section(self, quantity):
        """Create the primary description for this label
        """
         #Add the product information to the array
        #print product.product.image9
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=18,
                               leading=18,
                               alignment=TA_CENTER,
                               textColor=colors.CMYKColor(black=60))
        paragraph = Paragraph(u"QTY: {0}".format(quantity), style)
        data = [[paragraph]]
        
        table = Table(data, colWidths=(self.width))
        style = TableStyle([('FONTSIZE', (0,0), (-1, -1), 16),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('FONT', (0,0), (-1,-1), 'Garuda'),
                            ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1,-1), 'MIDDLE'),
                            ('LINEBELOW', (-1, -1), (-1, -1),1, colors.CMYKColor(black=100)),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60))])
        table.setStyle(style)

        return table

    def _create_barcode_section(self, template_str, id):
        """Create and returns a barcode
        """
        code = template_str.format(id)
        barcode = code128.Code128(code, barHeight=50)

        code_table = Table([[barcode], [code]], colWidths=(self.width))
        code_style = TableStyle([('FONTSIZE', (0, 1), (0 , 1), 8), #Font size for code
                                 #Set code next to barcode
                                 ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
                                 ('TOPPADDING', (0, 0), (0, 0), 10),
                                 ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'), #Alignment for barcode, code, and qty
                                 ('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60))])
        code_table.setStyle(code_style)

        return code_table

    def _create_details_section(self, item=None):
        """Creates a table with the order details
        """

        if item:
            data = [[u"Item:", u"{0}".format(item.description)]]
        else:
            data = []

        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=10,
                               leading=10,
                               textColor=colors.CMYKColor(black=60))
        customer_paragraph = Paragraph(u"{0}".format(self.ack.customer.name), style)
        
        try:
            project = u"{0}".format(self.ack.project.codename)
        except AttributeError:
            project = ""

        try:
            room = u"{0}".format(self.ack.room.description)
        except AttributeError:
            room = ""
            
        data  += [["Ack#:", u"{0}".format(self.ack.id)],
                  ["Customer:", customer_paragraph],
                  ["Project:", project],
                  ["Room:", room]]

        
        
        details_table = Table(data, colWidths=(self.width * .3, self.width * .7))
        style = TableStyle([('FONTSIZE', (0, 0), (-1 , -1), 10), #Font size for order data
                            ('TOPPADDING', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, -1), (-1, -1), 20),
                            ('FONT', (0,0), (-1,-1), 'Garuda'), #Font for all text
                            ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'), #Alignment for barcode, code, and qty
                            ('LEFTPADDING', (0, 0), (-1, -1), 5),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.CMYKColor(black=100)),
                            ('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60))])
        details_table.setStyle(style)

        return details_table


    def _create_packing_label(self, product):
        """
        Creates an individual packing label as a 
        Table.
        """ 
        label_data = [[self._create_logo()],
                      [self._create_description_section(product.description)], 
                      [self._create_quantity_section(1)],
                      [self._create_details_section()],
                      [self._create_barcode_section("DRAI-{0}", product.id)]]
        label = Table(label_data, colWidths=(self.width))
        label_style = TableStyle([('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('BOX', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60))])
        label.setStyle(label_style)
        
        return label

    def _create_component_label(self, component):
        """
        Creates an individual component label as a 
        Table.
        """
        label_data = [[self._create_logo()],
                      [self._create_description_section(component.description)],
                      [self._create_quantity_section(component.quantity)],
                      [self._create_details_section(item=component.item)],
                      [self._create_barcode_section("DRAC-{0}", component.id)]]
        label = Table(label_data, colWidths=self.width)
        label_style = TableStyle([('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('BOX', (0, 0), (-1, -1), 1, colors.CMYKColor(black=60))])
        label.setStyle(label_style)
        
        return label
    
    def _create_packing_labels_section(self, story):
        
        product_data = []
        
        #Produces a label for each quantity of each product
        for product in self.products:
            for i in range(0, product.quantity):
                story.append(self._create_packing_label(product))
                story.append(PageBreak())
                for component in product.components.all():
                    story.append(self._create_component_label(component))
                    story.append(PageBreak())
      
    
        return story
        
    #helps change the size and maintain ratio
    def get_image(self, path, width=None, height=None):
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
        if width!=None and height==None:
            ratio = float(imgHeight)/float(imgWidth)
            newHeight = ratio*width
            newWidth = width
        elif height!=None and width==None:
            ratio = float(imgWidth)/float(imgHeight)
            newHeight = height
            newWidth = ratio*height
           
        return Image(path, width=newWidth, height=newHeight)
    