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
from contacts.models import Customer
from products.models import Product, Upholstery
from supplies.models import Fabric

# Create your models here.

#Create the initial Acknowledgement category
class Acknowledgement(models.Model):
    #Customer's PO ID
    #We keep for customer
    #courtesy
    po_id = models.TextField()
    discount = models.IntegerField(default=0)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    employee = models.ForeignKey(User, on_delete=models.PROTECT)
    time_created = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateField()
    status = models.TextField()
    production_key = models.TextField()
    acknowledgement_key = models.TextField()
    bucket = models.TextField()
    remarks = models.TextField()
    fob = models.TextField()
    shipping = models.TextField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    vat = models.IntegerField(default=0)
    
    #Get Data
    def get_data(self):
        
        data = {
                'id':self.id,
                'delivery_date':self.delivery_date.strftime('%B %d, %Y'),
                'time_created':self.time_created.strftime('%B %d, %Y %H:%M:%S'), 
                'status':self.status, 
                'remarks':self.remarks,
                'fob':self.fob,
                'shipping':self.shipping, 
                'customer':self.customer.name,
                'employee':'%s %s' %(self.employee.first_name, self.employee.last_name)}
        
        return data
    
    #Create Acknowledgement
    def create(self, data, user=None):
        #Set ack information
        self.customer = Customer.objects.get(id=data['customer']['id'])
        self.employee = user
        date_obj = data['delivery_date']
        self.delivery_date = datetime.date(date_obj['year'], date_obj['month'], date_obj['date'])
        if "vat" in data: self.vat = int(data["vat"]) 
        self.status = 'ACKNOWLEDGED'
        self.save()
        #Set products information
        for product_data in data['products']:
            self.__set_product(product_data)
        #Calculate totals
        self.__calculate_totals()
        #Initialize and create pdf  
        pdf = AcknowledgementPDF(customer=self.customer, ack=self, products=self.item_set.all())
        filename = pdf.create()
        #Upload and return the url
        self.__upload(filename)
        return self.__get_url()
    
    
    
    #Set the product from data
    def __set_product(self, product_data):
        if "id" in product_data:
            #Get the product by id
            product = Product.objects.get(id=product_data["id"])
        else:
            product = Product.objects.get(id=10436)
        #Create Ack Item and assign product data
        ack_item = Item()
        ack_item.acknowledgement = self
       
        ack_item.set_data(product, data=product_data, customer=self.customer)
        ack_item.save()
        
    #Calculate totals and subtotals
    def __calculate_totals(self):
        running_total = 0
        #Loop through products
        for product in self.item_set.all():
            #Add Price
            running_total += product.total
        #Set Subtotal
        self.subtotal = running_total
        discount = (Decimal(self.discount)/100)*running_total
        running_total -= discount
        vat = (Decimal(self.vat)/100)*running_total
        running_total += vat
        self.total = running_total
    
    #Get the correct product based on type    
    def __get_product(self, product_data):
        if product_data["type"] == "Upholstery":
            return Upholstery.objects.get(product_ptr_id=product_data["id"])
    
    #Get the Url of the document
    def __get_url(self):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the url
        url = conn.generate_url(1800, 'GET', bucket=self.bucket, key=self.key, force_http=True)
        #return the url
        return url
            
    #uploads the pdf
    def __upload(self, filename):
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('document.dellarobbiathailand.com', True)
        #Create a key and assign it 
        k = Key(bucket)        
        #Set file name
        k.key = "acknowledgement/Acknowledgement-%s.pdf" % self.id
        #upload file and set acl
        k.set_contents_from_filename(filename)
        k.set_acl('private')
        #Remove original
        os.remove(filename)
        #set Url, key and bucket
        self.bucket = "document.dellarobbiathailand.com"
        self.key = k.key
        self.save()
    
#Create the Acknowledgement Items
class Item(models.Model):
    acknowledgement = models.ForeignKey(Acknowledgement)
    product = models.ForeignKey(Product)
    type = models.CharField(max_length=20)
    #Price not including discount
    quantity = models.IntegerField(null=False)
    unit_price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    total = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    fabric = models.TextField(default=None)
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size', default=False)
    is_custom_item = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    bucket = models.TextField()
    image_key = models.TextField()
    
    def set_data(self, product, data=None, user=None, customer=None):
        """Set the objects attributes with data from the product
        as defined by the database. After, if there is a data object
        they data object will used to be set the attributes with the 
        proper check for which can be overwritten and which can't"""
        #Set quantity used for calculation later
        if data != None:
            if "quantity" in data: self.quantity = int(data["quantity"])
        else:
            self.quantity = 0
        #Set from product
        self._set_attr_from_product(product, customer)
        #Set from data if exists
        if data != None:
            self._set_attr_from_data(data)
                
    def _set_attr_from_product(self, product, customer):
        self.description = product.description
        self.product = product
        #Get Price based on customer typpe
        if customer.type == "Retail":
            price = product.retail_price
        elif customer.type == "Dealer":
            price = product.wholesale_price
        else:
            price = product.retail_price
        #Set the unit price then total 
        self.unit_price = price
        self.total = self.unit_price*Decimal(self.quantity)
        #Set dimensions
        self.width = product.width
        self.depth = product.depth
        self.height = product.height
        #Set Image properties
        self.bucket = product.bucket
        self.image_key = product.image_key
        self.save()
        
                
    def _set_attr_from_data(self, data):
        """Sets the attribute, but checks if they
        exists first."""
        #Set dimensions
        if "is_custom_size" in data:
            if data["is_custom_size"] == True:
                self.is_custom_size = True
                #Checks if data is greater than 0
                if "width" in data and data['width'] > 0: self.width = int(data['width'])
                if "depth" in data and data['depth'] > 0: self.depth = int(data['depth'])
                if "height" in data and data['height'] > 0: self.height = int(data['height'])
        #Checks if it a custom item
        if "is_custom" in data:
            if data["is_custom"] == True:
                self.is_custom_item = True
                self.description = data["description"]
                #Add Image to product if exists
                if "image" in data:
                    self.image_key = data["image"]["key"]
                    self.bucket = data["image"]["bucket"]
        #Checks if fabric in data
        if "fabric" in data:
            print data["fabric"]
            fabric = Fabric.objects.get(id=data["fabric"]["id"])
            self.fabric = fabric.description
        #Checks if this item has pillows
        if "pillows" in data:
            pillows = []
            for pillow in data["pillows"]:
                for i, item in enumerate(pillows):
                    if item["type"] == pillow["type"] and item["fabric"]["description"] == pillow["fabric"]["description"]:
                            pillows[i]["quantity"] += 1
                            break
                else:
                    if "quantity" not in pillow: pillow["quantity"] = 1
                    pillows.append(pillow)
                    
           
            #Get pillows
        
            for pillow in pillows:
                ack_pillow = Pillow()
                ack_pillow.item = self
                ack_pillow.type = pillow["type"]
                ack_pillow.quantity = pillow["quantity"]*self.quantity
                ack_pillow.fabric = Fabric.objects.get(id=pillow["fabric"]["id"])
                ack_pillow.save()
        
#Pillows for Acknowledgement items
class Pillow(models.Model):
    item = models.ForeignKey(Item)
    type = models.CharField(max_length=10, null=True)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric)
        
    
class AcknowledgementPDF():
    """Class to create PO PDF"""
    
    #def methods
    def __init__(self, customer=None, products=None, ack=None, connection=None):
        #Imports
        
        #set connection
        self.connection = connection if connection != None else S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        #Set Defaults
        self.width, self.height = A4
        stylesheet = getSampleStyleSheet()
        normalStyle = stylesheet['Normal']
        #Set Var
        self.customer = customer  
        self.products = products
        self.ack = ack
        self.employee = self.ack.employee
    
    #create method
    def create(self):
        self.filename = "Acknowledgement-%s.pdf" % self.ack.id
        self.location = "{0}{1}".format(settings.MEDIA_ROOT,self.filename)
        #create the doc template
        doc = SimpleDocTemplate(self.location, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36)
        #initialize story array
        Story = []
        #add heading and spacing
        Story.append(self.__create_heading())
        Story.append(Spacer(0,50))
        #create table for supplier and recipient data
        Story.append(self.__create_contact_section())
        Story.append(Spacer(0,20))
        #Create table for po data
        Story.append(self.__create_ack_section())
        Story.append(Spacer(0,40))
        #Alignes the header and supplier to the left
        for a_story in Story:
            a_story.hAlign = 'LEFT'
        #creates the data to hold the product information
        Story.append(self.__create_products_section())
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
                         self.__create_sub_heading()],
                         ["8/10 Moo 4 Lam Lukka Rd. Soi 65, Lam Lukka,", ""],
                         ["Pathum Thani, Thailand 12150", ""],
                         ["+66 2 998 7490", ""],
                         ["www.dellarobbiathailand.com", ""]
                         ], colWidths=(320, 210))
        #create the heading format and apply
        headingStyle = TableStyle([('TOPPADDING', (0,0), (-1,-1), 0),
                                   ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                                   ('VALIGN', (0,0), (0,-1), 'BOTTOM'),
                                   ('FONT', (0,0), (-1,-1), 'Helvetica'),
                                   ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                                   ('VALIGN', (1,0), (1,-1), 'TOP'),
                                   ('ALIGNMENT', (1,0), (1,-1), 'RIGHT'),
                                   ('FONTSIZE', (0,1),(0,-1), 8)])
        heading.setStyle(headingStyle)
        #Return the heading
        return heading
        
    def __create_sub_heading(self):
        #Create Subheading with PO number
        sub_heading = Table([["Acknowledgement"],
                            ["Ack#: %s" %self.ack.id]])
        #Create and set style
        style = TableStyle([('FONTSIZE', (0,0), (0,0), 15),
                    ('FONTSIZE', (0,1),(0,1), 11),
                    ('VALIGN', (0,0),(-1,-1), 'TOP'),
                    ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                    ('ALIGNMENT', (0,0), (-1,-1), 'RIGHT')])
        sub_heading.setStyle(style)
        #return the sub_heading
        return sub_heading
    
    def __create_customer_section(self):
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
        data.append(['', '%s, %s' % (city, territory)])
        data.append(['', "%s %s" % (country, zipcode)]) 
        #Create Table
        table = Table(data, colWidths=(80, 200))
        #Create and apply Table Style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1,-1), 'Helvetica')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
        table.setStyle(style)
        #Return the Recipient Table
        return table
    
    def __create_contact_section(self):
        """Create the Contact Table."""
        t1 = self.__create_customer_section()
        #t2 = self.__create_recipient_section()
        #create table for supplier and recipient data
        contact = Table([[t1]])
        #Create Style and apply
        style = TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), 
                            ('ALIGNMENT', (0,0), (-1,-1), 'LEFT')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
        contact.setStyle(style)
        #Return table
        return contact
        
    def __create_ack_section(self):
        #Create data array
        data = []
        #Add Data
        data.append(['Currency:', self.__get_currency()])
        data.append(['Order Date:', self.ack.time_created.strftime('%B %d, %Y')])
        data.append(['Delivery Date:', self.ack.delivery_date.strftime('%B %d, %Y')])
        #Create table
        table = Table(data, colWidths=(80, 200))
        #Create and set table style
        style = TableStyle([('BOTTOMPADDING', (0,0), (-1,-1), 1),
                            ('TOPPADDING', (0,0), (-1,-1), 1),
                            ('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('FONT', (0,0), (-1, -1), 'Helvetica')])
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=60))])
        table.setStyle(style)
        #Return Table
        return table
    
    def __create_products_section(self):
        
        #Create data and index array
        data = []
        #Add Column titles
        data.append([self.__create_products_title_section()])
        #iterate through the array
        for product in self.products:
            data.append([self.__create_products_item_section(product)])
        
        data.append([self.__create_totals_section()])  
        #add a shipping line item if there is a shipping charge
        #if self.ack.shipping_type != "none":
        #    shipping_description, shipping_amount = self.__get_shipping()
            #Add to data
            #data.append(['', '', shipping_description, '','','', "%.2f" %float(self.po.shipping_amount)])
        #Get totals data and style
        #totals_data, totals_style = self.__get_totals() 
        #merge data
        #data += totals_data
        #Create Table
        table = Table(data, colWidths=(520), repeatRows=1)
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                      ('GRID', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                      ('TOPPADDING', (0,0), (-1,-1), 0),
                      ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                      ('ALIGNMENT', (0,0), (-1,-2), 'CENTER'),
                      ('ALIGNMENT', (0,-1), (-1,-1), 'RIGHT')]
                           
        table.setStyle(TableStyle(style_data))
        #loop through index to add line below item
        #for index in indexes:
            #style_data.append(('LINEBELOW', (0, index), (-1, index), 1, colors.CMYKColor(black=20)))
        #Create and apply table style
        #style = TableStyle(style_data)
        #table.setStyle(style)
        #Return the table
        return table
    
    def __create_products_title_section(self):
        table = Table([['Product ID', 'Description', 'Unit Price', 'Qty', 'Total']], colWidths=(65, 300, 60, 40, 65))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                      ('GRID', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                      #General alignment
                      ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                      #Align description
                      ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                      #Align Quantity
                      ('ALIGNMENT', (-3,0), (-2,-1), 'CENTER'),
                      #align totals to the right
                      ('ALIGNMENT', (-1,1), (-1,-1), 'RIGHT')]
        style = TableStyle(style_data)
        table.setStyle(style)
        return table
    
    def __create_products_item_section(self, product):
        data = []
        #add the data
        data.append([product.product.id, product.description, product.unit_price,product.quantity, product.total])
        if product.fabric != None:
            print type(product.fabric), product.fabric
            data.append(['', '   Fabric: {0}'.format(product.fabric), '', '', ''])
        if product.is_custom_size:
            data.append(['', '   Width: %imm Depth: %imm Height: %imm' %(product.width, product.depth, product.height)])
        #increase the item number
        if len(product.pillow_set.all()) > 0:
            for pillow in product.pillow_set.all():
                data.append(['', '   {0} Pillow: {1}'.format(pillow.type.capitalize(), pillow.fabric.description), '', pillow.quantity, ''])
                data.append(['', '       - Fabric: {0}'.format(pillow.fabric.description), '', '', ''])
        #Get Image url and add image
        image_url = self.connection.generate_url(100, 'GET', bucket=product.bucket, key=product.image_key, force_http=True)
        data.append(['', self.get_image(image_url, height=100)])
        #Create table
        table = Table(data, colWidths=(65, 300, 60, 40, 65))
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0,0), (-1,-1), 1, colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0,0), (0,-1), 1, colors.CMYKColor(black=60)),
                            #General alignment
                            ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                            #Align description
                            ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                            #Align Unit Price
                            ('ALIGNMENT', (-3,0), (-3,-1), 'RIGHT'),
                            #Align Quantity
                            ('ALIGNMENT', (-2,0), (-2,-1), 'CENTER'),
                            #align totals to the right
                            ('ALIGNMENT', (-1,0), (-1,-1), 'RIGHT')]
        style = TableStyle(style_data)
        table.setStyle(style)
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
        """
        if self.po.currency == "EUR":
            currency = "Euro(EUR)"
        elif self.po.currency == "THB":
            currency = "Thai Baht(THB)"
        elif self.po.currency == "USD":
            currency = "US Dollar(USD)"
        #return currency"""
        return self.customer.currency
    
    def __get_description(self, supply):
        #Set description
        description = supply.description
        #If there is a discount then append
        # original price string
        if supply.discount > 0:
            description += " (discounted %s%% from %s)" %(supply.description, supply.discount, supply.cost)
        #return description
        return description
    
    def __get_shipping(self):
        #set the description
        if self.ack.shipping_type == "air":
            description = "Air Freight"
        elif self.ack.shipping_type == "sea":
            description = "Sea Freight"
        elif self.ack.shipping_type == "ground":
            description = "Ground Freight"
        #return descript and amount
        return description, self.ack.shipping_amount
    
    def __create_totals_section(self):
        #Create data and style array
        data = []
        #calculate the totals     
        #what to do if there is vat or discount
        if self.ack.vat > 0 or self.ack.discount > 0:
            #get subtotal and add to pdf
            data.append(['Subtotal', "%.2f" % self.ack.subtotal])
            total = self.ack.subtotal
            #add discount area if discount greater than 0
            if self.ack.discount != 0:
                discount = self.ack.subtotal*(Decimal(self.ack.discount)/Decimal(100))
                data.append(['Discount %s%%' % self.ack.discount, "%.2f" % discount])       
            #add vat if vat is greater than 0
            if self.ack.vat !=0:
                if self.ack.discount != 0:
                    #append total to pdf
                    discount = self.ack.subtotal*(Decimal(self.ack.discount)/Decimal(100))
                    total -= discount
                    data.append(['Total', "%.2f" % total])
                #calculate vat and add to pdf
                vat = Decimal(self.ack.total)*(Decimal(self.ack.vat)/Decimal(100))
                data.append(['Vat %s%%' % self.ack.vat, "%.2f" % vat])
        data.append(['Grand Total', "%.2f" % self.ack.total]) 
        table = Table(data, colWidths=(60,65))
        style = TableStyle([('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            #Lines around content
                            ('LINEBELOW', (0,-1), (-1,-1), 1, colors.CMYKColor(black=80)),
                            ('LINEAFTER', (0,0), (-1,-1), 1, colors.CMYKColor(black=60)),
                            ('LINEBEFORE', (0,0), (0,-1), 1, colors.CMYKColor(black=60)),
                            #General alignment
                            ('ALIGNMENT', (0,0), (0,-1), 'LEFT'),
                            #Align description
                            ('ALIGNMENT', (1,0), (1,-1), 'RIGHT'),
                            #Align Unit Price
                            ('ALIGNMENT', (-3,0), (-3,-1), 'RIGHT'),
                            #Align Quantity
                            ('GRID', (0,0), (0,-1), 1, colors.CMYKColor(black=60))])
        table.setStyle(style)
        style = TableStyle()
        
        return table
        
    #helps change the size and maintain ratio
    def get_image(self, path, width=None, height=None):
        """Retrieves the image via the link and gets the 
        size from the image. The correct dimensions for 
        image are calculated based on the desired with or
        height"""
        #Read image from link
        img = utils.ImageReader(path)
        #Get Size
        imgWidth, imgHeight = img.getSize()
        #Detect if there height or width provided
        if width!=None and height==None:
            ratio = imgHeight/imgWidth
            newHeight = ratio*width
            newWidth = width
        elif height!=None and width==None:
            ratio = float(imgWidth)/float(imgHeight)
            newHeight = height
            newWidth = ratio*height
           
        return Image(path, width=newWidth, height=newHeight)
    
    
    
    




