# !/usr/bin/python
# -*- coding: utf-8 -*-

"""
Collection of the classes that create pdf files
for an Acnowledgement. The Acknowledgement creates
an order confirmation to be used for the office and
for customers. The production pdf is created to be
use by the production team and the office overseeing
production
"""

from decimal import Decimal
import logging
import re
import pytz
from pytz import timezone

from django.conf import settings
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import *
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128


logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class PODocTemplate(BaseDocTemplate):
    id = 0
    top_padding = 150

    def __init__(self, filename, **kw):
        if "id" in kw:
            self.id = kw["id"]
        if "revision" in kw:
            self.revision = kw['revision']
        if "revision_date" in kw:
            self.revision_date = kw['revision_date']
            
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
        # Draw the logo in the upper left
        path = """https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg"""
        
        # Read image from link
        img = utils.ImageReader(path)
        
        # Get Size
        img_width, img_height = img.getSize()
        new_width = (img_width * 30) / img_height
        canvas.drawImage(path, 42, 780, height=30, width=new_width)

        # Add Company Information in under the logo
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorCMYK(0, 0, 0, 60)
        canvas.drawString(42, 760,
                          "8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka")
        canvas.drawString(42, 750, "Pathum Thani, Thailand, 12150")
        canvas.drawString(42, 740, "T: +66 2 998 7490")
        canvas.drawString(42, 730, "F: +66 2-997-3361")
        canvas.drawString(42, 720, "www.dellarobbiathailand.com")

        # Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Purchase Order')
        canvas.setFont("Helvetica", 12)
        canvas.drawRightString(550, 780, 'PO# : {0}'.format(self.id))

        # Create a barcode from the id
        canvas.setFillColorCMYK(0, 0, 0, 1)
        code = 'PO-{0}'.format(self.id)
        barcode = code128.Code128(code, barHeight=20, barWidth=0.5 * mm)
        x_position = 570 - barcode.width
        # drawOn puts the barcode on the canvas at the specified coordinates
        barcode.drawOn(canvas, x_position, 750)
        
        # Create the revision
        if self.revision:
            if self.revision_date:
                msg = u"Revision: {0}, # {1}"
                revision_str = msg.format(self.revision_date.strftime('%B %d, %Y'),
                                          self.revision)
            else:
                msg = u'Revision: # {0}'
                revision_str = msg.format(self.revision)
                
            canvas.setFillColorCMYK(0, 0, 0, 1)
            canvas.setFont("Helvetica", 12)
            canvas.drawRightString(550, 730, revision_str)


class PurchaseOrderPDF():
    """Class to create PO PDF"""
    document_type = "Purchase_Order"

    def __init__(self, supplier=None, items=None, po=None, attention=None,
                 misc=None, connection=None, revision=None, revision_date=None,
                 filename=None):
        # Set Defaults
        self.width, self.height = A4

        self.supplier = supplier
        self.supplies = items
        self.po = po
        self.employee = self.po.employee
        self.attention = attention
        self.revision = revision
        self.revision_date = revision_date
        
        self.filename = "%s-%s.pdf" % (self.document_type, self.po.id)

    def create(self):
        self.location = "{0}/{1}".format(settings.MEDIA_ROOT, self.filename)
        # Create the doc template
        doc = PODocTemplate(self.location, id=self.po.id, pagesize=A4,
                            leftMargin=36, rightMargin=36, topMargin=36,
                            revision=self.revision, revision_date=self.revision_date)
        # Build the document with stories
        doc.build(self._get_stories())
        # return the filename
        return self.location

    def _get_stories(self):
        # initialize story array
        story = []
        # create table for supplier and recipient data
        story.append(self.__create_contact_section())
        story.append(Spacer(0, 20))
        # Create table for po data
        story.append(self.__create_po_section())
        story.append(Spacer(0, 40))
        # Alignes the header and supplier to the left
        for aStory in story:
            aStory.hAlign = 'LEFT'
        # creates the data to hold the supplies information
        story.append(self.__create_supplies_section())
        # spacer
        story.append(Spacer(0, 50))
        story.append(self._create_signature_section())
        # return the filename
        return story

    def __create_supplier_section(self):
       
        # Create data array
        data = []
        # Add supplier name
        data.append(['Supplier:', self.supplier.name])
        
        try:
            # extract supplier address
            address = self.supplier.addresses.all()[0]
            # add supplier address data
            data.append(['', address.address1])
            if address.address2:
                if address.address2.strip() != "":
                    data.append(['', address.address2])
    
            data.append(['', u"{0}, {1}".format(address.city, address.territory)])
            data.append(['', u"{0} {1}".format(address.country, address.zipcode)])
        except Exception as e:
            logger.warn(e)
            
        if self.supplier.telephone:
            data.append(['', "T: {0}".format(self.supplier.telephone)])
        if self.supplier.fax:
            data.append(['', "F: {0}".format(self.supplier.fax)])
        if self.supplier.email:
            data.append(['', "E: {0}".format(self.supplier.email)])
        try:
            contact = self.supplier.contacts.get(primary=True)
            data.append(['Contact:', u"{0}".format(contact.name)])
            data.append(['', u"{0}".format(contact.email)])
            data.append(['', u"{0}".format(contact.telephone)])
        except Exception as e:
            logger.warn(e)
            
        # Create Table
        table = Table(data, colWidths=(60, 200))
        # Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Garuda')])
        table.setStyle(style)
        # Return the Recipient Table
        return table

    def __create_recipient_section(self):
        # Create data array
        data = []
        # Add Employee Name
        ship_str = u"Dellarobbia Thailand"
        data.append(['Ship To:', ship_str])
        # Add Company Data
        data.append(['', '8/10 Moo 4 Lam Luk Ka Rd. Soi 65'])
        data.append(['', 'Lam Luk Ka, Pathum Thani'])
        data.append(['', 'Thailand 12150'])
        data.append(['', u'C: {0} {1}'.format(self.employee.first_name,
                                              self.employee.last_name)])
        data.append(['', u'E: {0}'.format(self.employee.email)])
        
        try:
            if self.employee.employee.telephone:
                if self.employee.employee.telephone != '':
                    data.append(['', u'T: {0}'.format(self.employee.employee.telephone)])
        except Exception as e:
            logger.warn(e)
            
        # Create Table
        table = Table(data, colWidths=(50, 150))
        # Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Helvetica')])
        table.setStyle(style)
        # Return the Recipient Table
        return table

    def __create_contact_section(self):
        """Create the Contact Table."""
        t1 = self.__create_supplier_section()
        t2 = self.__create_recipient_section()
        # create table for supplier and recipient data
        contact = Table([[t1, t2]], colWidths=(280, 200))
        # Create Style and apply
        style = TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP')])
        contact.setStyle(style)
        # Return table
        return contact

    def __create_po_section(self):
        # Create data array
        data = []
        # Add Data
        data.append(['Terms:', self._get_payment_terms()])
        data.append(['Currency:', self._get_currency()])
        order_date = self._outputBKKTime(self.po.order_date, '%B %d, %Y')
        data.append(['Order Date:', order_date])
        if self.po.receive_date:
            delivery_date = self._outputBKKTime(self.po.receive_date, '%B %d, %Y')
            data.append(['Delivery Date:', delivery_date])

        if self.po.project:
            project = self.po.project.codename
            
            if self.po.room:
                project += u", {0}".format(self.po.room.description)
                
            if self.po.phase:
                project += u", {0}".format(self.po.phase.description)
                
            data.append(['Project:', project])
        
        if self.po.comments:
            data.append(['Comments:', self._format_string_to_paragraph(self.po.comments)])

        # Create table
        table = Table(data, colWidths=(60, 200))
        # Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                            ('TOPPADDING', (0, 0), (-1, -1), 1),
                            ('TEXTCOLOR', (0, 0), (-1, -1),
                             colors.CMYKColor(black=60)),
                            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                            ('FONT', (0, -1), (-1, -1), 'Garuda')])
        table.setStyle(style)
        # Return Table
        return table

    def __create_supplies_section(self):
        # Create data array
        data = []
        # Add Column titles
        data = [['Item No.', 'Ref', 'Description', 'Units',
                 'Qty', 'Unit Price', 'Total']]
        i = 1
        # iterate through the array
        for supply in self.supplies:
            # add the data
            discount_perc = (Decimal(supply.discount) / Decimal('100'))
            calculated_unit_cost = supply.unit_cost - (supply.unit_cost * discount_perc)
            logger.debug('unit cost: {0:,}'.format(calculated_unit_cost))
            data.append([i,
                         self._get_reference(supply),
                         self._get_description(supply),
                         self._format_string_to_paragraph(supply.supply.purchasing_units),
                         "{0:,.2f}".format(supply.quantity),
                         "{0:,.3f}".format(calculated_unit_cost),
                         "{0:,.2f}".format(supply.total)])
                         
            # increase the item number
            i += 1
            
        # add a shipping line item if there is a shipping charge
        if self.po.shipping_type != "none":
            shipping_description, shipping_amount = self._get_shipping()
            # Add to data
            data.append(['', '', shipping_description,
                         '', '', '',
                         "{0:,}".format(round(self.po.shipping_amount, 2))])
        # Get totals data and style
        totals_data, totals_style = self._get_totals()
        # merge data
        data += totals_data
        
        # Add section for deposit
        if int(self.po.deposit) != 0:
            if self.po.deposit_type == "percent":
                deposit = Decimal(str(round((Decimal(self.po.deposit) / Decimal('100')) * self.po.grand_total, 2)))
                deposit_title = "{0}%".format(self.po.deposit)
            elif self.po.deposit_type == "amount":
                deposit = "{0:,.2f}".format(self.po.deposit)
                deposit_title = ""
                
            data += [['',
                      '',
                      '',
                      '',
                      '',
                      'Deposit {0}'.format(deposit_title),
                      deposit]]
            
        # Create Table
        table = Table(data, colWidths=(40, 84, 230, 55, 40, 50, 65))
        # Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1), colors.CMYKColor(black=60)),
                      ('LINEABOVE', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      # line under heading
                      ('LINEBELOW', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                      ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),
                      ('ALIGNMENT', (5, 0), (5, -1), 'CENTER'),
                      # align headers from description to total
                      ('ALIGNMENT', (3, 0), (-1, 0), 'CENTER'),
                      # align totals to the right
                      ('ALIGNMENT', (-1, 1), (-1, -1), 'RIGHT'),
                      ('ALIGNMENT', (-1, 0), (-1, 0), 'RIGHT'),
                      ('FONT', (0, 0), (-1, -1), 'Garuda'),
                      ('LEFTPADDING', (2, 0), (2, -1), 10),
                      ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                      ('VALIGN', (0, 1), (-1, -1), 'TOP')]
        style_data += totals_style
        
        # Add style if there is a deposit
        if int(self.po.deposit) != 0:
            line_color = colors.CMYKColor(black=60)
            style_data.append(('LINEABOVE', (-3, -1), (-1, -1), 1, line_color))
            
        # Create and apply table style
        style = TableStyle(style_data)
        table.setStyle(style)
        # Return the table
        return table

    def _create_signature_section(self):
        signature = Table([['x', '', 'x'], ['Purchasing Agent', '', 'Manager']],
                          colWidths=(200, 100, 200))
                          
        dark_grey = colors.CMYKColor(black=60)
        style = TableStyle([('TEXTCOLOR', (0, 0), (-1, -1), dark_grey),
                            ('LINEBELOW', (0, 0), (0, 0), 1, dark_grey),
                            ('LINEBELOW', (-1, 0), (-1, 0), 1, dark_grey),
                            ('ALIGNMENT', (0, -1), (-1, -1), 'CENTER'),
                            ('ALIGNMENT', (0, 0), (-1, 0), 'LEFT')])
        # spacer
        signature.setStyle(style)
        return signature

    def _get_payment_terms(self):
        # determine Terms String
        # based on term length
        if self.po.terms == 0:
            terms = "Payment On Delivery"
        elif self.po.terms < 0:
            terms = "Credit"
        else:
            terms = "{0} Days".format(self.po.terms)
        # return term
        return terms

    def _get_currency(self):
        # Determine currency string
        # based on currency
        if self.po.currency == "EUR":
            currency = "Euro(EUR)"
        elif self.po.currency == "THB":
            currency = "Thai Baht(THB)"
        elif self.po.currency == "USD":
            currency = "US Dollar(USD)"
        # return currency
        return currency

    def _get_description(self, supply):
        # Set description
        description = supply.description.replace('\n', '<br/>')
        
        if supply.comments:
            msg_template = u"<br/>[Comments: {0}]"
            description += msg_template.format(supply.comments.replace('\n', '<br/>'))
            
        # If there is a discount then append
        # original price string
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=10,
                               textColor=colors.CMYKColor(black=60))
                               
        if supply.discount > 0:
            supply.supply.supplier = self.po.supplier
            description += u" (discounted {0}% from {1})".format(supply.discount,
                                                                 supply.supply.cost)
                                                                 
        # return description
        return Paragraph(description, style)
        
    def _get_reference(self, supply):
        # Set reference
        try:
            reference = supply.reference
        except AttributeError:
            reference = supply.supply.reference or u""
            
        # If there is a discount then append
        # original price string
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=10,
                               textColor=colors.CMYKColor(black=60))
     
        # return description
        return Paragraph(reference, style)

    def _get_shipping(self):
        # set the description
        if self.po.shipping_type == "air":
            description = "Air Freight"
        elif self.po.shipping_type == "sea":
            description = "Sea Freight"
        elif self.po.shipping_type == "ground":
            description = "Ground Freight"
        # return descript and amount
        return description, self.po.shipping_amount

    def _get_totals(self):
        # Create data and style array
        data = []
        style = []
        # calculate the totals
        # what to do if there is vat or discount
        if self.po.vat != 0 or self.po.discount != 0:
            # get subtotal and add to pdf
            subtotal = Decimal(self.po.subtotal)
            data.append(['', '', '', '', '', 'Subtotal', "{0:,.2f}".format(subtotal)])
            # add discount area if discount greater than 0
            if self.po.discount != 0:
                discount = subtotal * (Decimal(self.po.discount) / Decimal('100'))
                dis_title = 'Discount {0}%'.format(self.po.discount)
                dis_str = "{0:,.2f}".format(discount)
                data.append(['', '', '', '', '', dis_title, dis_str])
                
            # add vat if vat is greater than 0
            if self.po.vat != 0:
                if self.po.discount != 0:
                    
                    # append total to pdf
                    data.append(['',
                                 '',
                                 '',
                                 '',
                                 '',
                                 'Total',
                                 "{0:,.2f}".format(self.po.total)])
                    
                # calculate vat and add to pdf
                vat = Decimal(self.po.total) * (Decimal(self.po.vat) / Decimal('100'))
                data.append(['',
                             '',
                             '',
                             '',
                             '',
                             'Vat {0}%'.format(self.po.vat), "{0:,.2f}".format(vat)])
        
        # Append the grand total
        data.append(['',
                     '',
                     '',
                     '',
                     '',
                     'Grand Total', "{0:,.2f}".format(self.po.grand_total)])
        
        # adjust the style based on vat and discount
        # if there is either vat or discount
        if self.po.vat != 0 or self.po.discount != 0:
            # if there is only vat or only discount
            if self.po.vat != 0 and self.po.discount != 0:
                style.append(('LINEABOVE', (0, -5), (-1, -5), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2, -5), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -5), (-1, -1), 1))
            # if there is both vat and discount
            else:
                style.append(('LINEABOVE', (0, -3), (-1, -3), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2, -3), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -3), (-1, -1), 1))
                
        # if there is no vat or discount
        else:
            if int(self.po.deposit) == 0:
                style.append(('LINEABOVE', (0, -1), (-1, -1), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-1, -1), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -1), (-1, -1), 1))
            elif int(self.po.deposit) > 0:
                style.append(('LINEABOVE', (0, -2), (-1, -2), 1,
                              colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2, -1), (-1, -1), 'RIGHT'))
                style.append(('BOTTOMPADDING', (-2, -1), (-1, -1), 1))
        style.append(('ALIGNMENT', (-2, -3), (-1, -1), 'RIGHT'))
        # Return data and style
        return data, style

    def _format_string_to_paragraph(self, string):
        """
        Changes the string to a paragraph
        """
        super_re = re.compile('\^(\d+)')
        string = super_re.sub('<super>\g<1></super>', string)
        
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=10,
                               alignment=TA_CENTER,
                               textColor=colors.CMYKColor(black=60))
        
        # return description
        return Paragraph(string, style)
        
    # helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None):
        img = utils.ImageReader(path)
        imgWidth, imgHeight = img.getSize()
        if width is not None and height is None:
            ratio = imgHeight / imgWidth
            newHeight = ratio * width
            newWidth = width
        elif height is not None and width is None:
            ratio = imgWidth / imgHeight
            newHeight = height
            newWidth = ratio * height
        return Image(path, width=newWidth, height=newHeight)
    
    def _outputBKKTime(self, dateTimeObj, fmt):
        """
        The function accepts the datetime object
        and the preferred output str format to return
        the datetime as. This function then converts
        from the current utc(preferred) to the 'Asia/Bangkok'
        timezone
        """
        bkkTz = timezone('Asia/Bangkok')
        try:
            bkkDateTime = dateTimeObj.astimezone(bkkTz)
        except ValueError:
            utctime = bkkTz.localize(dateTimeObj)
            bkkDateTime = utctime.astimezone(bkkTz)
            
        return bkkDateTime.strftime(fmt)
        
        
class AutoPrintCanvas(canvas.Canvas):
    
    def __init__(self, *args, **kwargs):
        
        canvas.Canvas.__init__(self, *args, **kwargs)
        
        script = '<</S/JavaScript/JS(this.print\({bUI:true,bSilent:false,bShrinkToFit:true}\);)>>'
        
        self._doc.Catalog.OpenAction = script
        

class InventoryPurchaseOrderPDF(PurchaseOrderPDF):
        
    def create(self):
        self.filename = "%s-%s-auto.pdf" % (self.document_type, self.po.id)
        
        self.location = "{0}/{1}".format(settings.MEDIA_ROOT, self.filename)
        
        # create the doc template
        doc = PODocTemplate(self.location, id=self.po.id, pagesize=A4,
                            leftMargin=36, rightMargin=36, topMargin=36,
                            revision=self.revision, revision_date=self.revision_date)
                             
        # Build the document with stories
        doc.build(self._get_stories(), canvasmaker=AutoPrintCanvas)
        
        # return the filename
        return self.location

        
