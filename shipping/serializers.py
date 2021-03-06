import logging

from rest_framework import serializers
from administrator.models import User
from administrator.serializers import UserFieldSerializer as EmployeeSerializer
from shipping.models import Shipping, Item
from acknowledgements.models import Acknowledgement, Item as AckItem
from acknowledgements.serializers import ItemFieldSerializer as AckItemFieldSerializer, AcknowledgementFieldSerializer
from contacts.models import Customer
from contacts.serializers import CustomerSerializer, CustomerFieldSerializer
from projects.models import Project, Phase, Room
from projects.serializers import ProjectFieldSerializer, RoomFieldSerializer
from media.serializers import S3ObjectFieldSerializer
from acknowledgements import service as ack_service


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    item = AckItemFieldSerializer(required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Item
        read_only_fields = ('shipping',)
        fields = ('description', 'quantity', 'comments', 'gross_weight', 'net_weight', 'item', 'id')
    
    def to_internal_value(self, data):

        ret = super(ItemSerializer, self).to_internal_value(data)

        try:
            ret['item'] = ack_service.get_item(pk=data['item']['id'])
        except KeyError as e:
            pass
        except AckItem.DoesNotExist as e:
            logger.warn(e)

        return ret

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
    items = ItemSerializer(many=True, required=True)
    customer = CustomerSerializer(required=True)
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pdf = S3ObjectFieldSerializer(read_only=True, required=False)
    employee = EmployeeSerializer(required=False, read_only=True)

    class Meta:
        model = Shipping
        fields = '__all__'
    
    def to_internal_value(self, data):
        ret = super(ShippingSerializer, self).to_internal_value(data)

        try:
            ret['customer'] = Customer.objects.get(pk=data['customer']['id'])
        except (Customer.DoesNotExist, KeyError) as e:
            try:
                ret['customer'] = Customer.objects.get(name=data['customer']['name'])
            except Customer.DoesNotExist as e:
                ret['customer'] = Customer.objects.create(**data['customer'])
            except Customer.MultipleObjectsReturned as e:
                logger.warn(e)

        library = {'project': Project, 
                   'room': Room,
                   'phase': Phase}
        for key  in library:
            try:
                ret[key] = library[key].objects.get(pk=data[key]['id'])
            except (library[key].DoesNotExist, KeyError, TypeError) as e:

                try:
                    ret[key] = library[key].objects.create(**data[key])
                except (KeyError, TypeError) as e:
                    pass
        
        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError, TypeError) as e:
            try:
                del ret['acknowledgement']
            except KeyError as e: 
                pass

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create items from nested data
        """ 
        employee = self.context['request'].user

        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        
        try:
            instance = self.Meta.model.objects.create(employee=employee,
                                                      **validated_data)
        except AttributeError:
            instance = self.Meta.model.objects.create(employee=employee, **validated_data)
        
        instance.comments = validated_data.pop('comments', instance.comments)
        instance.save()
            
        item_serializer = ItemSerializer(data=items_data, context={'shipping': instance}, many=True)
                
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        
        if instance.acknowledgement:
            if instance.acknowledgement.items.count() == instance.acknowledgement.items.filter(status='SHIPPED').count():
                instance.acknowledgement.status = 'SHIPPED'
            else:
                instance.acknowledgement.status = 'PARTIALLY SHIPPED'
            instance.acknowledgement.save()    
        
        instance.create_and_upload_pdf()
        
        instance.save()

        # Add Shipping Doc to Ack
        if instance.acknowledgement:
            ack_service.add_file(acknowledgement=instance.acknowledgement, 
                                 media_obj=instance.pdf)
        
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
        instance.comments = validated_data.pop('comments', instance.comments)

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
            
            # Update the delivery date for the acknowledgement
            instance.acknowledgement.delivery_date = instance.delivery_date
            instance.acknowledgement.save()
        
            # Update the calendar event
            try:
                instance.acknowledgement.update_calendar_event()
            except Exception as e:
                logger.warn(e)


        instance.create_and_upload_pdf()
        instance.save()


        return instance
        
    def xto_representation(self, instance):
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
            ret['acknowledgement'] = {'id': instance.acknowledgement.id,
                                      'status': instance.acknowledgement.status}
        except AttributeError:
            pass
            
        try:
            ret['project'] = {'id': instance.project.id or instance.acknowledgement.project.id,
                              'codename': instance.project.codename or instance.acknowledgement.project.codename}
        except AttributeError:
            pass

        try:
            ret['room'] = {'id': instance.room.id,
                            'description': instance.room.description}
        except AttributeError:
            pass
        
        
        try:
            ret['pdf'] = {'id': instance.pdf.id,
                          'filename': instance.pdf.key.split('/')[-1],
                          'url': instance.pdf.generate_url()}
        except AttributeError as e:
            logger.warn(e)
       
        return ret
                         
        
    
