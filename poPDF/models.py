from reportlab.lib import pdfencrypt, colors, utils
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.conf import settings
import os
import logging

logger = logging.getLogger('EmployeeCenter');

width, height = A4
stylesheet = getSampleStyleSheet()
normalStyle = stylesheet['Normal']

class PurchaseOrderPDF():
    
    #def methods
    def __init__(self, supplier=None, supplies=None, po=None, misc=None):
        
        
        self.supplier = supplier
       
        self.supplies = supplies
        self.po = po
        
    
    #create method
    def create(self):
        self.filename = "Purchase_Order-%s.pdf" % self.po.id
        self.location = "%s%s" % (settings.MEDIA_ROOT,self.filename)
        #create the doc template
        doc = SimpleDocTemplate(self.location, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #initialize story array
        Story = []
        #create the heading
        heading = Table([
                         [self.getImage("https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg", height=30), "Purchase Order"],
                         ["8/10 Moo 4 Lam Lukka Rd., Soi 65", "PO#: %s" % self.po.id], 
                         ["Lam Lukka, Pathum Thani, Thailand 12150", self.po.order_date.strftime('%B %d, %Y')],
                         ["T: 02-998-7490 F: 02-997-3251", ""],
                         ["info@dellarobbiathailand.com", ""]
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
        contact = Table(self.formatSupplierData(self.supplier))#, colWidths=(100, 180, 100, 150))
        contact.setStyle(TableStyle([
                                     ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                                     ('TOPPADDING', (0,0), (-1,-1), 1),
                                     ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                                     ('FONT', (0,0), (-1,-1), 'Helvetica'),
                                     
                                     #('TOPPADDING', (0,-2), (-1,-2), 20)
                                     ]))
        Story.append(contact)
        Story.append(Spacer(0,40))
        
        #Alignes the header and supplier to the left
        for aStory in Story:
            aStory.hAlign = 'LEFT'
        
        #creates the data to hold the supplies information
        styleData = [
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             #('LINEABOVE', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             #line under heading
                             ('LINEBELOW', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                             ('ALIGNMENT', (4,0), (4,-1), 'RIGHT'),
                             ('ALIGNMENT', (5,0), (5,-1), 'CENTER'),
                             #align headers from description to total
                             ('ALIGNMENT', (3,0), (-1,0), 'CENTER'),
                             #align totals to the right
                             ('ALIGNMENT', (-1,1), (-1,-1), 'RIGHT'),
                             #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=80)),
                             ('LEFTPADDING', (2,0), (2,-1), 10)
                             ]
        t = Table(self.formatSuppliesData(self.supplies, style=styleData), colWidths=(40,84,210,35, 50, 40, 65))
        tStyle = TableStyle(styleData)
        t.setStyle(tStyle)
        Story.append(t)
        
        #create the signature
        s = [
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             #('LINEABOVE', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('LINEBELOW', (0,0), (0,0), 1, colors.CMYKColor(black=60)),
                             ('LINEBELOW', (-1,0), (-1,0), 1, colors.CMYKColor(black=60)),
                             ('ALIGNMENT', (0,-1), (-1,-1), 'CENTER'),
                             ('ALIGNMENT', (0,0), (-1,0), 'LEFT'),
                             
                             ]
        
        sigStyle = TableStyle(s)
        
        #spacer
        Story.append(Spacer(0, 50))
        
        signature = Table([['x', '', 'x'], ['Purchasing Agent', '', 'Manager']], colWidths=(200,100,200))
        signature.setStyle(sigStyle)
        Story.append(signature)
        
        doc.build(Story, onFirstPage=self.firstPage)
        #upload the file and return 
        #the upload data
        uploadData = self.upload()
        #delete the file from local harddisk
        os.remove(self.location)
        #return the upload data
        return uploadData
            
            
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
        
        #add name AND DELIVERY DATE
        data.append(['Supplier:',supplier.name])
        
        #add address data
        data.append(['',address.address1])
        #checks if see if second line needed fro address2
        if address.address2 != None:
            data.append(['',address.address2])
        data.append(['', address.city+', '+address.territory])
        data.append(['', "%s %s" %(address.country, address.zipcode)])
        
        #checks if this po needs someone's attention
        if self.po.attention != None:
            
            data.append(['Attention:', self.po.attention])
        
        #determine what the terms are
        if supplier.terms == 0:
            terms = "Payment Before Deliver"
        else:
            terms = "%s Days" %supplier.terms
            
        #add the terms to the data
        data.append(['Payment Terms:', terms])
        #add currency
        if self.po.currency == "EUR":
            currency_description = "Euro(EUR)"
        elif self.po.currency == "THB":
            currency_description = "Thai Baht(THB)"
        elif self.po.currency == "USD":
            currency_description = "US Dollar(USD)"
        data.append(["Currency:", currency_description])
        #add the delivery date
        data.append(['Delivery Date:', self.po.delivery_date.strftime('%B %d, %Y')])
        
        
        return data
    
    
    def formatSuppliesData(self, supplies, style=None):
        #create an array
        data = [['Item No.','Ref', 'Description','Units', 'Unit Price', 'Qty', 'Total']]
        i = 1
        #iterate through the array
        for supply in supplies:
            #determine if the supply has a discount
            if supply.discount == 0:
                description = supply.description
            else:
                description = "%s (discounted %s%% from %s)" %(supply.description, supply.discount, supply.cost)
            #add the data
            data.append([i, supply.supply.reference, description, supply.supply.purchasing_units, "%.2f" % float(supply.unit_cost), supply.quantity, "%.2f" % float(supply.total)])
            #increase the item number
            i = i+1
        
        #add a shipping line item if there is a shipping charge
        if self.po.shipping_type != "none":
            #set the description
            if self.po.shipping_type == "air":
                shipping_description = "Air Freight"
            elif self.po.shipping_type == "sea":
                shipping_description = "Sea Freight"
            elif self.po.shipping_type == "ground":
                shipping_description = "Ground Freight"
            #Add to data
            data.append(['', '', shipping_description, '','','', "%.2f" %float(self.po.shipping_amount)])
        
        
        self.addTotal(data, style)
        #return the array
        return data
    
    def addTotal(self, data, style=None):
       
        #calculate the totals
            
        #what to do if there is vat or discount
        if self.po.vat !=0 or self.supplier.discount!=0:
            #get subtotal and add to pdf
            subtotal = float(self.po.subtotal)
            data.append(['', '','','','','Subtotal', "%.2f" % subtotal])
            #add discount area if discount greater than 0
            if self.supplier.discount != 0:
                discount = subtotal*(float(self.supplier.discount)/float(100))
                data.append(['', '','','','','Discount %s%%' % self.supplier.discount, "%.2f" % discount])
                
            #add vat if vat is greater than 0
            if self.po.vat !=0:
                if self.supplier.discount != 0:
                    #append total to pdf
                    data.append(['', '','','','','Total', "%.2f" % self.po.total])
                #calculate vat and add to pdf
                vat = float(self.po.total)*(float(self.po.vat)/float(100))
                data.append(['', '','','','','Vat %s%%' % self.po.vat, "%.2f" % vat])

        data.append(['', '','','','','Grand Total', "%.2f" % self.po.grand_total])
            
        #adjust the style based on vat and discount
        
        #if there is either vat or discount
        if self.po.vat !=0 or self.supplier.discount!=0:
            #if there is only vat or only discount
            if self.po.vat !=0 and self.supplier.discount!=0:
                style.append(('LINEABOVE', (0,-5), (-1,-5), 1, colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2,-5), (-1,-1), 'RIGHT'))       
            #if there is both vat and discount
            else:
                style.append(('LINEABOVE', (0,-3), (-1,-3), 1, colors.CMYKColor(black=60)))
                style.append(('ALIGNMENT', (-2,-3), (-1,-1), 'RIGHT'))
        #if there is no vat or discount
        else:
            style.append(('LINEABOVE', (0,-1), (-1,-1), 1, colors.CMYKColor(black=60)))
            style.append(('ALIGNMENT', (-2,-1), (-1,-1), 'RIGHT'))
            
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
        k.set_contents_from_filename(self.location)
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
    