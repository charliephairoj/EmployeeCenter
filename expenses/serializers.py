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

from administrator.models import User
from administrator.serializers import UserFieldSerializer, LogSerializer, LogFieldSerializer
from invoices.models import Invoice, Item, Log as InvoiceLog, File
from invoices import service as invoice_service
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
from acknowledgements.serializers import ItemFieldSerializer as AckItemFieldSerializer, AcknowledgementFieldSerializer
from acknowledgements.models import Acknowledgement, Item as AckItem, File as AckFile
from accounting.serializers import JournalEntrySerializer


logger = logging.getLogger(__name__)


class ItemListSerializer(serializers.ListSerializer):
    pass


class ItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(required=False, allow_null=True)
    acknowledgement_item = AckItemFieldSerializer(required=False, allow_null=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, default=0)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, default='invoiced')
    #location = serializers.CharField(required=False, allow_null=True)
    image = S3ObjectFieldSerializer(required=False, allow_null=True)
    id = serializers.IntegerField(required=False, allow_null=True)

    grades = {'A1': 15,
              'A2': 20,
              'A3': 25,
              'A4': 30,
              'A5': 35,
              'A6': 40}

    class Meta:
        model = Item
        fields = ('description', 'id', 'unit_price', 'total', 'product',
                  'acknowledgement_item', 'comments', 'image', 'quantity', 'status')
        read_only_fields = ('total',)
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
            ret['acknowledgement_item'] = AckItem.objects.get(pk=data['acknowledgement_item']['id'])
        except (KeyError, AckItem.DoesNotExist, TypeError) as e:
            if 'acknowledgement_item' in ret:
                del ret['acknowledgement_item']

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
        invoice = self.context['invoice']

        instance = self.Meta.model.objects.create(invoice=invoice, **validated_data)
       
        instance.total = (instance.quantity or 1) * (instance.unit_price or 0)

        instance.save()

        return instance

    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """

        # Update attributes from client side details
        invoice = self.context['invoice']
        employee = self.context['employee']

        # Loops through attributes and logs changes
        updatable_attributes = ['quantity', 'unit_price', 'description', 'comments', 'status']

        for attr in updatable_attributes:
            new_attr_value = validated_data.pop(attr, getattr(instance, attr))

            if getattr(instance, attr) != new_attr_value:
                old_attr_value = getattr(instance, attr)
                setattr(instance, attr, new_attr_value)

                # Log data changes
                message = u"{0}: {1} changed from {2} to {3}"
                message = message.format(instance.description, attr, old_attr_value, new_attr_value)
                InvoiceLog.create(message=message, invoice=instance.invoice, user=employee)


        # Set the price of the total for this item
        instance.total = instance.quantity * instance.unit_price
        instance.save()

        return instance


class ItemFieldSerializer(serializers.ModelSerializer):
   
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    quantity = serializers.DecimalField(required=False, decimal_places=2, max_digits=15)
    description = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ('description', 'id', 'unit_price', 'quantity')



class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = File
        fields = '__all__'
        read_only_fields = ('invoice', 'file')


class InvoiceSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)
    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer = CustomerOrderFieldSerializer()
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    employee = UserFieldSerializer(required=False, read_only=True)
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    phase = PhaseFieldSerializer(allow_null=True, required=False)
    items = ItemSerializer(item_queryset, many=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    due_date = serializers.DateTimeField(required=True)
    logs = LogFieldSerializer(many=True, read_only=True)
    journal_entry = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        read_only_fields = ('total', 'subtotal', 'time_created', 'logs')
        exclude = ('pdf', 'trcloud_id',
                   'trcloud_document_number')
        depth = 3

    def to_internal_value(self, data):
        ret = super(InvoiceSerializer, self).to_internal_value(data)

        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError) as e:
            try:
                del ret['acknowledgement']
            except Exception as e:
                logger.warn(e)

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

        logger.debug("\n\nInvoice to internal value\n\n")

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """

        #Discard STatus
        status = validated_data.pop('status', 'invoiced')
        
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        files = validated_data.pop('files', [])
        
        # Get user 
        employee = self.context['request'].user

        try:
            assert isinstance(employee, User)
        except AssertionError as e:
            employee = User.objects.get(pk=1)
        
        for item_data in items_data:
            for field in ['product']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass

        discount = validated_data.pop('discount', validated_data['customer'].discount)
        due_date = timezone('Asia/Bangkok').normalize(validated_data.pop('due_date'))

        instance = self.Meta.model.objects.create(employee=employee, discount=discount,
                                                  status='invoiced', _due_date=due_date,
                                                  **validated_data)

        item_serializer = ItemSerializer(data=items_data, context={'invoice': instance}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()


        instance.calculate_totals()

        instance.create_and_upload_pdf()
        
        # Add pdfs to files list
        filenames = ['pdf', ]
        for filename in filenames:
            try:
                File.objects.create(file=getattr(instance, filename),
                                    invoice=instance)
            except Exception as e:
                logger.warn(e)

        # Assign files
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                invoice=instance)

        # Create Sales Order File Link
        # - So Invoices will show up in acknowledgement Files
        if instance.acknowledgement:
            AckFile.objects.create(acknowledgement=instance.acknowledgement,
                                   file=instance.pdf)

        # Create a calendar event
        try:
            instance.create_calendar_event(employee)
        except Exception as e:
            message = u"Unable to create calendar event for invoice {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = InvoiceLog.create(message=message, 
                                invoice=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR")

        # Log Opening of an order
        message = u"Created Invoice #{0}.".format(instance.id)
        log = InvoiceLog.create(message=message, invoice=instance, user=employee)

        if instance.vat > 0:
            try:
                pass #instance.create_in_trcloud() 
            except Exception as e:
                message = u"Unable to create invoice because:\n{0}"
                message = message.format(e)
                log = InvoiceLog.create(message=message, 
                                    invoice=instance, 
                                    user=employee,
                                    type="TRCLOUD")

        # Create Journal Entry in Accouting
        invoice_service.create_journal_entry(instance)

        # Update Sales Order/ Acknowledgement status
        instance.acknowledgement.status = 'invoiced' if instance.acknowledgement.balance == 0 else 'partially invoiced'
        instance.acknowledgement.save()
        
        return instance

    def update(self, instance, validated_data):

        # Get user 
        try:
            employee = self.context['request'].user
        except KeyError as e:
            employee = self.context['employee']

        if settings.DEBUG:
            employee = User.objects.get(pk=1)
        
        instance.current_user = employee
        dd = timezone('Asia/Bangkok').normalize(validated_data.pop('due_date', instance.due_date))
        instance.project = validated_data.pop('project', instance.project)
        instance.acknowledgement = validated_data.pop('acknowledgement', instance.acknowledgement)
        instance.vat = validated_data.pop('vat', instance.vat)
        instance.discount = validated_data.pop('discount', instance.discount)
        instance.room = validated_data.pop('room', instance.room)
        status = validated_data.pop('status', instance.status)

        if instance.due_date != dd:
            old_dd = instance.due_date
            instance.due_date = dd
           
            # Log Changing delivery date
            message = u"Invoice #{0} due date changed from {1} to {2}."
            message = message.format(instance.id, old_dd.strftime('%d/%m/%Y'), dd.strftime('%d/%m/%Y'))
            InvoiceLog.create(message=message, invoice=instance, user=employee)

        if status.lower() != instance.status.lower():

            message = u"Updated Invoice #{0} from {1} to {2}."
            message = message.format(instance.id, instance.status.lower(), status.lower())
            InvoiceLog.create(message=message, invoice=instance, user=employee)

            instance.status = status

        old_qty = sum([item.quantity for item in instance.items.all()])
        
        # Extract items data
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        fabrics = {}

        self._update_items(instance, items_data)

        #Update attached files
        files = validated_data.pop('files', [])
        for file in files:
            try:
                File.objects.get(file_id=file['id'], invoice=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                    invoice=instance)

        #if instance.status.lower() in ['invoiced', 'in production', 'ready to ship']:

        # Store old total and calculate new total
        old_total = instance.total
        instance.calculate_totals()

        try:
            instance.create_and_upload_pdf()
        except IOError as e:

        
            tb = traceback.format_exc()
            logger.error(tb)
            
            message = u"Unable to update PDF for invoice {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = InvoiceLog.create(message=message, 
                                invoice=instance, 
                                user=employee,
                                type="PDF CREATION ERROR")


        try:
            instance.update_calendar_event()
        except Exception as e:
            logger.debug(e)
            message = u"Unable to update calendar event for invoice {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = InvoiceLog.create(message=message, 
                                invoice=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR ERROR")

        instance.save()

        if instance.vat > 0 and instance.trcloud_id:
            try:
                pass #instance.update_in_trcloud()
            except Exception as e:
                message = u"Unable to update invoice {0} because:\n{1}"
                message = message.format(instance.id, e)
                log = InvoiceLog.create(message=message, 
                                    invoice=instance, 
                                    user=employee,
                                    type="TRCLOUD ERROR")
           
        return instance

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
                #item.deleted = True
                #item.save()

        #Update or Create Item
        for item_data in items_data:
            try:
                item = Item.objects.get(pk=item_data['id'], invoice=instance)
                serializer = ItemSerializer(item, context={
                    'customer': instance.customer, 
                    'invoice': instance, 
                    'employee': instance.employee}, data=item_data)
            except (KeyError, Item.DoesNotExist) as e:
                serializer = ItemSerializer(data=item_data, context={
                    'customer': instance.customer, 
                    'invoice': instance,
                    'employee': instance.employee})
                
            if serializer.is_valid(raise_exception=True):
                item = serializer.save()
                id_list.append(item.id)

    def get_journal_entry(self, instance):

        return JournalEntrySerializer(instance.journal_entry).data

   

class InvoiceFieldSerializer(serializers.ModelSerializer):
    project = ProjectFieldSerializer(required=False, read_only=True)
    acknowledgement = AcknowledgementFieldSerializer(required=False, read_only=True)

    class Meta:
        model = Invoice
        fields = ('company', 'id', 'remarks', 'due_date', 'total', 'subtotal', 'time_created', 'project', 'acknowledgement')
        read_only_fields = ('project', 'acknowledgement')


