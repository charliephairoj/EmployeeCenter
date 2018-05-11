import logging
from decimal import Decimal
import pprint

from django.db import models
from rest_framework import serializers
from rest_framework.fields import DictField

from estimates.models import Estimate, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from administrator.serializers import UserFieldSerializer as EmployeeSerializer
from projects.serializers import ProjectFieldSerializer
from acknowledgements.serializers import AcknowledgementSerializer
from contacts.models import Customer
from products.models import Product
from supplies.models import Fabric, Log
from projects.models import Project
from media.models import S3Object
from media.serializers import S3ObjectFieldSerializer
from acknowledgements.models import Acknowledgement


logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=1, width=1)


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


class ItemListSerializer(serializers.ListSerializer):

    def xto_internal_value(self, data):
        logger.debug("\n\nItem List\n\n")
        logger.debug(data)
        return super(ItemListSerializer, self).to_internal_value(data)

    def xto_representation(self, data):
        logger.debug("\n\nItem List\n\n")
        logger.debug(isinstance(data, models.Manager))
        logger.debug(type(data))
        logger.debug(data)
        data = data.exclude(deleted=True)
        logger.debug(isinstance(data, models.Manager))
        data = data.select_related('image')
        data = data.prefetch_related('pillows')
        logger.debug(isinstance(data, models.Manager))
        data = super(ItemListSerializer, self).to_representation(data)

        logger.debug(data)

        

        return data


class ItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(required=False, queryset=Product.objects.all())
    pillows = PillowSerializer(required=False, many=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = S3ObjectFieldSerializer(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(decimal_places=2, max_digits=12, default=1)
    #custom_price = serializers.DecimalField(decimal_places=2, max_digits=12, write_only=True, required=False,
    #                                        allow_null=True)
    fabric_quantity = serializers.DecimalField(decimal_places=2, max_digits=12,
                                               write_only=True, required=False,
                                               allow_null=True)
    id = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ('description', 'id', 'width', 'depth', 'height', 'comments', 
                  'product', 'pillows', 'unit_price', 'fabric', 'image', 'units',
                  'quantity', 'fabric_quantity', 'type')
        read_only_fields = ('total',)
        list_serializer_class = ItemListSerializer

    def to_internal_value(self, data):
        ret = super(ItemSerializer, self).to_internal_value(data)

        try:
            ret['image'] = S3Object.objects.get(pk=data['image']['id'])
        except (KeyError, S3Object.DoesNotExist) as e:
            pass
        
        return ret

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        estimate = self.context['estimate']
        pillow_data = validated_data.pop('pillows', None)
        product = validated_data['product']
        unit_price = validated_data.pop('unit_price', validated_data.pop('price', product.price))
        width = validated_data.pop('width', product.width)
        depth = validated_data.pop('depth', product.depth)
        height = validated_data.pop('height', product.height)
        fabric_quantity = validated_data.pop('fabric_quantity', None)

        instance = self.Meta.model.objects.create(estimate=estimate, unit_price=unit_price,
                                                  width=width, depth=depth,
                                                  height=height, **validated_data)

        #attach fabric quantity
        instance.fabric_quantity = fabric_quantity

        #Calculate the total price of the item
        if instance.is_custom_size and product.price == unit_price:
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
        #instance = super(ItemSerializer, self).update(instance, validated_data)

        instance.image = validated_data.get('image', instance.image)
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.unit_price = validated_data.get('unit_price', instance.unit_price)
        instance.comments = validated_data.get('image', instance.comments)

        instance.save()

        return instance

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

        """
        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url()}
        except AttributeError:
            pass
        """

        return ret

"""
class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = File
        read_only_fields = ('acknowledgement', 'file')
""" 

class EstimateSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)

    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer = CustomerSerializer()#serializers.PrimaryKeyRelatedField()
    employee = EmployeeSerializer(required=False, read_only=True)#serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    project = ProjectFieldSerializer(allow_null=True, required=False) #serializers.PrimaryKeyRelatedField(required=False, allow_null=True)
    items = ItemSerializer(item_queryset, many=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    po_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shipping_method = serializers.CharField(required=False, allow_null=True)
    fob = serializers.CharField(required=False, allow_null=True)
    delivery_date = serializers.DateTimeField(required=True)
    #vat = serializers.DecimalField(required=False, allow_null=True)
    discount = serializers.IntegerField(required=False, allow_null=True)
    files = serializers.ListField(child=serializers.DictField(), required=False,
                                  allow_null=True)
    acknowledgement = AcknowledgementSerializer(required=False, allow_null=True) #serializers.PrimaryKeyRelatedField(allow_null=True, required=False)

    class Meta:
        model = Estimate
        read_only_fields = ('total', 'subtotal', 'time_created', 'employee')
        exclude = ('pdf', 'deal')
        depth = 1

    def to_internal_value(self, data):
        ret = super(EstimateSerializer, self).to_internal_value(data)

        try:
            ret['customer'] = Customer.objects.get(pk=data['customer']['id'])
        except (Customer.DoesNotExist, KeyError) as e:
            ret['customer'] = Customer.objects.create(**data['customer'])

        try:
            ret['project'] = Project.objects.get(pk=data['project']['id'])
        except (Project.DoesNotExist, KeyError, TypeError) as e:

            try:
                ret['project'] = Project.objects.create(**data['project'])
            except (TypeError) as e:
                logger.warn(e)
                try:
                    del ret['project']
                except Exception as e:
                    logger.warn(e)
            except KeyError as e:
                pass

        try:
            ret['acknowledgement'] = Project.objects.get(pk=data['acknowledgement']['id'])
        except (Customer.DoesNotExist, KeyError, TypeError) as e:
            pass

        logger.debug("\n\nEstimate to internal value\n\n")
        logger.debug(ret['items'])

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """
        items_data = self.initial_data['items']
        #files = validated_data.pop('files', [])

        for item_data in items_data:
            for field in ['product', 'fabric']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass

        try:
            discount = validated_data.pop('discount', validated_data['customer'].discount)
        except AttributeError as e:
            discount = 0

        try:
            files = validated_data.pop('files', [])
        except KeyError as e:
            files = []

        instance = self.Meta.model.objects.create(employee=self.context['request'].user, 
                                                  discount=discount,
                                                  status="open",
                                                  **validated_data)

        item_serializer = ItemSerializer(data=items_data, context={'estimate': instance}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()

        instance.calculate_totals()

        try:
            instance.create_and_update_deal()
        except Exception as e:
            logger.warn(e)
            
        instance.create_and_upload_pdf()
     
        #Assign files
        #for file in files:
        #    File.objects.create(file=S3Object.objects.get(pk=file['id']),
        #                        acknowledgement=instance)

        """
        #Extract fabric quantities
        fabrics = {}

        for item in item_serializer.instance:
            if item.fabric:
                if item.fabric in fabrics:
                    fabrics[item.fabric] += Decimal(str(item.quantity)) * item.fabric_quantity
                else:
                    fabrics[item.fabric] = Decimal(str(item.quantity)) * item.fabric_quantity

        #Log Fabric Reservations
        for fabric in fabrics:
            self.reserve_fabric(fabric, fabrics[fabric], instance.id)
        """

        return instance

    def update(self, instance, validated_data):

        instance.vat = validated_data.pop('vat', instance.vat)
        instance.discount = validated_data.pop('discount', instance.discount)
        instance.remarks = validated_data.pop('remarks', instance.remarks)
        instance.delivery_date = validated_data.pop('delivery_date', instance.delivery_date)
        #instance.project = validated_data.pop('project', instance.project)
        #Update attached files
        #files = validated_data.pop('files', [])
        #for file in files:
        #    try:
        #        File.objects.get(file_id=file['id'], acknowledgement=instance)
        #    except File.DoesNotExist:
        #        File.objects.create(file=S3Object.objects.get(pk=file['id']),
        #                            acknowledgement=instance)

        new_status = validated_data.pop('status', instance.status)
        logger.debug(new_status)
        logger.debug(instance.status)
        # Set the corresponding deal as closed lost
        if new_status.lower() != instance.status.lower() and new_status.lower() == 'cancelled':
            try:
                instance.deal.status = 'closed lost'
                instance.deal.save()
            except (AttributeError, TypeError) as e:
                logger.debug(e)

        instance.status = new_status

        items_data = validated_data.pop('items')

        self._update_items(instance, items_data)

        instance.save()

        instance.calculate_totals()

        instance.create_and_upload_pdf()

        instance.save()

        return instance

    def xto_representation(self, instance):
        """
        Override the default 'to_representation' method to customize the output data
        """
        ret = super(EstimateSerializer, self).to_representation(instance)

        
        ret['employee'] = {'id': instance.employee.id,
                           'name': "{0} {1}".format(instance.employee.first_name, instance.employee.last_name)}



        try:
            ret['files'] = [{'id': instance.id,
                             'filename': instance.pdf.key.split('/')[-1],
                             'url': instance.pdf.generate_url()}]
        except AttributeError as e:
            ret['files'] = []

        """
        try:
            ret['files'] += [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url()} for file in instance.files]
        except AttributeError as e:
            logger.warn(e)
        """

        return ret

    def _update_items(self, instance, items_data):
        """
        Handles creation, update, and deletion of items
        """
        #Maps of id
        id_list = [item_data.get('id', None) for item_data in items_data]

        #Delete Items
        for item in instance.items.all():
            if item.id not in id_list:
                item.deleted = True
                item.save()

        #Update or Create Item
        for item_data in items_data:
            try:
                item = Item.objects.get(pk=item_data['id'], estimate=instance)
                serializer = ItemSerializer(item, context={'customer': instance.customer, 'estimate': instance}, data=item_data)
            except (KeyError, Item.DoesNotExist) as e:
                serializer = ItemSerializer(data=item_data, context={'customer': instance.customer, 'estimate': instance})
                
            if serializer.is_valid(raise_exception=True):
                item = serializer.save()
                id_list.append(item.id)


            """ 
            item.estimate = instance
            item.width = item_data.get('width', item.width)
            item.depth = item_data.get('depth', item.depth)
            item.height = item_data.get('height', item.height)
            item.description = item_data.get('description', item.description)
            item.quantity = item_data.get('quantity', item.quantity)
            item.unit_price = item_data.get('unit_price', item.unit_price or item.product.price)
            item.comments = item_data.get('comments', item.comments)

            item.total = item.quantity * item.unit_price

          
                
            item.save()
            """
            """
            try:

                item = Item.objects.get(pk=item_data['id'])
                serializer = ItemSerializer(item, context={'customer': instance.customer, 'estimate': instance}, data=item_data)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()

                
                item.supply.supplier = instance.supplier
                item.discount = item_data.get('discount', None) or item.discount
                item.quantity = item_data.get('quantity', None) or item.quantity
                item.unit_cost = item_data.get('unit_cost', None) or item.unit_cost

                #Change the cost of the supply and log price change
                if item.unit_cost != item.supply.cost:
                    self._change_supply_cost(item.supply, item.unit_cost)

                item.calculate_total()
                item.save()
                
            except KeyError:
                item_data['product'] = item_data['product'].id
                serializer = ItemSerializer(data=item_data, context={'customer': instance.customer, 'estimate': instance})
                if serializer.is_valid(raise_exception=True):
                    item = serializer.save()
                    id_list.append(item.id)
            """
            
        
        
