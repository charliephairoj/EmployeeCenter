import logging

from rest_framework import serializers

from shipping.models import Shipping, Item
from acknowledgements.models import Acknowledgement, Item as AckItem
from contacts.serializers import CustomerSerializer


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=AckItem.objects.all())
    comments = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Item
        read_only_fields = ('shipping',)
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the shipping instance pass via the context
        """
        shipping = self.context['shipping']
        
        instance = self.Meta.model.objects.create(shipping=shipping, **validated_data)
        
        if instance.quantity == instance.item.quantity:
            instance.item.status = "SHIPPED"
            instance.item.save()
        
        return instance
    
class ShippingSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True)
    customer = CustomerSerializer(read_only=True)
    acknowledgement = serializers.PrimaryKeyRelatedField(queryset=Acknowledgement.objects.all())
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Shipping
        read_only_fields = ('employee',)
        exclude = ('pdf',)
    
    def create(self, validated_data):
        """
        Override the 'create' method in order to create items from nested data
        """ 
        items_data = validated_data.pop('items')
        for item_data in items_data:
            item_data['item'] = item_data['item'].id
            
        instance = self.Meta.model.objects.create(customer=validated_data['acknowledgement'].customer, 
                                                  employee=self.context['request'].user,
                                                  **validated_data)
        
        item_serializer = ItemSerializer(data=items_data, context={'shipping': instance}, many=True)
                
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        if instance.acknowledgement.items.count() == instance.acknowledgement.items.filter(status='SHIPPED').count():
            instance.acknowledgement.status = 'SHIPPED'
        else:
            instance.acknowledgement.status = 'PARTIALLY SHIPPED'
        instance.acknowledgement.save()    
        
        instance.create_and_upload_pdf()
        
        instance.save()
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method
        """
        delivery_date = validated_data.pop('delivery_date', instance.delivery_date)
        
        if instance.delivery_date != delivery_date:
            instance.delivery_date = delivery_date
            instance.acknowledgement.delivery_date = delivery_date
            instance.create_and_upload_pdf()
            instance.save()
        
        return instance
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method in order to customize the output of 
        customer and acknowledgement
        """
        ret = super(ShippingSerializer, self).to_representation(instance)
        
        try:
            ret['employee'] = {'id': instance.employee.id,
                               'name': instance.employee.name}
        except:
            pass
            
        ret['acknowledgement'] = {'id': instance.acknowledgement.id}
        
        try:
            ret['acknowledgement']['project'] = {'id': instance.acknowledgement.project.id,
                                                 'codename': instance.acknowledgement.project.codename}
        except AttributeError:
            pass
            
        try:
            ret['pdf'] = {'url': instance.pdf.generate_url()}
        except AttributeError:
            pass
       
        return ret
                         
        
    
