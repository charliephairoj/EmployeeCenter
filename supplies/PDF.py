"""PDF classes for various collection of supplies"""
from decimal import Decimal
from pytz import timezone

from django.conf import settings
from django.db import models
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code39
from reportlab.graphics.barcode import code128

from supplies.models import Supply

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


