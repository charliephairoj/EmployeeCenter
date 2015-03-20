import sys, os, django
sys.path.append('/Users/Charlie/Sites/employee/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'EmployeeCenter.settings'
import logging
from decimal import *

from django.conf import settings
from django.core.exceptions import *
from reportlab.lib import colors, utils
from reportlab.lib.units import mm
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from contacts.models import Supplier
from supplies.models import Supply
from projects.models import Project
from po.models import PurchaseOrder, Item


django.setup()

logger = logging.getLogger(__name__)

pdfmetrics.registerFont(TTFont('Tahoma', settings.FONT_ROOT + 'Tahoma.ttf'))
pdfmetrics.registerFont(TTFont('Garuda', settings.FONT_ROOT + 'Garuda.ttf'))


class ProjectPDF():
    queryset = Project.objects.filter(purchaseorder__isnull=False).order_by('codename')
   
    item_heading_style = [('INNERGRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                          ('LINERIGHT', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                          ('VALIGN', (0,0), (-1,-1), 'TOP'),
                          ('FONT', (0,0), (-1,-1), 'Tahoma'),
                          ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                          ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                          ('PADDING', (0,1), (-1,-1), 0),
                          ('FONTSIZE', (0,0),(-1,-1), 10)]
    item_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                  ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                  ('FONT', (0,0), (-1,-1), 'Garuda'),
                  ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                  ('ALIGNMENT', (0,0), (-1,-1), 'CENTER'),
                  ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                  ('ALIGNMENT', (-1,1), (-1, -1), 'RIGHT'),
                  ('PADDING', (0, 0), (-1,-1), 2),
                  ('FONTSIZE', (0,0),(-1,-1), 8),
                  ('SPAN', (0, 1), (0, -2)),
                  ('SPAN', (0, -1), (-2, -1))]
    order_style = [('GRID', (0, 0), (-1,-1), 1, colors.CMYKColor(black=60)),
                   ('VALIGN', (0,0), (-1,-1), 'TOP'),
                   ('FONT', (0,0), (-1,-1), 'Tahoma'),
                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                   ('ALIGNMENT', (0,0), (4 ,-1), 'CENTER'),
                   ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                   ('PADDING', (0,0), (-1,-1), 0),
                   ('LEFTPADDING', (4,0), (-1, -1), 0),
                   ('TOPPADDING', (4,0), (-1, -1), 0),
                   ('BOTTOMPADDING', (4,0), (-1, -1), 0),
                   ('FONTSIZE', (0,0),(-1,0), 10),
                   ('FONTSIZE', (0, 1),(-3,-1), 6)]                    
    item_cols_widths = (50, 110, 50, 30, 50)
    
    project_title_style = ParagraphStyle(name="Normal",
                                         fontName='Garuda',
                                         alignment=1,
                                         fontSize=16)
        
    def create(self):
        doc = SimpleDocTemplate('Projects.pdf', 
                                pagesize=A4, 
                                leftMargin=12, 
                                rightMargin=12, 
                                topMargin=12, 
                                bottomMargin=12)
        stories = []
        
        logger.debug("Processing {0} orders".format(self.queryset.count()))
        
        index = 0
        for project in self.queryset:
            if (index > 0):
                
                stories.append(PageBreak())
            
            index += 1
                
            stories.append(Paragraph(project.codename, self.project_title_style))
            stories.append(Spacer(0, 20))
            stories.append(self._create_project_section(project))
        
        for story in stories:
            story.hAlign = "CENTER"
            
        doc.build(stories)
        
    def _create_project_section(self, project):
        """
        Creates the higher level order section
        
        This section will also contain a subsection of 
        the items for this order
        """     
        data = []   
        supplier_data = []
        for supplier in Supplier.objects.filter(purchaseorder__project__id=project.id).distinct():
            supplier_data.append(self._create_supplier_section(project, supplier))
            
        data.append([supplier_data])
            
        headings = Table(data, colWidths=[550])
        headings.setStyle(TableStyle(self.item_heading_style))
            
        return headings
    
    def _create_supplier_section(self, project, supplier):
        """
        Creates the higher level items section
        """
        
        data = [["Supplier", "Description", "Quantity", "Total"]]
        total = 0
        for supply in Supply.objects.raw("""
        SELECT s.id, s.description, sum(pi.quantity) as quantity, sum(pi.total) as total,
            po.currency
        FROM po_item AS pi
        INNER JOIN po_purchaseorder AS po
        ON po.id = pi.purchase_order_id
        INNER JOIN supplies_supply as s
        ON s.id = pi.supply_id
        GROUP BY pi.supply_id, pi.description, po.project_id, s.id, po.supplier_id,
            po.currency
        HAVING po.project_id={0} AND po.supplier_id={1}
        ORDER BY description""".format(project.id, 
                                                                  supplier.id), {
            'id': 'id',
            'quantity': 'quantity',
            'description': 'description',
            'total': 'total',
            'currency': 'currency'
        }):
            total += self._exchange_currency(supply.total, supply.currency)
            data.append([self._prepare_text(supplier.name),
                         self._prepare_text(supply.description), 
                         supply.quantity, 
                         self._exchange_currency(supply.total, supply.currency)])
        """
        total = 0
        for po in PurchaseOrder.objects.filter(supplier=supplier).filter(project=project):
            
            for item in po.items.all():
                data.append([self._prepare_text(supplier.name), 
                             po.id, 
                             item.description, 
                             item.quantity, 
                             item.total])
        """
        data.append(["Total", "", "", total])

        table = Table(data, colWidths=[150, 200,100, 100])
        table.setStyle(TableStyle(self.item_style))
        
        return table
    
    def _prepare_text(self, description, font_size=8):
        
        text = description if description else u""
        style = ParagraphStyle(name='Normal',
                               fontName='Garuda',
                               fontSize=font_size,
                               textColor=colors.CMYKColor(black=60))
        return Paragraph(text, style)
        
    def _exchange_currency(self, amount, currency):
        if currency.lower() == "eur":
            return amount * Decimal('36.9')
        elif currency.lower() == "usd":
            return amount * Decimal('32.65')
        else:
            return amount
        
    
if __name__ == "__main__":
    pdf = ProjectPDF()
    pdf.create()