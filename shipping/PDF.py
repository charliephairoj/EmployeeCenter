#!/usr/bin/python
# -*- coding: utf-8 -*-


"""Collection of the classes that create pdf files
for an Acnowledgement. The Acknowledgement creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing 
production"""

from decimal import Decimal
from pytz import timezone
import logging

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
from reportlab.graphics.barcode import code128


logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT+'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT+'Garuda.ttf'))


logo_height = 70


class ShippingDocTemplate(BaseDocTemplate):
    
    id = 0
    company = "alinea group"
    top_padding = 150
    
    def __init__(self, filename, **kw):
        if "id" in kw: self.id = kw["id"]
        if "company" in kw: self.company = kw["company"]
        BaseDocTemplate.__init__(self, filename, **kw)
        self.addPageTemplates([self._create_page_template(template_id="main"),
                               self._create_page_template(template_id="labels", header=False)])
        
    def _create_page_template(self, template_id, header=True):
        """
        Creates a basic page template
        """
        top_padding = self.top_padding if header else 30
        frame = Frame(0, 0, 210 * mm,297 * mm, leftPadding=36, bottomPadding=30, rightPadding=36, topPadding=top_padding)
        template = PageTemplate(id=template_id, frames=[frame])
        if header:
            template.beforeDrawPage = self._create_header
        return template
    
  
    def _create_header(self, canvas, doc):
        #Draw the logo in the upper left
        
        path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/Alinea-Logo_Master.jpg"""

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
        
        
        canvas.drawString(42, 760,
                            "78/448 Moo.6 Lam Lukka Rd. Bueng Kham Phroi, Lam Lukka")
        canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
        canvas.drawString(42, 740, "+66 2 508 8681")
        #canvas.drawString(42, 730, "www.dellarobbiathailand.com")
        
        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Shipping/Receiving') 
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'Shipping#: {0}'.format(self.id))
        
        #Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = "S-{0}".format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas,x_position,740)

        
class ShippingPDF(object):
    """Class to create PO PDF"""
    
    #attributes
    document_type = "Shipping"
    
    #def methods
    def __init__(self, customer=None, products=None, shipping=None, employee=None):
        
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer  
        self.products = products
        self.shipping = shipping
        try:
            self.ack = shipping.acknowledgement
        except AttributeError as e:
            self.ack = None
        self.employee = employee
    
    
    #create method
    def create(self):
        self.filename = "Shipping-{0}.pdf".format(self.shipping.id)
        self.location = "{0}{1}".format(settings.MEDIA_ROOT,self.filename)
        #create the doc template
        try:
            company = self.shipping.acknowledgement.company
        except AttributeError as e:
            company = "alinea group"

        doc = ShippingDocTemplate(self.location, id=self.shipping.id, company=company,
                                  pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #Build the document with stories
        stories = self._get_stories()
        doc.build(stories)
        #return the filename
        return self.location
        
    def _get_stories(self):
        #initialize story array
        story = []
        #add heading and spacing
        
        #create table for supplier and recipient data
        story.append(self._create_contact_section())
        story.append(Spacer(0,20))
        #Create table for po data
        story.append(self._create_ack_section())
        story.append(Spacer(0,40))
        #Alignes the header and supplier to the left
        for a_story in story:
            a_story.hAlign = 'LEFT'
        #creates the data to hold the product information
        story.append(self._create_products_section())
        #spacer
        story.append(Spacer(0, 50))   
        story.append(self._create_signature_section())
        
        #New Page
        """
        story.append(PageBreak())
        story.append(self._create_authorization_section())
        return story
        """
        """
        story.append(NextPageTemplate('labels'))
        #New Page
        story.append(PageBreak())
        story.append(self._create_packing_labels_section())
        """
        return story
    
    def _create_customer_section(self):
        #extract supplier address
        try:
            address = self.customer.addresses.all()[0] 
        except IndexError:
            address = None
        #Create data array
        data = []
        #Add supplier name
        data.append(['Customer:', self.customer.name])
        if address:
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
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                            ('FONT', (0,0), (-1,-1), 'Garuda')])
                            #('GRID', (0,0), (-1,-1), 1, colors.black)])
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
                            #('GRID', (0,0), (-1,-1), 1, colors.black)])
        contact.setStyle(style)
        #Return table
        return contact

    def _create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        try:
            order_date, od_obj = self.outputBKKTime(self.shipping.acknowledgement.time_created, '%B %d, %Y')
            data.append(['Order Date:', order_date])
        except AttributeError as e:
            logger.info(e)
        delivery_date, dd_obj = self.outputBKKTime(self.shipping.delivery_date, '%B %d, %Y')
        data.append(['Delivery Date:', delivery_date])
        try:
            # Add the acknowledgement number
            data.append(['Acknowledgement #:', self.shipping.acknowledgement.id])
            #Adds po if exists
            if self.shipping.acknowledgement.po_id != None:
                data.append(['PO #:', self.ack.po_id])
        except AttributeError as e:
            logger.info(e)

        try:
            data.append(['Project:', self.shipping.acknowledgement.project.codename])
        except AttributeError as e:
            logger.warn(e)

        try:
            data.append(['Room:', self.shipping.acknowledgement.room.description])
        except AttributeError as e:
            logger.warn(e)

        if self.shipping.comments is not None and self.shipping.comments != '':
            data.append(['Comments', self.shipping.comments])
        #Create table
        table = Table(data, colWidths=(110, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
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
        #Create Table
        table = Table(data, colWidths=(520), repeatRows=1)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                      ('TOPPADDING', (0,0), (-1,-1), 0),
                      ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                      ('ALIGNMENT', (0,0), (-1,-1), 'CENTER')]
                           
        table.setStyle(TableStyle(style_data))
        #Return the table
        return table
    
    def _create_products_title_section(self):
        table = Table([['Product ID', 'Description', 'Qty', 'Net Weight', 'Gross Weight']], colWidths=(65, 240, 40, 90, 90))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                      ('GRID', (0,0), (-1,0), 1, colors.black),
                      #General alignment
                      ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
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
                     product.quantity,
                     u"{0} kg".format(product.net_weight),
                     u"{0} kg".format(product.gross_weight)])
        try:
            data.append([u'', self._get_fabric_table(product.item.fabric, u"   Fabric:")])
        except:
            pass
        
        # Wrap in try, in case there is no preceding item
        try:
            if product.item.is_custom_size:
                dimension_str = '   Width: {0}mm Depth: {1}mm Height: {2}mm'
                dimension_str = dimension_str.format(product.item.width, product.item.depth, product.item.height)
                data.append(['', dimension_str])
            #increase the item number
            pillows = product.item.pillows.all()
            if len(pillows) > 0:
                for pillow in pillows:
                    data.append([u'', u'   {0} Pillow'.format(pillow.type.capitalize()), pillow.quantity])
                    try:
                        data.append([u'', self._get_fabric_table(pillow.fabric.description, u'       - Fabric:'), u'',])
                    except: pass
        except AttributeError as e:
            logger.info(e)

        try:
            components = product.item.components.all()
            if len(components) > 0:
                for component in components:
                    data.append([u'', u'   {0}'.format(component.description), u'{0}'.format(component.quantity)])
        except AttributeError as e:
            logger.info(e)

        #Add comments if they exists
        if product.comments is not None and product.comments != '':
            style = ParagraphStyle(name='Normal',
                                   fontName='Garuda',
                                   fontSize=10,
                                   textColor=colors.black)
            paragraph = Paragraph(product.comments.replace('\n', '<br/>'), style)
            comments = Table([['  Comments:', paragraph]], colWidths=(60, 340))
            comments.setStyle(TableStyle([('FONT', (0,0), (-1,-1), 'Garuda'),
                                          ('FONTSIZE', (0,0), (-1, -1), 10),
                                          ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                          ('TEXTCOLOR', (0,0), (-1,-1), colors.black)]))
            data.append(['', comments, ''])
        #Get Image url and add image
        try:
            if product.item.image is not None:
                image_url = product.item.image.generate_url('', '', time=3600)
                data.append(['', self.get_image(image_url, height=100)])
        except AttributeError as e:
            logger.info(e)
            
        #Create table
        table = Table(data, colWidths=(65, 240, 40, 90, 90))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                            #Lines around content
                            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0,0), (-1,-1), 1, colors.black),
                            ('LINEBEFORE', (0,0), (0,-1), 1, colors.black),
                            ('FONT', (0,0), (-1,-1), 'Garuda'),
                            #General alignment
                            ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                            #Align description
                            ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                            ('ALIGNMENT', (3, 0), (-1, -1), 'RIGHT')]
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
                                          ('TEXTCOLOR', (0,0), (-1,-1), colors.black)]))
        return fabric_table
    
    def _create_signature_section(self, sig1='Delivery Agent', sig2='Recipient'):
        #create the signature
        signature = Table([['x', '', 'x'], [sig1, '', sig2]], colWidths=(200,100,200))
        style = TableStyle([
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
                             #('LINEABOVE', (0,0), (-1,0), 1, colors.black),
                             ('LINEBELOW', (0,0), (0,0), 1, colors.black),
                             ('LINEBELOW', (-1,0), (-1,0), 1, colors.black),
                             ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                             ('ALIGNMENT', (0,0), (-1,0), 'LEFT')])
        signature.setStyle(style)
        return signature
    
    def _create_authorization_section(self):
        
        product_data = [['', 'ID', "Description", 'Quantity']]
        for product in self.products:
            #Create the barcode
            code = "SI-{0}".format(product.id)
            barcode = code128.Code128(code, barHeight=20)
            #Add the product information to the array
            product_data.append([barcode, product.id, product.description, product.quantity])
            
        product_table = Table(product_data, colWidths=(100, 50, 300, 60))
        product_style = TableStyle([('FONTSIZE', (0,0), (-1,0), 12),
                                    ('BOTTOMPADDING', (0,0), (-1,0), 8),
                                    ('PADDING', (0,1), (-1,-1), 5),
                                    ('FONT', (0,0), (-1,-1), 'Garuda'),
                                    ('ALIGNMENT', (-1,0), (-1,-1), 'CENTER'),
                                    ('VALIGN', (0,1), (-1,-1), 'MIDDLE'),
                                    ('TEXTCOLOR', (0,0), (-1,-1), colors.black)])
        product_table.setStyle(product_style)
        data = Table([['Authorization'], 
                      [Spacer(0, 25)],
                      [u'Customer: {0}'.format(self.customer.name)],
                      [Spacer(0, 10)], 
                      [product_table], 
                      [Spacer(0, 25)],
                      [self._create_signature_section('Department Head', 'Manager')]],
                     colWidths=(520))
        style = TableStyle([('FONTSIZE', (0,0), (-1, 0), 16),
                            ('PADDING', (0,0), (-1,-1), 0),
                            ('ALIGNMENT', (0, 0), (0, 0), 'CENTER'),
                            ('FONT', (0,0), (0, 0), 'Tahoma'),
                            ('FONT', (0,1), (0,2), 'Garuda'),
                            ('FONTSIZE', (0,2), (0,2), 14),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.black)
                             
                             ])
        data.setStyle(style)
        
        return data
    
    def _create_packing_label(self, product):
        """
        Creates an individual packing label as a 
        Table.
        """
        logo_path = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"
        logo = self.get_image(logo_path, width=200)
        
        
        #Add the product information to the array
        #print product.product.image9
        description_data = [[logo],
                            [product.description]]
        
        if product.item.image:
            image_url = product.item.image.generate_url('', '', time=3600)
            description_data.append([self.get_image(image_url, height=75)])
        
        description_table = Table(description_data, colWidths=(360))
        description_style = TableStyle([('FONTSIZE', (0,0), (-1, -1), 16),
                                        ('BOTTOMPADDING', (0, 0), (0, 1), 10),
                                        ('FONT', (0,0), (-1,-1), 'Garuda'),
                                        ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                                        ('VALIGN', (0, 0), (0, 0), 'TOP'),
                                        ('VALIGN', (0, 1), (-1,-1), 'MIDDLE'),
                                        ('TEXTCOLOR', (0,0), (-1,-1), colors.black)])
        description_table.setStyle(description_style)
        
        code = "DRAI-{0}".format(product.item.id)
        barcode = code128.Code128(code, barHeight=20)
        try:
            project = u"Project: {0}".format(self.ack.project.codename)
        except AttributeError:
            project = ""
            
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=12,
                               leading=16,
                               textColor=colors.black)
        customer_paragraph = Paragraph(u"Customer: {0}".format(self.ack.customer.name), style)
        code_data = [[barcode],
                     [code],
                     ["Ack#: {0}".format(self.ack.id)],
                     [customer_paragraph],
                     [project],
                     ["Qty: {0}".format(product.quantity)]]
        
        code_table = Table(code_data, colWidths=(150))
        code_style = TableStyle([('FONTSIZE', (0, 1), (0 , 1), 8), #Font size for code
                                 ('FONTSIZE', (0, 2), (0 , -2), 12), #Font size for order data
                                 ('FONTSIZE', (0, -1), (0, -1), 16), #Font size for quantity
                                 #Set code next to barcode
                                 ('BOTTOMPADDING', (0, 0), (0, 0), 0),
                                 ('TOPPADDING', (0, 1), (0, 1), 0),
                                 
                                 ('BOTTOMPADDING', (0, 1), (0, 1), 15), #Margin after barcode and code
                                 
                                 ('BOTTOMPADDING', (0, -2), (0, -2), 25), #Margin after order data
                                 
                                 ('FONT', (0,0), (-1,-1), 'Garuda'), #Font for all text
                                 ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'), #Alignment for barcode, code, and qty
                                 ('ALIGNMENT', (0, 2), (0,-2), 'LEFT'), #Alignment for order data
                                 ('VALIGN', (0, 1), (0, 1), 'TOP'),
                                 ('VALIGN', (0, 2), (0, -1), 'MIDDLE'),
                                 ('BOTTOMPADDING', (0, -1), (0, -1), 10), #Toppadding for quantity box
                                 ('TOPPADDING', (0, -1), (0, -1), 10), #Bottompadding for quantity box
                                 ('BOX', (0, -1), (0, -1), 1, colors.black),
                                 ('TEXTCOLOR', (0, 0), (-1, -1), colors.black)])
        code_table.setStyle(code_style)
        
        label_data = [[description_table, code_table]]
        label = Table(label_data, colWidths=(360, 160))
        label_style = TableStyle([('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                  ('BOX', (0, 0), (-1, -1), 1, colors.black)])
        label.setStyle(label_style)
        
        return label
    
    def _create_packing_labels_section(self):
        
        product_data = [[self._create_packing_label(product)] for product in self.products]
        
        product_table = Table(product_data, colWidths=(500))
        product_style = TableStyle([('ALIGNMENT', (0,0), (-1,-1), 'CENTER')])
        product_table.setStyle(product_style)
    
        return product_table
        
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


    