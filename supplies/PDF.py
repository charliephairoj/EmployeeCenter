"""PDF classes for various collection of supplies"""
from decimal import *
import decimal
from pytz import timezone
import logging
from copy import deepcopy

from django.conf import settings
from django.db import models
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfdoc
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code128

from supplies.models import Supply, Product

logger = logging.getLogger(__name__)
pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class BaseSupplyDocTemplate(BaseDocTemplate):

    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.addPageTemplates(self._create_page_template())

    def _create_page_template(self):
        """Creates the template used for each page"""
        frame = Frame(0, 0, 210 * mm, 297 * mm, leftPadding=36,
                      bottomPadding=30, rightPadding=36,
                      topPadding=150)
        template = PageTemplate('Normal', [frame])
        template.beforeDrawPage = self._create_header
        return template

    def _create_header(self, canvas, doc):
        """Creates the Header for the document"""
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
        canvas.drawString(42, 740, "+66 2 998 7490")
        canvas.drawString(42, 730, "www.dellarobbiathailand.com")

        #Create The document type and document number
        canvas.setFont("Helvetica", 16)
        canvas.drawRightString(550, 800, 'Prop List')


class PropsPDF(object):

    @classmethod
    def create(cls):
        obj = cls()
        obj.filename = "Prop-List.pdf"
        obj.location = "{0}{1}".format(settings.MEDIA_ROOT, obj.filename)
        #create the doc template
        doc = BaseSupplyDocTemplate(obj.location)
        #Build the document with stories
        stories = obj._get_stories()
        doc.build(stories)
        #return the filename
        return obj.location

    def _get_stories(self):
        story = []
        story.append(self._create_prop_section())
        return story

    def _create_prop_section(self):
        data = []
        data.append([self._create_prop_title()])


        for prop in Supply.objects.filter(type='prop').order_by('reference'):
            data.append([self._create_prop_item(prop)])

        table = Table(data, colWidths=(490), repeatRows=1)
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

    def _create_prop_title(self):
        titles = ['Example', 'ID', 'Barcode', 'Reference #', 'Unit Price(Baht)']
        table = Table([titles], colWidths=(70, 50, 100, 100, 100,))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.CMYKColor(black=60)),
                      ('GRID', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    def _create_prop_item(self, prop):
        data = [self._get_image(prop.image.generate_url(), width=70),
                prop.id, 
                code128.Code128("Prop-{0}".format(prop.id), barHeight=20),
                prop.reference,
                float(prop.cost)*5.07]
        table = Table([data], colWidths=(70, 50, 100, 100, 100))
        style_data = [('TEXTCOLOR', (0, 0), (-1, -1),
                       colors.CMYKColor(black=60)),
                      ('GRID', (0, 0), (-1, 0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
                      ('VALIGN', (0, 0), (-1, -1), 'TOP')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table

    #helps change the size and maintain ratio
    def _get_image(self, path, width=None, height=None):
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
        if width != None and height == None:
            ratio = float(imgHeight) / float(imgWidth)
            newHeight = ratio * width
            newWidth = width
        elif height != None and width == None:
            ratio = float(imgWidth) / float(imgHeight)
            newHeight = height
            newWidth = ratio * height

        return Image(path, width=newWidth, height=newHeight)


pdfdoc.PDFCatalog.OpenAction = """<</S/JavaScript/JS(this.print\({bUI:false,bSilent:true,bShrinkToFit:true}\);
this.close(SaveOptions.DONOTSAVECHANGES);)>>"""

class SupplyPDF():
    name_map = {'id': 'id',
                'description': 'description',
                'quantity': 'quantity',
                'to_buy': 'to_buy'}
    supplies = None
    layout_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                    ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                    ('ALIGNMENT', (-3,0), (-1,-1), 'RIGHT'),
                    ('TOPPADDING', (0,0), (-2,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-2,-1), 3),
                    ('LEFTPADDING', (0,0), (-2,-1), 6),
                    ('RIGHTPADDING', (0,0), (-2,-1), 6),
                    ('TOPPADDING', (-1,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (-1,0), (-1,-1), 0),
                    ('LEFTPADDING', (-1,0), (-1,-1), 0),
                    ('RIGHTPADDING', (-1,0), (-1,-1), 0),
                    ('FONTSIZE', (0,0), (-1,-1), 10)]
                    
    details_style = [#('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGNMENT', (0,0), (0,-1), 'LEFT'),
                    ('ALIGNMENT', (-3,0), (-1,-1), 'RIGHT'),
                    ('TOPPADDING', (0,0), (-1,-1), 3),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 3 ),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('FONTSIZE', (0,0), (-1,-1), 10)]
                    
    running_total = 0
    
    def __init__(self, *args, **kwargs):
        self.filename = kwargs['filename']
        self.supplies = Supply.objects.raw("""WITH weekly_average as (
                        SELECT s.id as id, sum(sl.quantity) as week_total
                        FROM supplies_log as sl
                        INNER JOIN supplies_supply as s
                        ON s.id = sl.supply_id
                        GROUP BY s.id, sl.action, date_trunc('week', log_timestamp)
                        HAVING (date_trunc('week', log_timestamp) > NOW() - interval '4 weeks'
                        AND sl.action = 'SUBTRACT'))
                        SELECT s.id, s.description, s.quantity, 
                        (SELECT round(avg(week_total), 2) FROM weekly_average WHERE id = s.id) as to_buy
                        FROM supplies_supply as s
                        WHERE (id in (SELECT id from weekly_average WHERE id = s.id)
                        OR id in (SELECT supply_id FROM supplies_log))
                        AND s.quantity < ((SELECT avg(week_total) FROM weekly_average WHERE id = s.id) * 2)
                        ORDER BY s.description""", translations=self.name_map)

    def create(self):
        doc = SimpleDocTemplate(self.filename, 
                                pagesize=landscape(A4), 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        stories.append(self._create_supply_table())
        doc.build(stories)
        
    def _create_supply_table(self):
        subtable = Table([['Supplier',
                          'Cost', 
                          'Units',
                          'Total']], colWidths=(175, 55, 55, 115))
        subtable.setStyle(TableStyle(self.details_style))
        data = [['ID', 'Description', 'Qty', 'Qty to Buy', subtable]]
        for supply in self.supplies:
            
            style = ParagraphStyle(name='Normal',
                                   fontName='Tahoma',
                                   leading=12,
                                   wordWrap='CJK',
                                   allowWidows=1,
                                   allowOrphans=1,
                                   fontSize=10,
                                   textColor=colors.CMYKColor(black=60))
            description = Paragraph(supply.description,
                                  style)
                                  
            data.append([supply.id,
                         description,
                         supply.quantity,
                         "{0} {1}".format(supply.to_buy, supply.units),
                         self._create_suppliers_table(supply, supply.to_buy)])
        data.append(['', '', '', 'Total', "{0:f}".format(self.running_total)])
        table = Table(data, colWidths=(50, 225, 55, 75, 405))
        table.setStyle(TableStyle(self.layout_style))
        return table
    
    def _create_suppliers_table(self, supply, quantity):
        data = []
        best = ()
        for index, product in enumerate(Product.objects.filter(supply=supply)):
            unit_cost = self._get_unit_cost(product)
            
            if best == ():
                best = (unit_cost, index, product)
            elif unit_cost < best[0]:
                best = (unit_cost, index, product)
                                           
            data.append([product.supplier.name,
                         product.cost,
                         product.purchasing_units,
                         self._get_total_str(supply, product, quantity)])
        
        table = Table(data, colWidths=(180, 55, 55, 115))
        
        #Append style for best price
        style = deepcopy(self.details_style)
        style.append(('FONTNAME', (0,best[1]), (-1,best[1]), 'Helvetica-Bold'))
        table.setStyle(TableStyle(style))
        
        #calculate total
        try:
            self.running_total += (quantity // best[2].quantity_per_purchasing_unit) * best[2].cost
        except Exception:
            pass
            
        return table
        
    def _get_total_str(self, supply, product, quantity):
        if product.purchasing_units != supply.units:
            if quantity <= product.quantity_per_purchasing_unit:
                total_cost = product.cost
            else:
                try:
                    total_cost = (quantity / product.quantity_per_purchasing_unit) * product.cost
                except Exception as e:
                    print product.quantity_per_purchasing_unit
                    print ""
        else: 
            total_cost = quantity * product.cost
        
        if not product.quantity_per_purchasing_unit:
            product.quantity_per_purchasing_unit = 1
            product.save()
            #raise ValueError("Value should not be {0}".format(product.quantity_per_purchasing_unit))
        
        
        logger.debug("{2} {0} : {1}".format(quantity, product.quantity_per_purchasing_unit, product.supply.description))
        try:
            buying_qty = (quantity // product.quantity_per_purchasing_unit)
        except decimal.InvalidOperation:
            buying_qty = quantity
            
        buying_qty = buying_qty if buying_qty > 0 else 1
        total_str = "{0:f} for {1} {2}".format(total_cost, 
                                       buying_qty,
                                       product.purchasing_units)
        return total_str
        
    def _get_unit_cost(self, product):
        try:
            unit_cost =  product.cost / product.quantity_per_purchasing_unit
        except TypeError as e:
            unit_cost = product.cost
            
        try:
            if product.supplier.discount:
                unit_cost = unit_cost - ((product.supplier.discount/Decimal('100')) * unit_cost)
        except Exception as e:
            print e
            print "\n"
            
        return unit_cost
