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
    discount = models.IntegerField()
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
        self.status = 'ACKNOWLEDGED'
        self.save()
        #Set products information
        for product_data in data['products']:
            self.__set_product(product_data)
        #Initialize and create pdf  
        pdf = AcknowledgementPDF(customer=self.customer, ack=self, products=self.item_set.all())
        filename = pdf.create()
        #Upload and return the url
        self.__upload(filename)
        return self.__get_url()
    
    #Set the product from data
    def __set_product(self, product_data):
        #Get the product by id
        product = Product.objects.get(id=product_data["id"])
        #Create Ack Item and assign product data
        ack_item = Item()
        ack_item.acknowledgement = self
        #Set Quantity for later calculations
        ack_item.quantity = int(product_data["quantity"])
        ack_item.set_data(product)
        #Assign order specific data
        if "width" in product_data and product_data['width'] > 0: ack_item.width = product_data['width']
        if "depth" in product_data and product_data['depth'] > 0: ack_item.width = product_data['depth']
        if "height" in product_data and product_data['height'] > 0: ack_item.width = product_data['height']
        ack_item.save()
    
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
    price = models.DecimalField(null=True, max_digits=15, decimal_places=2)
    width = models.IntegerField(db_column='width', default=0)
    depth = models.IntegerField(db_column='depth', default=0)
    height = models.IntegerField(db_column='height', default=0)
    units = models.CharField(max_length=20, default='mm')
    fabric = models.TextField()
    description = models.TextField()
    is_custom_size = models.BooleanField(db_column='is_custom_size', default=False)
    status = models.CharField(max_length=50)
    
    def set_data(self, product, user=None):
        self.description = product.description
        self.product = product
        print product.retail_price
        print product.wholesale_price
        self.price = product.retail_price*self.quantity
        self.width = product.width
        self.depth = product.depth
        self.height = product.height
        self.save()
        print product.pillow_set.all()
        if len(self.product.pillow_set.all()) > 0:
            for pillow in self.product.pillow_set.all():
                ack_pillow = Pillow()
                ack_pillow.item = self
                ack_pillow.type = pillow.type
                ack_pillow.quantity = pillow.quantity*self.quantity
                ack_pillow.fabric = Fabric.objects.all()[0]
                ack_pillow.save()
                print "Pillows:"
                print pillow.quantity * self.quantity
                print type(pillow.quantity)
                print type(int(self.quantity))
                print ack_pillow.quantity
        
#Pillows for Acknowledgement items
class Pillow(models.Model):
    item = models.ForeignKey(Item)
    type = models.CharField(max_length=10, null=True)
    quantity = models.IntegerField()
    fabric = models.ForeignKey(Fabric)
        
    
class AcknowledgementPDF():
    """Class to create PO PDF"""
    
    #def methods
    def __init__(self, customer=None, products=None, ack=None):
        #Imports
        
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
        #Story.append(self.__create_akc_section())
        #Story.append(Spacer(0,40))
        #Alignes the header and supplier to the left
        for aStory in Story:
            aStory.hAlign = 'LEFT'
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
        #add supplier address data
        data.append(['', address.address1])
        data.append(['', address.city+', '+ address.territory])
        data.append(['', "%s %s" % (address.country, address.zipcode)]) 
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
        data.append(['Payment Terms:', self.__get_payment_terms()])
        data.append(['Currency:', self.__get_currency()])
        data.append(['Date of Order:', self.po.order_date.strftime('%B %d, %Y')])
        data.append(['Delivery Date:', self.po.delivery_date.strftime('%B %d, %Y')])
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
        #Create data array
        data = []
        #Add Column titles
        data = [['Product ID', 'Description', 'Unit Price', 'Qty', 'Total']]
        #iterate through the array
        for product in self.products:
            print product.product.description
            print product.description
            #add the data
            data.append([product.product.id, product.description, '',product.quantity, product.price])
            #increase the item number
            print product.pillow_set.all()
            if len(product.pillow_set.all()) > 0:
                for pillow in product.pillow_set.all():
                    data.append(['', '{0} Pillow'.format(pillow.type.capitalize()), '', pillow.quantity])
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
        table = Table(data, colWidths=(65, 300, 50, 40, 65))\
        #Create table style data and merge with totals style data
        style_data = [('TEXTCOLOR', (0,0), (-1,-1), colors.CMYKColor(black=60)),
                            ('LINEABOVE', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                            #line under heading
                            ('LINEBELOW', (0,0), (-1,0), 1, colors.CMYKColor(black=60)),
                            ('ALIGNMENT', (0,0), (1,-1), 'CENTER'),
                            ('ALIGNMENT', (1,0), (1,-1), 'LEFT'),
                            #('ALIGNMENT', (5,0), (5,-1), 'CENTER'),
                            #align headers from description to total
                            #('ALIGNMENT', (3,0), (-1,0), 'CENTER'),
                            #align totals to the right
                            ('ALIGNMENT', (-1,1), (-1,-1), 'RIGHT')]
                            #('GRID', (0,0), (-1,-1), 1, colors.CMYKColor(black=80)),
                            #('LEFTPADDING', (2,0), (2,-1), 10)]
        #style_data += totals_style
        #Create and apply table style
        style = TableStyle(style_data)
        table.setStyle(style)
        #Return the table
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
    
    def __get_totals(self):
        #Create data and style array
        data = []
        style = []
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
        #Return data and style
        return data, style
        
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
    
    
    
    




