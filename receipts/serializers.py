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
from receipts.models import Receipt, Item, Log as ReceiptLog, File
from receipts import service as receipt_service
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
from invoices.models import Invoice, File as InvFile, Item as InvItem
from invoices.serializers import InvoiceFieldSerializer, ItemFieldSerializer as InvItemFieldSerializer
from accounting.serializers import AccountFieldSerializer
from accounting.models import Account
from accounting.account import service as acc_service


logger = logging.getLogger(__name__)


class ItemListSerializer(serializers.ListSerializer):
    pass


class ItemSerializer(serializers.ModelSerializer):
    invoice_item = InvItemFieldSerializer(required=False, allow_null=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, default=0)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, default='receiptd')
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ('description', 'id', 'unit_price', 'total',
                  'invoice_item', 'comments', 'quantity', 'status')
        read_only_fields = ('total',)
        list_serializer_class = ItemListSerializer

    def to_internal_value(self, data):
        ret = super(ItemSerializer, self).to_internal_value(data)

        try:
            ret['invoice_item'] = InvItem.objects.get(pk=data['invoice_item']['id'])
        except (KeyError, InvItem.DoesNotExist, TypeError) as e:
            if 'invoice_item' in ret:
                del ret['invoice_item']
        
        return ret

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        receipt = self.context['receipt']

        instance = self.Meta.model.objects.create(receipt=receipt, **validated_data)
       
        instance.total = (instance.quantity or 1) * (instance.unit_price or 0)

        instance.save()

        return instance

    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """

        # Update attributes from client side details
        receipt = self.context['receipt']
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
                ReceiptLog.create(message=message, receipt=instance.receipt, user=employee)


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
        read_only_fields = ('receipt', 'file')


class ReceiptSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)
    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer = CustomerOrderFieldSerializer()
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    employee = UserFieldSerializer(required=False, read_only=True)
    items = ItemSerializer(item_queryset, many=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    paid_date = serializers.DateTimeField(required=True)
    logs = LogFieldSerializer(many=True, read_only=True)
    invoice = InvoiceFieldSerializer(required=True)
    deposit_to = AccountFieldSerializer(required=True, write_only=True)

    class Meta:
        model = Receipt
        read_only_fields = ('total', 'subtotal', 'time_created', 'logs')
        write_only_fields = ('deposit_to',)
        exclude = ('pdf',)
        depth = 2

    def to_internal_value(self, data):
        ret = super(ReceiptSerializer, self).to_internal_value(data)

        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError) as e:
            try:
                del ret['acknowledgement']
            except Exception as e:
                logger.warn(e)
        
        try:
            ret['invoice'] = Invoice.objects.get(pk=data['invoice']['id'])
        except (Invoice.DoesNotExist, KeyError) as e:
            try:
                del ret['invoice']
            except Exception as e:
                logger.warn(e)

        try:
            ret['customer'] = Customer.objects.get(pk=data['customer']['id'])
        except (Customer.DoesNotExist, KeyError) as e:
            ret['customer'] = Customer.objects.create(**data['customer'])

        try:
            ret['deposit_to'] = Account.objects.get(pk=data['deposit_to']['id'])
        except (Account.DoesNotExist, KeyError) as e:
            ret['deposit_to'] = Account.objects.create(**data['deposit_to'])


        logger.debug("\n\nReceipt to internal value\n\n")

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """

        #Discard STatus
        status = validated_data.pop('status', 'paid')
        
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        files = validated_data.pop('files', [])
        deposit_to = validated_data.pop('deposit_to')
        
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
        paid_date = timezone('Asia/Bangkok').normalize(validated_data.pop('paid_date'))

        instance = self.Meta.model.objects.create(employee=employee, discount=discount,
                                                  status='receiptd', paid_date=paid_date,
                                                  **validated_data)

        item_serializer = ItemSerializer(data=items_data, context={'receipt': instance}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()


        instance.calculate_totals()

        instance.create_and_upload_pdf()
        
        # Add pdfs to files list
        filenames = ['pdf', ]
        for filename in filenames:
            try:
                File.objects.create(file=getattr(instance, filename),
                                    receipt=instance)
            except Exception as e:
                logger.warn(e)

        # Assign files
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                receipt=instance)

        # Create Sales Order File Link
        # - So Receipts will show up in acknowledgement Files
        if instance.acknowledgement:
            AckFile.objects.create(acknowledgement=instance.acknowledgement,
                                   file=instance.pdf)

        # Create Sales Order File Link
        # - So Receipts will show up in acknowledgement Files
        if instance.invoice:
            InvFile.objects.create(invoice=instance.invoice,
                                   file=instance.pdf)

            if instance.invoice.acknowledgement:
                AckFile.objects.create(acknowledgement=instance.invoice.acknowledgement,
                                       file=instance.pdf)

        # Create a calendar event
        try:
            instance.create_calendar_event(employee)
        except Exception as e:
            message = u"Unable to create calendar event for receipt {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = ReceiptLog.create(message=message, 
                                receipt=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR")

        # Log Opening of an order
        message = u"Created Receipt #{0}.".format(instance.id)
        log = ReceiptLog.create(message=message, receipt=instance, user=employee)

        # Create Journal Entry in Accouting
        receipt_service.create_journal_entry(instance, deposit_to=deposit_to)

        # Update Sales Order/ Acknowledgement status
        if instance.invoice:
            instance.invoice.status = 'paid'
            instance.invoice.save()

            if instance.invoice.acknowledgement:
                instance.invoice.acknowledgement.status = 'paid'
                instance.invoice.acknowledgement.save()
        
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
            message = u"Receipt #{0} due date changed from {1} to {2}."
            message = message.format(instance.id, old_dd.strftime('%d/%m/%Y'), dd.strftime('%d/%m/%Y'))
            ReceiptLog.create(message=message, receipt=instance, user=employee)

        if status.lower() != instance.status.lower():

            message = u"Updated Receipt #{0} from {1} to {2}."
            message = message.format(instance.id, instance.status.lower(), status.lower())
            ReceiptLog.create(message=message, receipt=instance, user=employee)

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
                File.objects.get(file_id=file['id'], receipt=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                    receipt=instance)

        #if instance.status.lower() in ['receiptd', 'in production', 'ready to ship']:

        # Store old total and calculate new total
        old_total = instance.total
        instance.calculate_totals()

        try:
            instance.create_and_upload_pdf()
        except IOError as e:

        
            tb = traceback.format_exc()
            logger.error(tb)
            
            message = u"Unable to update PDF for receipt {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = ReceiptLog.create(message=message, 
                                receipt=instance, 
                                user=employee,
                                type="PDF CREATION ERROR")


        try:
            instance.update_calendar_event()
        except Exception as e:
            logger.debug(e)
            message = u"Unable to update calendar event for receipt {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = ReceiptLog.create(message=message, 
                                receipt=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR ERROR")

        instance.save()

        if instance.vat > 0 and instance.trcloud_id:
            try:
                pass #instance.update_in_trcloud()
            except Exception as e:
                message = u"Unable to update receipt {0} because:\n{1}"
                message = message.format(instance.id, e)
                log = ReceiptLog.create(message=message, 
                                    receipt=instance, 
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
                item = Item.objects.get(pk=item_data['id'], receipt=instance)
                serializer = ItemSerializer(item, context={
                    'customer': instance.customer, 
                    'receipt': instance, 
                    'employee': instance.employee}, data=item_data)
            except (KeyError, Item.DoesNotExist) as e:
                serializer = ItemSerializer(data=item_data, context={
                    'customer': instance.customer, 
                    'receipt': instance,
                    'employee': instance.employee})
                
            if serializer.is_valid(raise_exception=True):
                item = serializer.save()
                id_list.append(item.id)


   

class ReceiptFieldSerializer(serializers.ModelSerializer):
    acknowledgement = AcknowledgementFieldSerializer(required=False, read_only=True)

    class Meta:
        model = Receipt
        fields = ('company', 'id', 'remarks', 'due_date', 'total', 'subtotal', 'time_created', 'acknowledgement')
        read_only_fields = ('acknowledgement', )


