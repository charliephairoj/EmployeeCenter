import logging

from rest_framework import serializers

from acknowledgements.models import Acknowledgement, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.models import Product
from supplies.models import Fabric


logger = logging.getLogger(__name__)


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.RelatedField(required=False)
    quantity = serializers.RelatedField()
    
    class Meta:
        model = Pillow
        field = ('type', 'fabric')
        read_only_fields = ('item',)
            
    def from_native(self, data, files):
        instance = super(PillowSerializer, self).from_native(data, files)
        
        if "fabric" in data:
            try:
                instance.fabric = Fabric.objects.get(pk=data['fabric']['id'])
            except:
                pass
                
        return instance
        
        
class ItemSerializer(serializers.ModelSerializer):
    pillows = PillowSerializer(required=False, many=True)
    unit_price = serializers.RelatedField(required=False)
    comments = serializers.RelatedField(required=False)
    location = serializers.RelatedField(required=False)
    fabric = serializers.RelatedField(required=False)
    width = serializers.RelatedField()
    depth = serializers.RelatedField()
    height = serializers.RelatedField()
    
    class Meta:
        model = Item
        field = ('description', 'id')
        read_only_fields = ('acknowledgement', 'total', 'image', 'type', 'product')
        
    def from_native(self, data, files=None):
        
        instance = super(ItemSerializer, self).from_native(data, files)
        
        #Apply base product details
        if "fabric" in data:
            fabric = Fabric.objects.get(pk=data['fabric']['id'])
            instance.fabric = fabric
            
        if "product" in data:
            instance.product = Product.objects.get(pk=data['product']['id'])
            
            #Set Width
            try:
                if int(data['width']) == 0:
                    instance.width = instance.product.width
                else:
                    instance.width = data['width']
            except KeyError:
                instance.width = instance.product.width
              
            #Set Depth 
            try:
                if int(data['depth']) == 0:
                    instance.depth = instance.product.depth
                else:
                    instance.depth = data['depth']
            except KeyError:
                instance.depth = instance.product.depth
            
            #Set Height    
            try:
                if int(data['height']) == 0:
                    instance.height = instance.product.height
                else: 
                    instance.height = data['height']
            except KeyError:
                instance.height = instance.product.height
            
            #Set unit price
            try:
                if int(data['unit_price']) == 0:
                    instance.unit_price = instance.product.price
            except KeyError:
                instance.unit_price = instance.product.price
        
        instance._calculate_custom_price()
        
        return instance
        
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
    customer = CustomerSerializer(read_only=True)
    employee = serializers.RelatedField()
    project = serializers.RelatedField(required=False)
    acknowledgement_pdf = serializers.RelatedField(required=False)
    production_pdf = serializers.RelatedField(required=False)
    original_acknowledgement_pdf = serializers.RelatedField(required=False)
    label_pdf = serializers.RelatedField(required=False)
    items = ItemSerializer(many=True)
    remarks = serializers.CharField(required=False)
    shipping_method = serializers.CharField(required=False)
    fob = serializers.CharField(required=False)
    
    class Meta:
        model = Acknowledgement
        field = ('id', 'discount', 'delivery_date', 'status', 'remarks', 'vat')
        read_only_fields = ('total', 'subtotal', 'time_created')
        
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
        
        
        
        
        
        
        
    