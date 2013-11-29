#!/usr/bin/python
# -*- coding: utf-8 -*-


"""Collection of the classes that create pdf files
for an Acnowledgement. The Acknowledgement creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing
production"""

from decimal import Decimal

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
from reportlab.graphics.barcode import code128


pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class PODocTemplate(BaseDocTemplate):
    id = 0
    top_padding = 150

    def __init__(self, filename, **kw):
        if "id" in kw:
            self.id = kw["id"]
        BaseDocTemplate.__init__(self, filename, **kw)
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
        path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"""
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * 30) / img_height
        canvas.drawImage(path, 42, 780, height=30, width=new_width)

        #Add Company Information in under the logo
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.drawString(42, 760,
                          "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
        canvas.drawString(42, 740, "T: +66 2 998 7490")
        canvas.drawString(42, 730, "F: +66 2-997-3361")
        canvas.drawString(42, 720, "www.dellarobbiathailand.com")

        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Purchase Order')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'PO#: {0}'.format(self.id))

        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = 'PO-{0}'.format(self.id)
        barcode = code128.Code128(code, barHeight=20)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)


class PurchaseOrderPDF():
    """Class to create PO PDF"""
    document_type = "Purchase_Order"

    #def methods
    def __init__(self, supplier=None, items=None, po=None, attention=None,
                 misc=None, connection=None):
        #set connection
        self.connection = connection if connection != None else S3Connection(settings.AWS_ACCESS_KEY_ID, 
                                                                             settings.AWS_SECRET_ACCESS_KEY)
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']

        self.supplier = supplier
        self.supplies = items
        self.po = po
        self.employee = self.po.employee
        self.attention = attention

    #create method
    def create(self):
        self.filename = "%s-%s.pdf" % (self.document_type, self.po.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT, self.filename)
        #create the doc template
        doc = PODocTemplate(self.location, id=self.po.id, pagesize=A4,
                             leftMargin=36, rightMargin=36, topMargin=36)
        #Build the document with stories
        doc.build(self._get_stories())
        #return the filename
        return self.location

    def _get_stories(self):
        #initialize story array
        story = []
        #create table for supplier and recipient data
        story.append(self.__create_contact_section())
        story.append(Spacer(0, 20))
        #Create table for po data
        story.append(self.__create_po_section())
        story.append(Spacer(0, 40))
        #Alignes the header and supplier to the left
        for aStory in story:
            aStory.hAlign = 'LEFT'
        #creates the data to hold the supplies information
        story.append(self.__create_supplies_section())
        #spacer
        story.append(Spacer(0, 50))
        story.append(self._create_signature_section())
        #return the filename
        return story

    def __create_supplier_section(self):
        #extract supplier address
        address = self.supplier.address_set.all()[0]
        #Create data array
        data = []
        #Add supplier name
        data.append(['Supplier:', self.supplier.name])
        #add supplier address data
        data.append(['', address.address1])
        if address.address2:
            if address.address2.strip() != "":
                data.append(['', address.address2])

        data.append(['', "{0}, {1}".format(address.city, address.territory)])
        data.append(['', "{0} {1}".format(address.country, address.zipcode)])
        if self.supplier.telephone:
            data.append(['', "T: {0}".format(self.supplier.telephone)])
        if self.supplier.fax: 
            data.append(['', "F: {0}".format(self.supplier.fax)])
        if self.supplier.email:
            data.append(['', "E: {0}".format(self.supplier.email)])
            
        #Determines if we can add attention section
        if self.attention != None:
            att = '{0} {1}'.format(self.attention.first_name,
                                   self.attention.last_name)
            data.append(['Attention:', att])
            data.append(['', self.attention.email])
            data.append(['', self.attention.telephone])
        #Create Table
        table = Table(data, colWidths=(60, 200))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Helvetica')])
        table.setStyle(style)
        #Return the Recipient Table
        return table

    def __create_recipient_section(self):
        #Create data array
        data = []
        #Add Employee Name
        ship_str = "{0} {1}".format(self.employee.first_name, self.employee.last_name)
        data.append(['Ship To:', ship_str])
        #Add Company Data
        data.append(['', '8/10 Moo 4 Lam Luk Ka Rd. Soi 65'])
        data.append(['', 'Lam Luk Ka, Pathum Thani'])
        data.append(['', 'Thailand 12150'])
        #Create Table
        table = Table(data, colWidths=(50, 150))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Helvetica')])
        table.setStyle(style)
        #Return the Recipient Table
        return table

    def __create_contact_section(self):
        """Create the Contact Table."""
        t1 = self.__create_supplier_section()
        t2 = self.__create_recipient_section()
        #create table for supplier and recipient data
        contact = Table([[t1, t2]], colWidths=(280, 200))
        #Create Style and apply
        style = TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP')])
        contact.setStyle(style)
        #Return table
        return contact

    def __create_po_section(self):
        #Create data array
        data = []
        #Add Data
        data.append(['Terms:', self._get_payment_terms()])
        data.append(['Currency:', self._get_currency()])
        data.append(['Order Date:', self.po.order_date.strftime('%B %d, %Y')])
        #data.append(['Delivery Date:', self.po.receive_date.strftime('%B %d, %Y')])
        #Create table
        table = Table(data, colWidths=(60, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Helvetica')])
        table.setStyle(style)
        #Return Table
        return table

    def __create_supplies_section(self):
        #Create data array
        data = []
        #Add Column titles
        data = [['Item No.', 'Ref', 'Description', 'Units',
                 'Unit Price', 'Qty', 'Total']]
        i = 1
        #iterate through the array
        for supply in self.supplies:
            #add the data
            data.append([i, supply.supply.reference,
                         self.__get_description(supply),
                         supply.supply.units,
                         "%.2f" % float(supply.unit_cost),
                         supply.quantity,
                         "%.2f" % float(supply.total)])
            #increase the item number
            i += 1
        #add a shipping line item if there is a shipping charge
        if self.po.shipping_type != "none":
            shipping_description, shipping_amount = self._get_shipping()
            #Add to data
            data.append(['', '', shipping_description,
                         '', '', '',
                         "%.2f" % float(self.po.shipping_amount)])
        #Get totals data and style
        totals_data, totals_style = self._get_totals()
        #merge data
        data += totals_data
        #Create Table
        table = Table(data, colWidths=(40, 84, 230, 50, 50, 40, 65))
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                      ('LINEABOVE', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      #line under heading
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                      ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),
                      ('ALIGNMENT', (5, 0), (5, -1), 'CENTER'),
                      #align headers from description to total
                      ('ALIGNMENT', (3, 0), (-1, 0), 'CENTER'),
                      #align totals to the right
                      ('ALIGNMENT', (-1, 1), (-1, -1), 'RIGHT'),
                      ('ALIGNMENT', (-1, 0), (-1, 0), 'RIGHT'),
                      ('FONT', (0, 0), (-1, -1), 'Garuda'),
                      ('LEFTPADDING', (2, 0), (2, -1), 10),
                      ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                      ('VALIGN', (0, 1), (-1, -1), 'TOP')]
        style_data += totals_style
        #Create and apply table style
        style = TableStyle(style_data)
        table.setStyle(style)
        #Return the table
        return table

    def _create_signature_section(self):
        signature = Table([['x', '', 'x'], ['Purchasing Agent', '', 'Manager']],colWidths=(200,100,200))
        style = TableStyle([('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                            ('LINEBELOW', (0, 0), (0, 0), 1, colors.CMYKColor(black=60)),
                            ('LINEBELOW', (-1, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                            ('ALIGNMENT', (0, -1), (-1, -1), 'CENTER'),
                            ('ALIGNMENT', (0, 0), (-1, 0), 'LEFT')])
        #spacer
        signature.setStyle(style)
        return signature

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
        if self.po.currency == "EUR":
            currency = "Euro(EUR)"
        elif self.po.currency == "THB":
            currency = "Thai Baht(THB)"
        elif self.po.currency == "USD":
            currency = "US Dollar(USD)"
        #return currency
        return currency

    def __get_description(self, supply):
        #Set description
        description = supply.description
        #If there is a discount then append
        # original price string
        style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
        if supply.discount > 0:
            description += " (discounted %s%% from %s)" %(supply.description, supply.discount, supply.cost)
        #return description
        return Paragraph(description, style)

    def _get_shipping(self):
        #set the description
        if self.po.shipping_type == "air":
            description = "Air Freight"
        elif self.po.shipping_type == "sea":
            description = "Sea Freight"
        elif self.po.shipping_type == "ground":
            description = "Ground Freight"
        #return descript and amount
        return description, self.po.shipping_amount

    def _get_totals(self):
        #Create data and style array
        data = []
        style = []
        #calculate the totals
        #what to do if there is vat or discount
        if self.po.vat != 0 or self.supplier.discount != 0:
            #get subtotal and add to pdf
            subtotal = float(self.po.subtotal)
            data.append(['', '', '', '', '', 'Subtotal', "{0:.2f}".format(subtotal)])
            #add discount area if discount greater than 0
            if self.supplier.discount != 0:
                discount = subtotal * (float(self.supplier.discount) / float(100))
                dis_title = 'Discount {0}%'.format(self.supplier.discount)
                dis_str = "{0:.2f}".format(discount)
                data.append(['', '', '', '', '', dis_title, dis_str])
            #add vat if vat is greater than 0
            if self.po.vat != 0:
                if self.supplier.discount != 0:
                    #append total to pdf
                    data.append(['', '', '', '', '', 'Total', "{0:.2f}".format(self.po.total)])
                #calculate vat and add to pdf
                vat = Decimal(self.po.total) * (Decimal(self.po.vat) / Decimal('100'))
                data.append(['', '', '', '', '', 'Vat {0}%'.format(self.po.vat), "{0:.2f}".format(vat)])
        data.append(['', '', '', '', '', 'Grand Total', "{0:.2f}".format(self.po.grand_total)]) 
        #adjust the style based on vat and discount
        #if there is either vat or discount
        if self.po.vat != 0 or self.supplier.discount != 0:
            #if there is only vat or only discount
            if self.po.vat != 0 and self.supplier.discount != 0:
                style.append(('LINEABOVE', (0, -5), (-1, -5), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2, -5), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -5), (-1, -1), 1))
            #if there is both vat and discount
            else:
                style.append(('LINEABOVE', (0, -3), (-1, -3), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2, -3), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -3), (-1, -1), 1))
                
        #if there is no vat or discount
        else:
            style.append(('LINEABOVE', (0, -1), (-1, -1), 1,
                          colors.CMYKColor(black=60)))
            style.append(('ALIGNMENT', (-2, -1), (-1, -1), 'RIGHT'))
            style.append(('BOTTOMPADDING', (-2, -1), (-1, -1), 1))
        style.append(('ALIGNMENT', (-2, -3), (-1, -1), 'RIGHT'))
        #Return data and style
        return data, style

    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None):
        img = utils.ImageReader(path)
        imgWidth, imgHeight = img.getSize()
        if width != None and height == None:
            ratio = imgHeight / imgWidth
            newHeight = ratio * width
            newWidth = width
        elif height != None and width == None:
            ratio = imgWidth / imgHeight
            newHeight = height
            newWidth = ratio * height
        return Image(path, width=newWidth, height=newHeight)
