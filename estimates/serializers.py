#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
import pprint
from datetime import datetime

from django.db import models
from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import DictField

from estimates.models import Estimate, Item, Pillow, File
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from administrator.serializers import UserFieldSerializer as EmployeeSerializer
from projects.serializers import ProjectFieldSerializer as ProjectSerializer
from acknowledgements.serializers import AcknowledgementFieldSerializer as AcknowledgementSerializer
from contacts.models import Customer
from administrator.models import User
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
    product = ProductSerializer(required=False, allow_null=True)
    pillows = PillowSerializer(required=False, many=True)
    
    comments = serializers.CharField(default='', allow_blank=True, allow_null=True)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = S3ObjectFieldSerializer(required=False, allow_null=True)
    units = serializers.CharField(default='mm', allow_null=True)
    width = serializers.IntegerField(default=0)
    depth = serializers.IntegerField(default=0)
    height = serializers.IntegerField(default=0)
    
    #custom_price = serializers.DecimalField(decimal_places=2, max_digits=12, write_only=True, required=False,
    #                                        allow_null=True)
    fabric_quantity = serializers.DecimalField(decimal_places=2, max_digits=12,
                                               write_only=True, required=False,
                                               allow_null=True)
    type = serializers.CharField(required=False, allow_null=True)

    # Price Related
    unit_price = serializers.DecimalField(default=0, min_value=0, decimal_places=2, max_digits=12)
    quantity = serializers.DecimalField(decimal_places=2, max_digits=12, default=1, min_value=1)
    
    class Meta:
        model = Item
        exclude = ('location', 'inventory')
        read_only_fields = ('total', 'estimate')
        list_serializer_class = ItemListSerializer

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
            del ret['image']
        
        return ret

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        estimate = self.context['estimate']
        product = validated_data['product']
        logger.debug(product)
        pillow_data = validated_data.pop('pillows', None)
        unit_price = validated_data.pop('unit_price', validated_data.pop('price', product.price))
        width = validated_data.pop('width') or product.width
        depth = validated_data.pop('depth') or product.depth
        height = validated_data.pop('height') or product.height
        fabric_quantity = validated_data.pop('fabric_quantity', None)

        instance = self.Meta.model.objects.create(estimate=estimate,
                                                  unit_price=unit_price,
                                                  width=width,
                                                  depth=depth,
                                                  height=height,
                                                  **validated_data)

        #attach fabric quantity
        instance.fabric_quantity = fabric_quantity

        #Calculate the total price of the item
        if instance.is_custom_size and product.price == unit_price:
            instance.total = instance.quantity * instance.unit_price
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
        instance.description = validated_data.get('description', instance.description)

        instance.width = validated_data.get('width', instance.width)
        instance.depth = validated_data.get('depth', instance.depth)
        instance.height = validated_data.get('height', instance.height)
        instance.image = validated_data.get('image', instance.image)
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.unit_price = validated_data.get('unit_price', instance.unit_price)
        instance.comments = validated_data.get('comments', instance.comments)

        instance.total = instance.quantity * instance.unit_price
        
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

    company = serializers.CharField(default="Alinea Group Co., Ltd.")
    customer = CustomerSerializer(required=True)
    employee = EmployeeSerializer(required=False, read_only=True)
    project = ProjectSerializer(allow_null=True, required=False)
    items = ItemSerializer(item_queryset, many=True, required=True)
    remarks = serializers.CharField(default="", allow_blank=True, allow_null=True)
    #shipping_method = serializers.CharField(default="Truck", allow_null=True)
    #fob = serializers.CharField(default="Bangkok", allow_null=True)
    lead_time = serializers.CharField(default="4 Weeks")
    vat = serializers.DecimalField(required=True, decimal_places=2, max_digits=12, min_value=0, max_value=100)
    discount = serializers.IntegerField(default=0, min_value=0, max_value=100)
    second_discount = serializers.IntegerField(default=0, min_value=0, max_value=100)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    acknowledgement = AcknowledgementSerializer(required=False, allow_null=True)
    delivery_date = serializers.DateTimeField(required=False, allow_null=True, default=datetime.now())
    # Totals

    class Meta:
        model = Estimate
        read_only_fields = ('grand_total',
                            'total',
                            'post_discount_total',
                            'subtotal',
                            'time_created',
                            'employee')

        exclude = ('pdf', 'deal', 'po_id', 'fob', 'shipping_method')
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
                logger.debug(ret['project'])
                try:
                    del ret['project']
                except Exception as e:
                    logger.warn(e)
            except KeyError as e:
                pass

        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError, TypeError) as e:
            try:
                del ret['acknowledgement']
            except KeyError as e: 
                pass

        logger.debug("\n\nEstimate to internal value\n\n")

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """
        items_data = self.initial_data['items']
        validated_data.pop('items', [])
        #files = validated_data.pop('files', [])

        for item_data in items_data:
            for field in ['fabric']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass

        currency = validated_data.pop('currency', validated_data['customer'].currency or 'THB')
        discount = validated_data.pop('discount', validated_data['customer'].discount)
        try:
            files = validated_data.pop('files', [])
        except KeyError as e:
            files = []

        #Get User
        employee = self.context['request'].user
        if settings.DEBUG:
            employee = User.objects.get(pk=1) 

        instance = self.Meta.model.objects.create(employee=employee,
                                                  currency=currency,
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

        # Add pdfs to files list
        filenames = ['pdf']
        for filename in filenames:
            try:
                File.objects.create(file=getattr(instance, filename),
                                    estimate=instance)
            except Exception as e:
                logger.warn(e)

        # Assign files
        for file_obj in files:
            File.objects.create(file_obj=S3Object.objects.get(pk=file_obj['id']),
                                estimate=instance)


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
        instance.second_discount = validated_data.pop('second_discount', instance.second_discount)
        instance.remarks = validated_data.pop('remarks', instance.remarks)
        instance.lead_time = validated_data.pop('lead_time', instance.lead_time)
        instance.currency = validated_data.pop('currency', instance.currency or 'THB')
        instance.acknowledgement = validated_data.pop('acknowledgement', instance.acknowledgement)
        instance.project = validated_data.pop('project', instance.project)

        #Update attached files
        files = validated_data.pop('files', [])
        for file_obj in files:
            try:
                File.objects.get(file_id=file_obj['id'], estimate=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file_obj['id']),
                                    estimate=instance)

        new_status = validated_data.pop('status', instance.status)
     
        # Set the corresponding deal as closed lost
        if new_status.lower() != instance.status.lower() and new_status.lower() == 'cancelled':
            try:
                instance.deal.status = 'closed lost'
                instance.deal.save()
            except (AttributeError, TypeError) as e:
                logger.debug(e)

        instance.status = new_status

        items_data = validated_data.pop('items')

        items_data = self.initial_data['items']

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
        logger.debug(id_list)

        #Delete Items
        for item in instance.items.all():
            if item.id not in id_list:
                item.delete()
                instance.items.filter(pk=item.id).delete()
                logger.debug(item)
                logger.debug(instance.items.all())
                #item.deleted = True
                #item.save()

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
            
        
        
