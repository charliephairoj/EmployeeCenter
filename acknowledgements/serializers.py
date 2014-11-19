import logging

from rest_framework import serializers

from acknowledgements.models import Acknowledgement, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from products.models import Product
from supplies.models import Fabric
from projects.models import Project


logger = logging.getLogger(__name__)


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.PrimaryKeyRelatedField(required=False)
    
    class Meta:
        model = Pillow
        field = ('type', 'fabric', 'quantity')
        read_only_fields = ('item',)
            
    def from_native(self, data, files):
        instance = super(PillowSerializer, self).from_native(data, files)
        
        if "fabric" in data:
            try:
                instance.fabric = Fabric.objects.get(pk=data['fabric']['id'])
            except:
                pass
                
        return instance
        
    def transform_fabric(self, obj, value):
        try:
            return {'id': obj.fabric.id,
                    'color': obj.fabric.color,
                    'pattern': obj.fabric.pattern}
        except AttributeError: 
            return None
        
        
class ItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(required=False)
    pillows = PillowSerializer(required=False, many=True, allow_add_remove=True)
    unit_price = serializers.DecimalField(required=False)
    comments = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    fabric = serializers.PrimaryKeyRelatedField(required=False)
   
    class Meta:
        model = Item
        field = ('description', 'id', 'width', 'depth', 'height')
        read_only_fields = ('total', 'image', 'type')
        exclude = ('acknowledgement', )
        
    def restore_object(self, attrs, instance):
        """
        Overrides the 'ModelSerializer' 'restore_object' method in order
        to separate the pathways for update and create. The parent method
        is called later in 'create' or 'update' method
        """
        if instance:
            instance = self.update(attrs, instance)
        else:
            instance = self.create(attrs, instance)
        
        return instance
        
    def create(self, attrs, instance):
        """
        Populates the instance after the parent 'restore_object' method is 
        called. 
        """
        instance = super(ItemSerializer, self).restore_object(attrs, instance)
        
        #Set the unit_price if the instance unit_price is 0
        if not instance.unit_price:
            instance.unit_price = instance.product.price
            
        #Populate the dimension fields with instance dimensions if they are zero
        for field in ['width', 'depth', 'height']:
            if (getattr(instance, field) != getattr(instance.product, field) and 
                getattr(instance, field) == 0):
                setattr(instance, field, getattr(instance.product, field))
        
        #Calculate the total price of the item
        if instance.is_custom_size:
            instance._calculate_custom_price()
        else:
            instance.total = instance.quantity * instance.unit_price
        
        return instance
        
    def update(self, attrs, instance):
        """
        Updates the instance after the parent method is called
        """
        return super(ItemSerializer, self).restore_object(attrs, instance)
        
    def transform_fabric(self, obj, value):
        """
        Change output of fabric
        """
        try:
            return {'id': obj.fabric.id,
                    'color': obj.fabric.color,
                    'pattern': obj.fabric.pattern}
        except AttributeError:
            return None
        
        
class AcknowledgementSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField()
    employee = serializers.RelatedField()
    project = serializers.PrimaryKeyRelatedField(required=False)
    acknowledgement_pdf = serializers.RelatedField(required=False)
    production_pdf = serializers.RelatedField(required=False)
    original_acknowledgement_pdf = serializers.RelatedField(required=False)
    label_pdf = serializers.RelatedField(required=False)
    items = ItemSerializer(many=True)
    remarks = serializers.CharField(required=False)
    shipping_method = serializers.CharField(required=False)
    fob = serializers.CharField(required=False)
    pdf = serializers.SerializerMethodField('get_pdf')
    
    class Meta:
        model = Acknowledgement
        field = ('id', 'discount', 'delivery_date', 'status', 'remarks', 'vat')
        read_only_fields = ('total', 'subtotal', 'time_created')
        exclude = ('acknowledgement_pdf', 'production_pdf', 'original_acknowledgement_pdf',
                   'label_pdf')
        
    def froms_native(self, data, files=None):
        
        instance = super(AcknowledgementSerializer, self).from_native(data, files)
        logger.debug(self.errors)

        if "project" in data:
            try:
                instance.project = Project.objects.get(codename=data['project']['codename'])
            except Project.DoesNotExist:
                instance.project = Project(codename=data['project']['codename'])
                instance.project.save()
                
        return instance
        
    def get_pdf(self, obj):
        """
        Get the url to access the acknowledgement and production
        pdfs
        """
        try:
            return {'acknowledgement': obj.acknowledgement_pdf.generate_url(),
                    'production': obj.acknowledgement_pdf.generate_url()}
        except AttributeError:
            return {'acknowledgement': '',
                    'production': ''}
    
    def transform_customer(self, obj, value):
        """
        Transform the customer data before serialization
        """
        try:
            return {'id': obj.customer.id,
                    'name': obj.customer.name}
        except AttributeError:
                return None
    def transform_employee(self, obj, value):
        """
        Transform the employee data before serialization
        
        Change from unicode form to dict
        """
        return {'id': obj.employee.id}

    def transform_project(self, obj, value):
        
        try:
            return {'id': obj.project.id,
                    'codename': obj.project.codename}
        except AttributeError:
            return None
        
        
        
        
        
        
        
    