#!/usr/bin/python
# -*- coding: utf-8 -*-


"""Collection of the classes that create pdf files
for an Acnowledgement. The Acknowledgement creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing 
production"""

from decimal import Decimal

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code39


pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT+'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT+'Garuda.ttf'))

class ShippingDocTemplate(BaseDocTemplate):
    
    id = 0
    top_padding = 150
    
    def __init__(self, filename, **kw):
        if "id" in kw: self.id = kw["id"]
        BaseDocTemplate.__init__(self, filename, **kw)
        self.addPageTemplates(self._create_page_template())
        
    def _create_page_template(self):
        frame = Frame(0, 0, 210*mm,297*mm, leftPadding=36, bottomPadding=30, rightPadding=36, topPadding=self.top_padding)
        template = PageTemplate('Normal', [frame])
        template.beforeDrawPage = self._create_header
        return template
    
  
    def _create_header(self, canvas, doc):
        #Draw the logo in the upper left
        path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width*30)/img_height
        canvas.drawImage(path, 42, 780, height=30, width=new_width)
        
        #Add Company Information in under the logo
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.drawString(42, 760, "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
        canvas.drawString(42, 740, "+66 2 998 7490")
        canvas.drawString(42, 730, "www.dellarobbiathailand.com")
        
        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Shipping/Receiving') 
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Shipping#: {0}'.format(self.id))
        
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        barcode = code39.Extended39('*S-{0}*'.format(self.id), barWidth=1, barHeight=30)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas,x_position,740)

        
class ShippingPDF(object):
    """Class to create PO PDF"""
    
    #attributes
    document_type = "Acknowledgement"
    
    #def methods
    def __init__(self, customer=None, products=None, shipping=None, connection=None):
        
        #set connection
        self.connection = connection if connection != None else S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer  
        self.products = products
        self.shipping = shipping
        self.ack = shipping.acknowledgement
        self.employee = self.ack.employee
    
    
    #create method
    def create(self):
        self.filename = "Shipping-{0}.pdf".format(self.shipping.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT,self.filename)
        #create the doc template
        doc = ShippingDocTemplate(self.location, id=self.shipping.id, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #Build the document with stories
        stories = self._get_stories()
        doc.build(stories)
        #return the filename
        return self.location
        
    def _get_stories(self):
        #initialize story array
        Story = []
        #add heading and spacing
        
        #create table for supplier and recipient data
        Story.append(self._create_contact_section())
        Story.append(Spacer(0,20))
        #Create table for po data
        Story.append(self._create_ack_section())
        Story.append(Spacer(0,40))
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
        #extract supplier address
        address = self.customer.address_set.all()[0] 
        #Create data array
        data = []
        #Add supplier name
        data.append(['Customer:', self.customer.name])
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
        #Create Table
        table = Table(data, colWidths=(80, 200))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1,-1), 'Garuda')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
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
        style = TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), 
                            ('ALIGNMENT', (0,0), (-1,-1), 'LEFT')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
        contact.setStyle(style)
        #Return table
        return contact
        
    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        data.append(['Order Date:', self.shipping.acknowledgement.time_created.strftime('%B %d, %Y')])
        data.append(['Delivery Date:', self.shipping.delivery_date.strftime('%B %d, %Y')])
        #Adds po if exists
        if self.shipping.acknowledgement.po_id != None:
            data.append(['PO #:', self.ack.po_id])
        if self.shipping.comments is not None and self.shipping.comments != '':
            data.append(['Comments', self.shipping.comments])
        #Create table
        table = Table(data, colWidths=(80, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
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
        #Create Table
        table = Table(data, colWidths=(520), repeatRows=1)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                      ('TOPPADDING', (0,0), (-1,-1), 0),
                      ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                      ('ALIGNMENT', (0,0), (-1,-1), 'CENTER')]
                           
        table.setStyle(TableStyle(style_data))
        #Return the table
        return table
    
    def _create_products_title_section(self):
        table = Table([['Product ID', 'Description', 'Qty']], colWidths=(65, 425, 40))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                      ('GRID', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                      #Align description
                      ('ALIGNMENT', (1,0), (1,-1), 'LEFT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table
    
    def _create_products_item_section(self, product):
        data = []
        #add the data
        data.append([product.item.product.id, product.description, product.quantity])
        try:
            data.append(['', self._get_fabric_table(product.item.fabric, "   Fabric:")])
        except:
            pass
        if product.item.is_custom_size:
            data.append(['', '   Width: %imm Depth: %imm Height: %imm' %(product.item.width, product.item.depth, product.item.height)])
        #increase the item number
        pillows = product.item.pillow_set.all()
        if len(pillows) > 0:
            for pillow in pillows:
                data.append(['', '   {0} Pillow'.format(pillow.type.capitalize()), pillow.quantity])
                try:
                    data.append(['', self._get_fabric_table(pillow.fabric.description, '       - Fabric:'), '',])
                except: pass
        #Add comments if they exists
        if product.comments is not None and product.comments != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'), style)
            comments = Table([['  Comments:', paragraph]], colWidths=(60, 340))
            comments.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Garuda'),
                                          ('FONTSIZE', (0,0), (-1, -1), 10),
                                          ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                          ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60))]))
            data.append(['', comments, ''])
        #Get Image url and add image
        if product.item.image_key is not None:
            image_url = self.connection.generate_url(100, 'GET', bucket=product.item.bucket, key=product.item.image_key, force_http=True)
            data.append(['', self.get_image(image_url, height=100)])
        #Create table
        table = Table(data, colWidths=(65, 425, 40))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0,0), (-1,-1), 1, colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0,0), (0,-1), 1, colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1,-1), 'Garuda'),
                            #General alignment
                            ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                            #Align description
                            ('ALIGNMENT', (1,0), (1,-1), 'LEFT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table
    
    def _get_fabric_table(self, fabric, string="   Fabric:"):
        fabric_str = string+' {0}'
        fabric_image = self.get_image(fabric.image_url, height=30)
        fabric_table = Table([[fabric_str.format(fabric.description), fabric_image]], colWidths=(200, 50))
        fabric_table.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Garuda'),
                                          ('FONTSIZE', (0,0), (-1, -1), 10),
                                          ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                          ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60))]))
        return fabric_table
    
    def _create_signature_section(self):
        #create the signature
        signature = Table([['x', '', 'x'], ['Delivery Agent', '', 'Recipient']], colWidths=(200,100,200))
        style = TableStyle([
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             #('LINEABOVE', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('LINEBELOW', (0,0), (0,0), 1, colors.CMYKColor(black=60)),
                             ('LINEBELOW', (-1,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                             ('ALIGNMENT', (0,0), (-1,0), 'LEFT')])
        signature.setStyle(style)
        return signature
        
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



    