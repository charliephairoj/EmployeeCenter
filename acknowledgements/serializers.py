#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
import traceback

import boto
from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import DictField
from pytz import timezone
from django.utils import timezone as tz

from administrator.models import User
from administrator.serializers import UserFieldSerializer, LogSerializer, LogFieldSerializer, CompanyDefault, BaseLogSerializer
from acknowledgements.models import Acknowledgement, Item, Pillow, Component, File, Log as AckLog
from contacts.serializers import CustomerOrderFieldSerializer, CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from projects.serializers import ProjectFieldSerializer, RoomFieldSerializer, PhaseFieldSerializer
from media.serializers import S3ObjectFieldSerializer
from contacts.models import Customer
from products.models import Product
from supplies.models import Fabric, Log
from projects.models import Project, Phase, Room
from media.models import S3Object
from acknowledgements import service as ack_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DefaultAcknowledgement(object):
    def set_context(self, serializer_field):
        if 'acknowledgement' in serializer_field.context:
            self.acknowledgement = serializer_field.context['acknowledgement']
        else:
            self.acknowledgement = serializer_field.parent.parent.instance

        logger.debug(self.acknowledgement)

    def __call__(self):
        return self.acknowledgement


class AcknowledgementLogSerializer(BaseLogSerializer):
    acknowledgement = serializers.HiddenField(default=DefaultAcknowledgement())
    type = serializers.CharField(default=serializers.CreateOnlyDefault('SALES ORDER'))

    class Meta:
        model = AckLog
        depth = 1
        fields = ('id', 'message', 'timestamp', 'user', 'company', 'type', 'acknowledgement')


class ComponentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Component
        fields = ('id', 'description', 'quantity')

    def create (self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']
        instance = self.Meta.model.objects.create(item=item, **validated_data)
        return instance

    def to_representation(self, instance):
        ret = super(ComponentSerializer, self).to_representation(instance)
        
        return ret


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    fabric_quantity = serializers.DecimalField(required=False, allow_null=True, decimal_places=2, max_digits=12)

    class Meta:
        model = Pillow
        fields = ('type', 'fabric', 'quantity', 'fabric_quantity')

    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']

        instance = self.Meta.model.objects.create(item=item, **validated_data)

        return instance

    def to_representation(self, instance):
        ret = super(PillowSerializer, self).to_representation(instance)

        try:
            ret['fabric'] = {'id': instance.fabric.id,
                             'description': instance.fabric.description}
        except AttributeError:
            pass

        return ret


class ItemListSerializer(serializers.ListSerializer):
    def update(self, instances, validated_data):
        logger.debug(validated_data)
        item_mapping = {item.id: item for item in instances}
        data_mapping = {d.get('id', d['description']): d for d in validated_data}

        ret = []

        for item_id, data in data_mapping.items():
            item = item_mapping.get(item_id, None)
            if item is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(item, data))

        # Perform deletions.
        for item_id, item in item_mapping.items():
            if item_id not in data_mapping:
                item.delete()

        return ret


class ItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    # Business Fields
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, default=0)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, default='acknowledged')
    #location = serializers.CharField(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    fabric_quantity = serializers.DecimalField(decimal_places=2, max_digits=12, required=False,
                                               allow_null=True)
    quantity = serializers.DecimalField(decimal_places=2,
                                        max_digits=12,
                                        min_value=1)
    type = serializers.CharField(required=False, allow_null=True)

    # Nested Relationships
    product = ProductSerializer(required=False, allow_null=True)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = S3ObjectFieldSerializer(required=False, allow_null=True)

    # Nested Many Relationship
    pillows = PillowSerializer(required=False, many=True)
    components = ComponentSerializer(required=False, many=True)

    # Non Model Properties
    grades = {'A1': 15,
              'A2': 20,
              'A3': 25,
              'A4': 30,
              'A5': 35,
              'A6': 40}

    class Meta:
        model = Item
        fields = ('description', 'id', 'width', 'depth', 'height', 'fabric_quantity', 'unit_price', 'total', 'product',
                  'pillows', 'comments', 'image', 'units', 'fabric', 'quantity', 'components', 'type',
                  'status')
        read_only_fields = ('total',)
        list_serializer_class = ItemListSerializer

    @classmethod
    def many_init(cls, *args, **kwargs):
        # Instantiate the child serializer.
        kwargs['child'] = cls()
        # Instantiate the parent list serializer.
        return cls.Meta.list_serializer_class(*args, **kwargs)

    def to_internal_value(self, data):
        ret = super(ItemSerializer, self).to_internal_value(data)

        try:
            ret['product'] = Product.objects.get(pk=data['product']['id'])
        except (KeyError, Product.DoesNotExist, TypeError) as e:
            try:
                ret['product'] = Product.objects.get(description=data['description'])
            except (Product.DoesNotExist) as e:
                try:
                    ret['product'] = Product.objects.get(pk=10436)
                except Product.DoesNotExist as e:
                    ret['product'] = Product.objects.create()

        try:
            ret['image'] = S3Object.objects.get(pk=data['image']['id'])
        except (KeyError, S3Object.DoesNotExist, TypeError) as e:
            if "image" in ret:
                del ret['image']
        
        return ret

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        components_data = validated_data.pop('components', None)
        pillow_data = validated_data.pop('pillows', None)
        product = validated_data['product']

        width = validated_data.pop('width', None) or product.width
        depth = validated_data.pop('depth', None) or product.depth
        height = validated_data.pop('height', None) or product.height

        instance = self.Meta.model.objects.create(acknowledgement=self.context['acknowledgement'], 
                                                  width=width, depth=depth,
                                                  height=height, **validated_data)

        #Calculate the total price of the item
        self._calculate_total(instance)

        instance.save()

        if pillow_data:
            pillow_serializer = PillowSerializer(data=pillow_data, context={'item': instance}, many=True)

            if pillow_serializer.is_valid(raise_exception=True):
                pillow_serializer.save()

        if components_data:
            component_serializer = ComponentSerializer(data=components_data, context={'item': instance}, many=True)

            if component_serializer.is_valid(raise_exception=True):
                component_serializer.save()

        return instance

    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """
        # Loops through attributes and logs changes
        updatable_attributes = ['quantity', 'unit_price', 'description', 'fabric', 
                                'comments', 'width', 'depth', 'height', 'status']

        for attr in updatable_attributes:
            new_attr_value = validated_data.pop(attr, getattr(instance, attr))

            if getattr(instance, attr) != new_attr_value:
                old_attr_value = getattr(instance, attr)
                setattr(instance, attr, new_attr_value)

                # Log data changes
                message = u"{0}: {1} changed from {2} to {3}"
                message = message.format(instance.description, attr, old_attr_value, new_attr_value)
                ack_service.log(message, instance.acknowledgement, self.context['request'])


        # Set the price of the total for this item
        self._calculate_total(instance)
        instance.save()

        pillows = validated_data.pop('pillows', [])
        for pillow_data in pillows:
            try:
                pillow = Pillow.objects.get(type=pillow_data['type'], item=instance, fabric=pillow_data['fabric'])
                serializer = PillowSerializer(pillow, data=pillow_data)
            except Pillow.DoesNotExist as e:
                serializer = PillowSerializer(data=pillow_data, context={'item': instance})

            if serializer.is_valid(raise_exception=True):
                serializer.save()

        components = validated_data.pop('components', [])
        for component_data in components:
            try:
                component = Component.objects.get(id=component_data['id'], item=instance)
                serializer = ComponentSerializer(component, data=component_data)
            except KeyError as e:
                logger.debug(e)
                serializer = ComponentSerializer(data=component_data, context={'item': instance})

            if serializer.is_valid(raise_exception=True):
                serializer.save()

        return instance

    def _calculate_total(self, instance):
        """
        Calculate the total of the instance
        """
        total = instance.quantity * (instance.unit_price or 0)
        instance.total = total

        return instance.total



class ItemFieldSerializer(serializers.ModelSerializer):
   
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    quantity = serializers.DecimalField(required=False, decimal_places=2, max_digits=15)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ('description', 'id', 'width', 'depth', 'height', 'unit_price', 'quantity')



class FileListSerializer(serializers.ListSerializer):
    def update(self, instances, validated_data):
        """
        Update List of Files

        1. List of ids
        2. Delete
        3. Create
        """

        data_id_list = [d['file'].get('id', None) for d in validated_data]
        instance_id_list = [f.file.id for f in instances]

        ret = []
        # Delete Files
        for f in instances:
            if f.file.id not in valid_id_list:
                f.delete()
            else:
                ret.append(f)

        # Add Files
        for d in validated_data:
            if d['file'].get('id', None) not in instance_id_list:
                ret.append(self.child.create(d))

        return ret


class FileSerializer(serializers.ModelSerializer):
    acknowledgement = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultAcknowledgement))
    file = S3ObjectFieldSerializer()

    class Meta:
        model = File
        fields = '__all__'
        list_serializer_class = FileListSerializer

    @classmethod
    def many_init(cls, *args, **kwargs):
        # Instantiate the child serializer.
        kwargs['child'] = cls()
        # Instantiate the parent list serializer.
        return cls.Meta.list_serializer_class(*args, **kwargs)



class AcknowledgementSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)

    # Internal Fields
    company = serializers.HiddenField(default=serializers.CreateOnlyDefault(CompanyDefault))
    employee = UserFieldSerializer(read_only=True, default=serializers.CurrentUserDefault())

    #Business Fields
    company_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer_name = serializers.CharField(default="")
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shipping_method = serializers.CharField(required=False, allow_null=True)
    fob = serializers.CharField(required=False, allow_null=True)
    delivery_date = serializers.DateTimeField(required=True, default_timezone=timezone('Asia/Bangkok'))
    balance = serializers.DecimalField(read_only=True, decimal_places=2, max_digits=15)

    # Nested Fields
    customer = CustomerOrderFieldSerializer()
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    phase = PhaseFieldSerializer(allow_null=True, required=False)

    # Nested Many Fields
    items = ItemSerializer(item_queryset, many=True)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    logs = LogFieldSerializer(many=True, read_only=True)
    
    # Method Fields
    invoices = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Acknowledgement
        read_only_fields = ('total', 'subtotal', 'time_created', 'logs', 'balance')
        exclude = ('acknowledgement_pdf', 'production_pdf', 'original_acknowledgement_pdf', 'label_pdf', 'trcloud_id',
                   'trcloud_document_number')
        depth = 3

    def to_internal_value(self, data):
        ret = super(AcknowledgementSerializer, self).to_internal_value(data)

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
                logger.debug(ret['project'])
                try:
                    del ret['project']
                except Exception as e:
                    logger.warn(e)
            except KeyError as e:
                pass

        logger.debug("\n\nAcknowledgement to internal value\n\n")

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """

        #Discard STatus
        status = validated_data.pop('status', 'acknowledged')
        
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        files = validated_data.pop('files', [])
                
        for item_data in items_data:
            for field in ['fabric']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass

        discount = validated_data.pop('discount', validated_data['customer'].discount)

        instance = self.Meta.model.objects.create(discount=discount,
                                                  status='acknowledged',
                                                  **validated_data)
        self.instance = instance

        item_serializer = ItemSerializer(data=items_data, context={'acknowledgement': instance, request:self.context['request']}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()


        instance.calculate_totals()

        instance.create_and_upload_pdfs()
        
        # Add pdfs to files list
        filenames = ['acknowledgement_pdf', 'production_pdf', 'label_pdf']
        for filename in filenames:
            self._add_file(getattr(instance, filename))
           
        # Add files
        for file in files:
            self._add_file(S3Object.objects.get(pk=file['id']))

        # Create a calendar event
        try:
            instance.create_calendar_event(employee)
        except Exception as e:
            message = u"Unable to create calendar event for acknowledgement {0} because:\n{1}"
            message = message.format(instance.document_number, e)
            self._log(message, instance, self.context['request'])

        # Log Opening of an order
        message = u"Created Sales Order #{0}.".format(instance.document_number)
        self._log(message, instance, self.context['request'])
                
        return instance

    def update(self, instance, validated_data):

        attrs_to_update = {'delivery_date': lambda x : x.strftime('%d/%m/%Y'),
                           'status': lambda x : x.lower(),
                           'project': None,
                           'vat': None,
                           'discount': None}

        for attr, attr_formatting in attrs_to_update.items():
            self._update_attr(instance, attr, validated_data, attr_formatting)
        
        # Extract items data
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        fabrics = {}
        logger.debug(items_data)
        items_serializer = ItemSerializer(instance=instance.items.all(), 
                                          data=items_data,
                                          many=True, 
                                          context={'request': self.context['request'],
                                                   'acknowledgement': instance,
                                                   'employee': self.context['request'].user,
                                                   'customer': instance.customer})

        if items_serializer.is_valid(raise_exception=True):
            items_serializer.save()
        
        #Update attached files
        files_data = validated_data.pop('files', None)
        if files_data:
            files_data = [{'file': f} for f in files_data]
            files_serializer = FileSerializer(File.objects.filter(acknowledgement=instance),
                                            data=files_data, 
                                            context={'request': self.context['request'],
                                                    'acknowledgement': instance},
                                            many=True)

        # Store old total and calculate new total
        instance.calculate_totals()

        try:
            instance.create_and_upload_pdfs()
        except IOError as e:

        
            tb = traceback.format_exc()
            logger.error(tb)
            
            message = u"Unable to update PDF for acknowledgement {0} because:\n{1}"
            message = message.format(instance.id, e)
            self._log(message, instance)

        try:
            instance.update_calendar_event()
        except Exception as e:
            logger.debug(e)
            message = u"Unable to update calendar event for acknowledgement {0} because:\n{1}"
            message = message.format(instance.id, e)
            self._log(message, instance)

        instance.save()

        return instance

    def get_invoices(self, instance):

        data = [
            {
                'id': inv.id,
                'grand_total': inv.grand_total
            }
        for inv in instance.invoices.all()]

        return data

    def reserve_fabric(self, fabric, quantity, acknowledgement_id, employee=None):
        """
        Internal method to apply the new quantity to the obj and
        create or update a log of the quantity change
        """



        #Create log to track quantity changes
        try:
            log = Log.objects.get(acknowledgement_id=acknowledgement_id, supply_id=fabric.id)
        except Log.DoesNotExist:
            log = Log(supply=fabric, acknowledgement_id=acknowledgement_id)

        # Get log quantity for fabric cut later
        original_qty = log.quantity or 0

        # Set log attributes
        log.action = "RESERVE"
        log.quantity = quantity
        log.employee = employee
        log.message = u"Reserve {0}{1} of {2} for Ack#{3}".format(quantity,
                                                                  fabric.units,
                                                                  fabric.description,
                                                                  acknowledgement_id)

        # Save log
        log.save()

    def _add_file(self, file):
        """
        Adds a file to the acknowledgement
        """
        File.objects.create(acknowledgement=self.instance, 
                            file=file)
        
        # Log addition of file
        msg = u"Added '{0}' to Sales Order #{1} files"
        msg = msg.format(file.filename, self.instance.document_number)
        self._log(msg)

    def _update_attr(self, instance, attr_name, data_mapping, format=None):
        """
        Update Attribute in instance if there is a change
        """
        new_val = data_mapping.get(attr_name, getattr(instance, attr_name))
        old_val = getattr(instance, attr_name)

        # Format if callable is set
        if callable(format):
            new_val = format(new_val)
            old_val = format(old_val)

        if old_val != new_val:
            setattr(instance, attr_name, data_mapping.get(attr_name, getattr(instance, attr_name)))
            msg = u"{0} for Sales Order # {1} changed from {2} to {3}"
            msg = msg.format(attr_name, instance.document_number, old_val, new_val)
            self._log(msg)

    def _log(self, message, instance=None):
        """
        Create Acknowledgement link Log
        """
        if not isinstance(instance, self.Meta.model):
            instance = self.instance

        serializer = AcknowledgementLogSerializer(data={'message': message}, 
                                                  context={'acknowledgement': instance,
                                                           'request': self.context['request']})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
        



"""
Field Serializers
"""


class AcknowledgementFieldSerializer(serializers.ModelSerializer):
    project = ProjectFieldSerializer(required=False, read_only=True)
    balance = serializers.DecimalField(read_only=True, decimal_places=2, max_digits=15)

    class Meta:
        model = Acknowledgement
        fields = ('id', 'remarks', 'fob', 'shipping_method', 'delivery_date', 
                  'total', 'subtotal', 'time_created', 'project', 'status', 'balance')
        read_only_fields = ('project', 'balance')

