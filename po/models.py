import sys, os
import datetime
import logging
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from reportlab.lib import colors, utils
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from supplies.models import Supply
from contacts.models import Supplier, SupplierContact


logger = logging.getLogger('tester')



# Create your models here.

class PurchaseOrder(models.Model):
    
    supplier = models.ForeignKey(Supplier)
    order_date = models.DateField(db_column = "order_date", null=True, default = datetime.date.today())
    delivery_date = models.DateField(null=True)
    vat = models.IntegerField(default=0)
    shipping_type = models.CharField(max_length=10, default="none")
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="THB")
    #refers to the total of all items
    subtotal = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to total after discount
    total = models.DecimalField(default=0, decimal_places=2, max_digits=12)
    #refers to the todal after vat
    grand_total = models.DecimalField(db_column='grand_total', default=0, decimal_places=2, max_digits=12)
    url = models.TextField(null = True)
    key = models.TextField(null = True)
    bucket = models.TextField(null = True)
    employee = models.ForeignKey(User)
    
    def create(self, data, user=None):
       
        #We will create the purchase order first
        #and then save it before creating the purchase order items 
        #so that the items have something to link to  
        #Set the employee that placed the order
        if user != None:    
            self.employee = user    
        #get supplier from data
        if "supplier" in data:
            self.supplier = Supplier.objects.get(id=data["supplier"])
        if "attention" in data:
            self.attention = data["attention"]
        #apply vat and currency
        if "vat" in data: self.vat = float(data["vat"])
        self.currency = self.supplier.currency
        #set the deliverydate
        if "deliveryDate" in data:
            delivery_date = datetime.date(data['deliveryDate']['year'], data['deliveryDate']['month'], data['deliveryDate']['date'])
            self.delivery_date = delivery_date     
        #save the purchase
        self.save()
        #model to hold subtotal
        self.subtotal = 0
        #array to hold supplies
        self.supplies = []
        #checks to see if has supplies to order
        if "supplies" in data:
            #iterate to create purchase order items
            for supplyData in data["supplies"]:
                #create item and apply data
                poItem = PurchaseOrderItems()
                poItem.create(supplyData)
                poItem.setPO(self)
                #save the item
                poItem.save()
                #add to array
                self.supplies.append(poItem)                
                #add supply total to po total
                self.subtotal = self.subtotal + poItem.total       
        #checks if there was a shipping charge
        if "shipping" in data:
            #checks whether shipping is charged
            if data['shipping'] != False:    
                if "type" in data["shipping"]: self.shipping_type = data['shipping']['type']
                if "amount" in data["shipping"]: self.shipping_amount = Decimal(data['shipping']['amount'])     
                #add shipping to subtotal
                self.subtotal = self.subtotal + self.shipping_amount     
        #Calculates the totals of the PO
        #calculate total after discount
        if self.supplier.discount != 0:
            #percentage 
            if sys.version_info[:2] == (2,6):
                percentage = Decimal(str(self.supplier.discount))/100
            elif sys.version_info[:2] == (2,7):
                percentage = Decimal(self.supplier.discount)/100
            #amount to discount based off of subtotal
            discount_amount = self.subtotal*percentage
            #remaining total after subtracting discount
            self.total = self.subtotal-discount_amount
        #if no supplier discount
        else:
            #total is equal to subtotal
            self.total = self.subtotal       
        #calculate total after tax
        if self.vat != 0 or self.vat != '0':
            #get vat percentage
            if sys.version_info[:2] == (2,6):
                percentage = Decimal(str(self.vat))/100
            elif sys.version_info[:2] == (2,7):
                percentage = Decimal(self.vat)/100
            #get vat amount
            vat_amount = self.total*percentage
            #remaining grand total after adding vat
            self.grand_total = self.total+vat_amount
        else:
            #grand total is equal to total
            self.grand_total = self.total
        
        #save the data
        self.save()   
        #creates the PDF and retrieves the returned
        #data concerning location of file
        if "attention" in data: 
            att_id = data["attention"]["id"]
            att = SupplierContact.objects.get(id=att_id)
        else:
            att = None 
        #Create the pdf object and have it create a pdf
        pdf = PurchaseOrderPDF(supplier=self.supplier, supplies=self.supplies, po=self, attention=att)
        filename = pdf.create()
        #update pdf
        self.upload(filename)
        self.save()

    #get data
    def get_data(self):
        #get the url
        data = {
                'url':self.get_url(),
                'id':self.id,
                'orderDate':self.order_date.isoformat(),
                'employee':self.employee.first_name+' '+self.employee.last_name
                }
        return data
    
    def get_url(self):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key = self.key, force_http=True)
        #return the url
        return url
    
    #uploads the pdf
    def upload(self, filename):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it 
        k = Key(bucket)        
        #Set file name
        k.key = "purchase_order/Purchase_Order-%s.pdf" % self.id
        #upload file
        k.set_contents_from_filename(filename)
        #set the Acl
        k.set_acl('private')
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        self.key = k.key
        self.save()
     
class PurchaseOrderItems(models.Model):
    
    purchase_order = models.ForeignKey(PurchaseOrder, db_column = "purchase_order_id")
    supply = models.ForeignKey(Supply, db_column = "supply_id")
    quantity = models.IntegerField()
    discount = models.IntegerField()
    unit_cost = models.DecimalField(decimal_places=2, max_digits=12, default=0, db_column="unit_cost")
    total = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    currency = models.CharField(max_length=10, default="THB")
    
    #set po
    def setPO(self, po):
        self.purchase_order = po
        
    #create
    def create(self, data):
        if "id" in data:
            self.supply = Supply.objects.get(id=data["id"])
            self.description = self.supply.description
            self.cost = self.supply.cost
            self.discount = self.supply.discount
            if self.supply.discount == 0:
                self.unit_cost = self.supply.cost
            else:
                if sys.version_info[:2] == (2,6):
                    discount_amount = self.supply.cost*(Decimal(str(self.supply.discount)/100))
                elif sys.version_info[:2] == (2,7):
                    discount_amount = self.supply.cost*(Decimal(self.supply.discount)/100)
                self.unit_cost = self.supply.cost-discount_amount
            
        if "quantity" in data: 
            self.quantity = data["quantity"]  
            #if there is a discount apply the discount
            self.total = self.unit_cost*self.quantity
        






class PurchaseOrderPDF():
    """Class to create PO PDF"""
    
    #def methods
    def __init__(self, supplier=None, supplies=None, po=None, attention=None, misc=None):
        #Imports
        
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.supplier = supplier  
        self.supplies = supplies
        self.po = po
        self.employee = self.po.employee
        self.attention = attention
    
    #create method
    def create(self):
        self.filename = "Purchase_Order-%s.pdf" % self.po.id
        self.location = "%s%s" % (settings.MEDIA_ROOT,self.filename)
        #create the doc template
        doc = SimpleDocTemplate(self.location, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #initialize story array
        Story = []
       
        #add heading and spacing
        Story.append(self.__create_heading())
        Story.append(Spacer(0,50))
        
        #create the table to hold the data
        #about the supplier
        
        #create table for supplier and recipient data
        Story.append(self.__create_contact_section())
        Story.append(Spacer(0,20))
        
        #Create table for po data
        Story.append(self.__create_po_section())
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
        #return the filename
        return self.location
                   
    def firstPage(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.CMYKColor(black=60))
        #canvas.drawRightString(width-36, height-72, "Purchase Order")
        canvas.restoreState()
        
    def __create_heading(self):
        """
        Create Heading.
        
        This method Creates the heading, which
        includes the logo and the subheading"""
        
        #create the heading
        heading = Table([
                         [self.get_image("https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/logo/form_logo.jpg", height=30), 
                         self.__create_sub_heading()]
                         ], colWidths=(320, 210))
        #create the heading format and apply
        headingStyle = TableStyle([('TOPPADDING', (0,0), (-1,-1), 0),
                             ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                             ('VALIGN', (0,0), (0,-1), 'BOTTOM'),
                             ('FONT', (0,0), (-1,-1), 'Helvetica'),
                             ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                             ('VALIGN', (1,0), (1,-1), 'TOP'),
                             ('ALIGNMENT', (1,0), (1,-1), 'RIGHT'),
                             ('FONTSIZE', (1,-1),(1,-1), 10)])
        heading.setStyle(headingStyle)
        #Return the heading
        return heading
        
    def __create_sub_heading(self):
        #Create Subheading with PO number
        sub_heading = Table([["Purchase Order"],
                            ["PO#: %s" %self.po.id]])
        #Create and set style
        style = TableStyle([('FONTSIZE', (0,0), (0,0), 15),
                    ('FONTSIZE', (0,1),(0,1), 11),
                    ('VALIGN', (0,0),(-1,-1), 'TOP'),
                    ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                    ('ALIGNMENT', (0,0), (-1,-1), 'RIGHT')])
        sub_heading.setStyle(style)
        #return the sub_heading
        return sub_heading
    
    def __create_supplier_section(self):
        #extract supplier address
        address = self.supplier.address_set.all()[0] 
        #Create data array
        data = []
        #Add supplier name
        data.append(['Supplier:', self.supplier.name])    
        #add supplier address data
        data.append(['', address.address1])
        data.append(['', address.city+', '+ address.territory])
        data.append(['', "%s %s" % (address.country, address.zipcode)]) 
        #Create Table
        table = Table(data, colWidths=(60, 200))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1,-1), 'Helvetica')])
        table.setStyle(style)
        #Return the Recipient Table
        return table
    
    def __create_recipient_section(self):
        #Create data array
        data = []
        #Add Employee Name
        data.append(['Ship To:', "%s %s" %(self.employee.first_name, self.employee.last_name)])    
        #Add Company Data
        data.append(['', '8/10 Moo 4 Lam Luk Ka Rd. Soi 65'])
        data.append(['', 'Lam Luk Ka, Pathum Thani'])
        data.append(['', 'Thailand 12150'])
        #Create Table
        table = Table(data, colWidths=(50, 150))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1,-1), 'Helvetica')])
        table.setStyle(style)
        #Return the Recipient Table
        return table
    
    def __create_contact_section(self):
        """Create the Contact Table."""
        t1 = self.__create_supplier_section()
        t2 = self.__create_recipient_section()
        #create table for supplier and recipient data
        contact = Table([[t1, t2]])
        return contact
        
    def __create_po_section(self):
        #Create data array
        data = []
        #Add Data
        data.append(['Payment Terms:', self.__get_payment_terms()])
        data.append(['Currency:', self.__get_currency()])
        data.append(['Date of Order:', self.po.order_date.strftime('%B %d, %Y')])
        data.append(['Delivery Date:', self.po.delivery_date.strftime('%B %d, %Y')])
        #Create table
        table = Table(data, colWidths=(90, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1, -1), 'Helvetica')])
        table.setStyle(style)
        #Return Table
        return table
        
    def __get_payment_terms(self):
        #determine Terms String
        # based on term length
        if self.supplier.terms == 0:
            terms = "Payment Before Delivery"
        else:
            terms = "%s Days" %self.supplier.terms  
        #return term
        return terms
    
    def __get_currency(self):
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
    def get_image(self, path, width=None, height=None):
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
    
    
    
    
    