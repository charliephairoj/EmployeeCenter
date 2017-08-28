import logging

from rest_framework import serializers

from shipping.models import Shipping, Item
from acknowledgements.models import Acknowledgement, Item as AckItem
from contacts.models import Customer
from contacts.serializers import CustomerSerializer
from projects.models import Project, Phase


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    item = serializers.PrimaryKeyRelatedField(queryset=AckItem.objects.all(), required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Item
        read_only_fields = ('shipping',)
        fields = ('description', 'quantity', 'comments', 'gross_weight', 'net_weight', 'item', 'id')
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the shipping instance pass via the context
        """
        shipping = self.context['shipping']
        
        instance = self.Meta.model.objects.create(shipping=shipping, **validated_data)
        
        if instance.item:
            if instance.quantity == instance.item.quantity:
                instance.item.status = "SHIPPED"
                instance.item.save()
        
        return instance
    
    
class ShippingSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), 
                                                  required=True, allow_null=False)
    #customer = CustomerSerializer(read_only=True)
    acknowledgement = serializers.PrimaryKeyRelatedField(queryset=Acknowledgement.objects.all(), required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    #project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all(), allow_null=True, required=False)
    #phase = serializers.PrimaryKeyRelatedField(queryset=Phase.objects.all(), required=False, allow_null=True)
    
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
            # add try and except that so new items no longer require a preapprove
            # product before creation
            try:
                item_data['item'] = item_data['item'].id
            except KeyError as e:
                item_data['item'] = None
        logger.debug(validated_data)
        try:
            instance = self.Meta.model.objects.create(employee=self.context['request'].user,
                                                      **validated_data)
        except AttributeError:
            instance = self.Meta.model.objects.create(employee=self.context['request'].user, **validated_data)
        
            
        item_serializer = ItemSerializer(data=items_data, context={'shipping': instance}, many=True)
                
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        """    
        if instance.acknowledgement:
            if instance.acknowledgement.items.count() == instance.acknowledgement.items.filter(status='SHIPPED').count():
                instance.acknowledgement.status = 'SHIPPED'
            else:
                instance.acknowledgement.status = 'PARTIALLY SHIPPED'
            instance.acknowledgement.save()    
        """
        
        instance.create_and_upload_pdf()
        
        instance.save()
        
        # Update the delivery date for the acknowledgement
        # Tries as there maybe shipping documents with no corresponding 
        # Acknowledgements
        try:
            instance.acknowledgement.delivery_date = instance.delivery_date
            instance.acknowledgement.save()
        except AttributeError as e:
            pass
        
        # Update the calendar event
        try:
            instance.acknowledgement.update_calendar_event()
        except Exception as e:
            logger.warn(e)
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method
        """
        delivery_date = validated_data.pop('delivery_date', instance.delivery_date)
        
        items_data = validated_data.pop('items', [])
        
        for item_data in items_data:
            try:
                item_data['item'] = item_data['item']['id']
            except KeyError:
                pass
            except TypeError:
                item_data['item'] = item_data['item'].id
                
            item = Item.objects.get(pk=item_data['id'])
            item_serializer = ItemSerializer(item, data=item_data, context={'shipping': instance})
            if item_serializer.is_valid(raise_exception=True):
                item_serializer.save()
                
        if instance.delivery_date != delivery_date:
            instance.delivery_date = delivery_date
            instance.acknowledgement.delivery_date = delivery_date
            instance.create_and_upload_pdf()
            instance.save()
            
            # Update the delivery date for the acknowledgement
            instance.acknowledgement.delivery_date = instance.delivery_date
            instance.acknowledgement.save()
        
            # Update the calendar event
            try:
                instance.acknowledgement.update_calendar_event()
            except Exception as e:
                logger.warn(e)
            
        
        return instance
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method in order to customize the output of 
        customer and acknowledgement
        """
        ret = super(ShippingSerializer, self).to_representation(instance)
        
        ret['customer'] = {'id': instance.customer.id,
                           'name': instance.customer.name}

        try:
            ret['employee'] = {'id': instance.employee.id,
                               'name': instance.employee.name}
        except:
            pass
            
        try:
            ret['acknowledgement'] = {'id': instance.acknowledgement.id}
        except AttributeError:
            pass
            
        try:
            ret['acknowledgement']['project'] = {'id': instance.acknowledgement.project.id,
                                                 'codename': instance.acknowledgement.project.codename}
        except AttributeError:
            pass
        
        
        
        try:
            iam_credentials = self.context['request'].user.aws_credentials
            key = iam_credentials.access_key_id
            secret = iam_credentials.secret_access_key
            ret['pdf'] = {'url': instance.pdf.generate_url(key, secret)}
        except AttributeError as e:
            logger.warn(e)
       
        return ret
                         
        
    
