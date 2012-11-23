from reportlab.lib import pdfencrypt, colors, utils
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from boto.s3.connection import S3Connection, Location
from boto.s3.key import Key
from django.conf import settings
from decimal import Decimal


width, height = A4
stylesheet = getSampleStyleSheet()
normalStyle = stylesheet['Normal']

class PurchaseOrderPDF():
    
    #def methods
    def __init__(self, supplier=None, supplies=None, po=None):
        
        
        self.supplier = supplier
       
        self.supplies = supplies
        self.po = po
        
    
    #create method
    def create(self):
        
        self.filename = settings.MEDIA_ROOT+"Purchase_Order-%s.pdf" % self.po.id
        #create the doc template
        doc = SimpleDocTemplate(self.filename, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #initialize story array
        Story = []
        #create the heading
        heading = Table([
                         [self.getImage("https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg", height=30), "Purchase Order"],
                         ["8/10 Moo 4 Lam Lukka Rd., Soi 65", "PO#: %s" % self.po.id], 
                         ["Lam Lukka, Pathum Thani, Thailand 12150", self.po.orderDate]
                         ], colWidths=(300, 210))
        #create the heading format and apply
        headingStyle = TableStyle([('TOPPADDING', (0,0), (-1,-1), 0),
                             ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                             ('FONTSIZE', (0,0), (-1,-1), 8),
                             ('VALIGN', (0,0), (0,-1), 'MIDDLE'),
                             ('FONT', (0,0), (-1,-1), 'Helvetica'),
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             ('VALIGN', (1,0), (1,-1), 'TOP'),
                             ('ALIGNMENT', (1,0), (1,-1), 'RIGHT'),
                             ('FONTSIZE', (1,0),(1,0), 14)
                             ])
        heading.setStyle(headingStyle)
        #add heading and spacing
        Story.append(heading)
        Story.append(Spacer(0,25))
        
        #create the table to hold the data
        #about the supplier
        
        #create table for supplier data
        contact = Table(self.formatSupplierData(self.supplier))
        contact.setStyle(TableStyle([
                                     ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                                     ('TOPPADDING', (0,0), (-1,-1), 1),
                                     ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                                     ('FONT', (0,0), (-1,-1), 'Helvetica')
                                     ]))
        Story.append(contact)
        Story.append(Spacer(0,40))
        
        #creates the data to hold the supplies information
        styleData = [
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             #('LINEABOVE', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('LINEBELOW', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('ALIGNMENT', (0,0), (0,-1), 'CENTER'),
                             ('ALIGNMENT', (2,0), (2,-1), 'RIGHT'),
                             ('ALIGNMENT', (3,0), (3,-1), 'CENTER'),
                             ('ALIGNMENT', (2,0), (-1,0), 'CENTER'),
                             ('ALIGNMENT', (-1,1), (-1,-1), 'RIGHT'),
                             #('GRID', (0,1), (-1,-1), 1, colors.CMYKColor(black=80)),
                             ('LEFTPADDING', (1,0), (1,-1), 15)
                             ]
        t = Table(self.formatSuppliesData(self.supplies, style=styleData), colWidths=(50,285, 50, 50, 65))
        tStyle = TableStyle(styleData)
        t.setStyle(tStyle)
        
        for aStory in Story:
            aStory.hAlign = 'LEFT'
        Story.append(t)
        doc.build(Story, onFirstPage=self.firstPage)
        
        #upload the file and return 
        #the upload data
        return self.upload()
            
            
    def firstPage(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.CMYKColor(black=60))
        #canvas.drawRightString(width-36, height-72, "Purchase Order")
        canvas.restoreState()
    
    #format the supplier data
    def formatSupplierData(self, supplier):
        #All data is in a single column 
        #so we will only best adding one value to 
        #each nested array
        
        #create array to hold data with initial heading
        data = []
        address = supplier.address_set.all()[0]
        
        #add name
        data.append(['Supplier:',supplier.name])
        
        #add address data
        data.append(['',address.address1])
        #checks if see if second line needed fro address2
        if address.address2 != None:
            data.append(['',address.address2])
        data.append(['', address.city+', '+address.territory])
        data.append(['', "%s %s" %(address.country, address.zipcode)])
        
        #determine what the terms are
        if supplier.terms == 0:
            terms = "Payment Before Deliver"
        else:
            terms = "%s Days" %supplier.terms
            
        #add the terms to the data
        data.append(['Payment Terms:', terms])
        
        return data
    
    
    def formatSuppliesData(self, supplies, style=None):
        #create an array
        data = [['Item No.', 'Description', 'Unit Price', 'Qty', 'Total']]
        i = 1
        #iterate through the array
        for supply in supplies:
            #determine if the supply has a discount
            if supply.discount == 0:
                description = supply.description
            else:
                description = "%s (discounted %s%% from %s)" %(supply.description, supply.discount, supply.cost)
            #add the data
            data.append([i, description, "%.2f" % float(supply.unitCost), supply.quantity, "%.2f" % float(supply.total)])
            #increase the item number
            i = i+1
        
        self.addTotal(data, style)
        #return the array
        return data
    
    def addTotal(self, data, style=None):
        #Determines whether the supplier has a discount
        if self.supplier.discount == 0:
            data.append(['','','','Grand Total', self.po.total])
            #adjust the style
            style.append(('LINEABOVE', (0,-1), (-1,-1), 1, colors.CMYKColor(black=60)))
        else:
            
            #calculate the totals
            #get subtotal
            subtotal = float(self.po.total)
            discount = subtotal*(float(self.supplier.discount)/float(100))
            grandTotal = subtotal-discount
            
            data.append(['','','','Subtotal', "%.2f" % subtotal])
            data.append(['','','','Discount %s%%' % self.supplier.discount, "%.2f" % discount])
            data.append(['','','','Grand Total', "%.2f" % grandTotal])
            
            #adjust the style
            style.append(('LINEABOVE', (0,-3), (-1,-3), 1, colors.CMYKColor(black=60)))
            style.append(('ALIGNMENT', (-2,-3), (-1,-1), 'RIGHT'))
    
    #helps change the size and maintain ratio
    def getImage(self, path, width=None, height=None):
        img = utils.ImageReader(path)
        imgWidth, imgHeight = img.getSize()
        
        if width!=None and height==None:
            ratio = imgHeight/imgWidth
            newHeight = ratio*width
            newWidth = width
        elif height!=None and width==None:
            ratio = imgWidth/imgHeight
            newHeight = height
            newWidth = ratio*height
            
        return Image(path, width=newWidth, height=newHeight)
    
    
    #uploads the pdf
    def upload(self):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it 
        k = Key(bucket)
            
        #Set file name
        k.key = "purchase_order/%s" % self.filename
        #upload file
        k.set_contents_from_filename(self.filename)
        #set the Acl
        k.set_acl('public-read')
        #set Url, key and bucket
        data = {
                'url':"http://document.dellarobbiathailand.com.s3.amazonaws.com/"+k.key,
                'key':k.key,
                'bucket':'document.dellarobbiathailand.com'
        }
        
        return data
        #self.save()
    