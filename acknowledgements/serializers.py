import logging
from decimal import Decimal

from rest_framework import serializers

from acknowledgements.models import Acknowledgement, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from contacts.models import Customer
from products.models import Product
from supplies.models import Fabric
from projects.models import Project
from media.models import S3Object
from administrator.models import User


logger = logging.getLogger(__name__)


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    
    class Meta:
        model = Pillow
        field = ('type', 'fabric', 'quantity')
        exclude = ('item',)
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']
        
        instance = self.Meta.model.objects.create(item=item, **validated_data)
        
        return instance
        
        
class ItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    pillows = PillowSerializer(required=False, many=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    comments = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = serializers.PrimaryKeyRelatedField(required=False, queryset=S3Object.objects.all())
    units = serializers.CharField(required=False)
   
    class Meta:
        model = Item
        field = ('description', 'id', 'width', 'depth', 'height')
        read_only_fields = ('total', 'type')
        exclude = ('acknowledgement', )
        
    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is 
        called. 
        """
        acknowledgement = self.context['acknowledgement']
        pillow_data = validated_data.pop('pillows', None)      
        product = validated_data['product']
        unit_price = validated_data.pop('unit_price', None) or product.price
        width = validated_data.pop('width', None) or product.width
        depth = validated_data.pop('depth', None) or product.depth
        height = validated_data.pop('height', None) or product.height
        
        
        instance = self.Meta.model.objects.create(acknowledgement=acknowledgement, unit_price=unit_price, 
                                                  width=width, depth=depth, 
                                                  height=height, **validated_data)
        
        #Calculate the total price of the item
        if instance.is_custom_size:
            instance._calculate_custom_price()
        else:
            instance.total = instance.quantity * instance.unit_price
        
        instance.save()
        
        if pillow_data:
            pillow_serializer = PillowSerializer(data=pillow_data, context={'item': instance}, many=True)
        
            if pillow_serializer.is_valid(raise_exception=True):
                pillow_serializer.save()
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """
        return super(ItemSerializer, self).update(instance, validated_data)
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method to transform the output for related and nested items
        """
        ret = super(ItemSerializer, self).to_representation(instance)
        
        try:
            ret['fabric'] = {'id': instance.fabric.id,
                             'description': instance.fabric.description}
        except AttributeError:
            pass
            
        try:
            ret['image'] = {'url': instance.image.generate_url()}
        except AttributeError:
            pass
            
        return ret
        
        
class AcknowledgementSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    employee = serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    project = serializers.PrimaryKeyRelatedField(required=False, queryset=Project.objects.all())
    items = ItemSerializer(many=True)
    remarks = serializers.CharField(required=False)
    shipping_method = serializers.CharField(required=False)
    fob = serializers.CharField(required=False)
    
    class Meta:
        model = Acknowledgement
        read_only_fields = ('total', 'subtotal', 'time_created') 
        exclude = ('acknowledgement_pdf', 'production_pdf', 'original_acknowledgement_pdf', 'label_pdf')
       
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """
        
        items_data = validated_data.pop('items')
        
        for item_data in items_data:
            for field in ['product', 'fabric', 'image']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
        
        discount = validated_data.pop('discount', None) or validated_data['customer'].discount
        
        instance = self.Meta.model.objects.create(employee=self.context['request'].user, discount=discount,
                                                  **validated_data)
        
        item_serializer = ItemSerializer(data=items_data, context={'acknowledgement': instance}, many=True)
        
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
        
        instance.calculate_totals()
        
        #instance.create_and_upload_pdfs()
        
        return instance
        
    def update(self, instance, validated_data):
        
        return instance
        
    def to_representation(self, instance):
        """
        Override the default 'to_representation' method to customize the output data
        """
        ret = super(AcknowledgementSerializer, self).to_representation(instance)
        
        ret['customer'] = {'id': instance.customer.id, 
                           'name': instance.customer.name}
                           
        ret['employee'] = {'id': instance.employee.id,
                           'name': "{0} {1}".format(instance.employee.first_name, instance.employee.last_name)}
                           
        try:
            ret['project'] = {'id': instance.project.id,
                              'codename': instance.project.codename}
        except AttributeError:
            pass
            
        try:
            ret['pdf'] = {'acknowledgement': instance.acknowledgement_pdf.generate_url(),
                          'production': instance.production_pdf.generate_url()}
        except AttributeError:
            ret['pdf'] = {'acknowledgement': 'test',
                          'production': 'test'}
                          
        return ret
        
        
        
        
        
    