import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from decimal import *

from django.conf import settings
from django.core.exceptions import *
from django.db.models import Q
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_LEFT

from contacts.models import Supplier
from supplies.models import Supply
from projects.models import Project
from po.models import PurchaseOrder, Item


django.setup()

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class SupplyPDF(object):
   
    table_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                   ('FONT', (0,0), (-1,-1), 'Garuda'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (-1,-1), 'LEFT'),
                   ('ALIGNMENT', (2,0), (2,-1), 'CENTER'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('FONTSIZE', (0,0),(-1,-1), 10)]
        
    def __init__(self, *args, **kwargs):
        
        self.queryset = Supply.objects.raw(
            """
            SELECT DISTINCT id, description, type, image_id
            FROM supplies_supply AS s
            WHERE (s.id IN (SELECT supply_id from po_item)
                   OR s.id IN (SELECT supply_id FROM supplies_log where action != 'PRICE CHANGE'))
            AND s.type != 'Wool'
            AND s.type != 'Acrylic'
            AND s.type != 'fabric'
            AND s.type != 'prop'
            AND s.type != 'foam'
            AND s.description not ilike '%%test%%'
            ORDER BY s.type, s.description
            """
        )
        super(SupplyPDF, self).__init__(*args, **kwargs)
        
    def create(self):
        doc = SimpleDocTemplate('SupplyBook.pdf', 
                                pagesize=A4, 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        #logger.debug("Processing {0} supplies".format(self.queryset.count()))
        
        stories.append(self._create_supply_section())
        
        for story in stories:
            story.hAlign = "CENTER"
            
        doc.build(stories)
        
    def _create_supply_section(self):
        """
        Creates the higher level order section
        
        This section will also contain a subsection of 
        the items for this order
        """     
        data = [["PREVIEW", 'ID', "BARCODE", "TYPE", "DESCRIPTION"]]   
        
        for supply in self.queryset:
            
            try:
                image = self.get_image(supply.image.generate_url(), width=100)
            except AttributeError:
                image = ""
            except IOError:
                image = "Image NA"
                
            data.append([image,
                         supply.id,
                         code128.Code128("DRS-{0}".format(supply.id), 
                                         barHeight=20),
                         supply.type, 
                         self._prepare_text(supply.description)])
       
            
        table = Table(data, colWidths=[110, 50, 100, 75, 200], repeatRows=1)
        table.setStyle(TableStyle(self.table_style))
            
        return table
    

    def _prepare_text(self, description, font_size=8):
        
        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               alignment=TA_LEFT,
                               fontName='Garuda',
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
    
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
        
    
if __name__ == "__main__":
    pdf = SupplyPDF()
    pdf.create()