"""
API file for acknowledgements
"""
import logging 
import dateutil

from tastypie import fields
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization
from django.contrib.auth.models import User

from acknowledgements.models import Acknowledgement, Item, Pillow
from contacts.models import Customer
from auth.models import S3Object


logger = logging.getLogger(__name__)

        
class AcknowledgementResource(ModelResource):
    items = fields.ToManyField('acknowledgements.api.ItemResource', 'items', 
                               readonly=True, null=True, full=True)
    customer = fields.ToOneField('contacts.api.CustomerResource', 'customer',
                                 readonly=True, full=True)
    
    class Meta:
        queryset = Acknowledgement.objects.filter(deleted=False)
        resource_name = 'acknowledgement'
        fields = ['time_created', 'deleted', 'last_modified', 'po_id', 'subtotal', 'vat', 'total', 
                  'remarks', 'status', 'delivery_date', 'id']
        always_return_data = True
    
    def dehydrate(self, bundle):
        """
        Implements the dehydrate method
        
        Adds the urls for the acknowledgement and
        the production pdf to the data
        """
        #Add URLS for the acknowledgement
        #and the production pdf to the data
        #bundle
        try:
            ack = bundle.obj.acknowledgement_pdf
            production = bundle.obj.production_pdf
            bundle.data['acknowledgement_pdf'] = {'url': ack.generate_url()}
            bundle.data['production_pdf'] = {'url': production.generate_url()}
        except AttributeError: 
            logger.warn('Missing acknowledgement or production pdf')
            
        return bundle
    
    def obj_create(self, bundle, **kwargs):
        """
        Creates the acknowledgement resource
        """
        logger.info("Creating a new acknowledgement...")
        #Create the object
        bundle.obj = Acknowledgement()
        
        #hydrate
        bundle = self.full_hydrate(bundle)
        
        #Set the customer
        try:
            logger.info("Setting customer...")
            bundle.obj.customer = Customer.objects.get(pk=bundle.data["customer"]["id"])
        except:
            logger.error("Customer with ID {0} could not be found.".format(bundle.data['customer']['id']))
            raise
        
        #Set the employee
        try:
            logger.info("Setting employee...")
            bundle.obj.employee = User.objects.get(pk=bundle.data['employee']['id'])
        except User.DoesNotExist:
            logger.error("User with ID {0} could not be found".format(bundle.data['employee']['id']))
            raise
        except KeyError:
            logger.critical("Missing employee ID.")
            raise
        
        #Set Status
        bundle.obj.status = "ACKNOWLEDGED"
        
        #Create items without saving them 
        logger.info("Creating items...")
        self.items = [Item.create(acknowledgement=bundle.obj,
                                  commit=False,
                                  **product) for product in bundle.data["items"]]
        
        #Calculate the total price
        logger.info("Calculating balance of the order...")
        bundle.obj.calculate_totals(self.items)
        bundle.obj.save()
        
        #Save the items
        logger.info("Saving the items to the database...")
        for item in self.items:
            item.acknowledgement = bundle.obj
            item.save()
        
        #Create and upload the pdfs to the 
        #S3 system. The save the pdfs as
        #Attributes of the acknowledgement
        logger.info("Creating PDF documents...")
        ack, production = bundle.obj._create_pdfs()
        ack_key = "acknowledgement/Acknowledgement-{0}.pdf".format(bundle.obj.id)
        production_key = "acknowledgement/Production-{0}.pdf".format(bundle.obj.id)
        bucket = "document.dellarobbiathailand.com"
        
        logger.info("Uploading PDF documents...")
        ack_pdf = S3Object.create(ack, ack_key, bucket, encrypt_key=True)
        prod_pdf = S3Object.create(production, production_key, bucket, encrypt_key=True)
        bundle.obj.acknowledgement_pdf = ack_pdf
        bundle.obj.production_pdf = prod_pdf
        bundle.obj.original_acknowledgement_pdf = ack_pdf
        bundle.obj.save()
        
        #Conditionally email ack to Decoroom
        if "decoroom" in bundle.obj.customer.name.lower():
            try:
                logger.info("Emailing Decoroom Co., Ltd. the order details...")
                bundle.obj.email_decoroom()
            except Exception as e:
                logger.error("Unable to mail decoroom.")
                logger.error(e)
               
        logger.info("Acknowledgement #{0} created for {1}".format(bundle.obj.id, 
                                                                  bundle.obj.customer.name)) 
        return bundle
    
    def obj_update(self, bundle, **kwargs):
        """
        Implements the obj_update method
        """
        logger.info("Updating acknowledgement...")
        
        #Attempt to get the obj from the kwargs
        try:
            bundle.obj = Acknowledgement.objects.get(pk=kwargs['pk'])
        except Acknowledgement.DoesNotExist:
            logger.error("Acknowledgement #{0} could not be found.".format(kwargs['pk']))
        
        if "delivery_date" in bundle.data:
            bundle.obj.delivery_date = dateutil.parser.parse(bundle.data['delivery_date'])
        
        return bundle
        

class ItemResource(ModelResource):    
    class Meta:
        queryset = Item.objects.all()
        resource_name = 'item'
        always_return_data = True
        authorization = Authorization()
        
    def dehydrate(self, bundle):
        """
        Implment dehydration
        """
        #Adds the fabric information if 
        #a fabric exists for this item
        if bundle.obj.fabric:
            bundle.data['fabric'] = {'id': bundle.obj.fabric.id,
                                'description': bundle.obj.fabric.description}
            #Attempts to add an url to the image if it exists
            try:
                bundle.data['fabric']['image'] = {'url': bundle.obj.fabric.image.generate_url()}
            except AttributeError:
                logger.info("Fabric {0} has no image.".format(bundle.obj.fabric.description))
                
        #Adds pillow dictionaries to the 'pillows'
        #category for every pillow referenced to the
        #item
        bundle.data['pillows'] = [{'id': pillow.id,
                                   'quantity': pillow.quantity,
                                   'type': pillow.type} for pillow
                                  in bundle.obj.pillow_set.all()]
            
        return bundle
        
