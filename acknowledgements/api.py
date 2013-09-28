"""
API file for acknowledgements
"""
from tastypie import fields
from tastypie.resources import ModelResource
from django.contrib.auth.models import User

from acknowledgements.models import Acknowledgement, Item
from contacts.models import Customer
from auth.models import S3Object


class AcknowledgementResource(ModelResource):
    items = fields.ToManyField('acknowledgements.api.ItemResource', 'items')
    class Meta:
        queryset = Acknowledgement.objects.all()
        resource_name = 'acknowledgement'
        fields = ['time_created', 'deleted', 'last_modified', 'po_id', 'subtotal', 'vat', 'total', 
                  'remarks', 'status']
        
    def obj_create(self, bundle):
        """
        Creates the acknowledgement resource
        """
        #Create the object
        bundle.obj = Acknowledgement()
        
        #hydrate
        bundle = self.full_hydrate(bundle)
        
        #Set the customer
        try:
            bundle.obj.customer = Customer.objects.get(pk=bundle.data["customer"]["id"])
        except:
            raise
        
        #Set the employee
        try:
            bundle.obj.employee = User.objects.get(pk=bundle.request.user)
        except User.DoesNotExist, AttributeError:
            raise
        
        #Set Status
        bundle.status = "ACKNOWLEDGED"
        
        #Create items without saving them 
        bundle.obj.items = [Item.create(acknowledgement=bundle.obj,
                                        commit=False,
                                        **product) for product in bundle.data["products"]]
        
        #Calculate the total price
        bundle.obj.calculate_totals(bundle.obj.items)
        bundle.save()
        
        #Create PDFs
        ack, production = bundle.obj._create_pdfs()
        ack_key = "acknowledgement/Acknowledgement-{0}.pdf".format(bundle.obj.id)
        production_key = "acknowledgement/Production-{0}.pdf".format(bundle.obj.id)
        bucket = "document.dellarobbiathailand.com"
        ack_pdf = S3Object.create(ack, ack_key, bucket, encrypt_key=True)
        prod_pdf = S3Object.create(production, production_key, bucket, encrypt_key=True)
        bundle.obj.acknowledgement_pdf = ack_pdf
        bundle.obj.production_pdf = prod_pdf
        bundle.obj.original_acknowledgement_pdf = ack_pdf
        bundle.obj.save()
        
        #Conditionally email ack to Decoroom
        if "decoroom" in bundle.obj.customer.name.lower():
            bundle.obj.email_decoroom()
                
        return bundle
        

class ItemResource(ModelResource):
    acknowledgement = fields.ToOneField('acknowledgements.api.AcknowledgementResource', 'acknowledgement')
    class Meta:
        queryset = Item.objects.all()
        resource_name = 'acknowledgement/item'
        
