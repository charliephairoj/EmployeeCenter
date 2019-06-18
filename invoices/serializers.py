#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
import traceback
from datetime import date

import boto
from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.fields import DictField
from django.utils import timezone as tz
from pytz import timezone

from administrator.models import User, Company
from administrator.serializers import UserFieldSerializer, LogSerializer, LogFieldSerializer, CompanySerializer, BaseLogSerializer
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
from accounting.transaction import service as trx_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DefaultInvoice(object):
    def set_context(self, serializer_field):
        self.invoice = serializer_field.context['invoice']

    def __call__(self):
        return self.invoice


class InvoiceLogSerializer(BaseLogSerializer):
    invoice = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultInvoice()))
    type = serializers.CharField(default=serializers.CreateOnlyDefault('INVOICE'))

    class Meta:
        model = InvoiceLog
        depth = 1
        fields = ('message', 'timestamp', 'user', 'company', 'type', 'invoice')


class ItemListSerializer(serializers.ListSerializer):
    def update(self, instances, validated_data):
        logger.info(validated_data)
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
                self._log(message, invoice)


        # Set the price of the total for this item
        instance.total = instance.quantity * instance.unit_price
        instance.save()

        return instance
    
    def _log(self, message, instance=None):
        """
        Create Invoice link Log
        """
        if not isinstance(instance, Invoice):
            instance = self.instance.invoice

        serializer = InvoiceLogSerializer(data={'message': message}, 
                                          context={'invoice': instance,
                                                   'request': self.context['request']})

        if serializer.is_valid(raise_exception=True):
            serializer.save()



class ItemFieldSerializer(serializers.ModelSerializer):
   
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    quantity = serializers.DecimalField(required=False, decimal_places=2, max_digits=15)
    description = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Item
        fields = ('description', 'id', 'unit_price', 'quantity')


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
    invoice = serializers.HiddenField(default=serializers.CreateOnlyDefault(DefaultInvoice))
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


class InvoiceSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)

    # Business Related
    document_number = serializers.IntegerField(default=0)
    customer_name = serializers.CharField()
    customer_branch = serializers.CharField(default="Headquarters")
    customer_address = serializers.CharField()
    customer_telephone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer_email = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer_tax_id = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    due_date = serializers.DateTimeField(required=True)
    issue_date = serializers.DateField(default=date.today)
    tax_date = serializers.DateField(default=date.today)
    
    

    # Relationships
    customer = CustomerOrderFieldSerializer()
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    employee = UserFieldSerializer(required=False, read_only=True)
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    phase = PhaseFieldSerializer(allow_null=True, required=False)
    items = ItemSerializer(item_queryset, many=True)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    logs = LogFieldSerializer(many=True, read_only=True)
    journal_entry = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        read_only_fields = ('total', 'subtotal', 'time_created', 'logs', 'grand_total')
        exclude = ('pdf', 'trcloud_id', 'company', 'company_name')
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
                del ret['project']
            except Exception as e:
                logger.warn(e)

        logger.debug("\n\nInvoice to internal value\n\n")

        return ret

    @transaction.atomic
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

        instance = self.Meta.model.objects.create(employee=employee, company=employee.company,
                                                  discount=discount, status='invoiced',
                                                  _due_date=due_date, **validated_data)
        self.instance = instance

        item_serializer = ItemSerializer(data=items_data,
                                         context={'invoice': instance, 
                                                  'request': self.context['request']},
                                         many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()


        instance.calculate_totals()

        instance.create_and_upload_pdf()
        
        # Add pdfs to files list
        filenames = ['pdf', ]
        for filename in filenames:
            self._add_file(getattr(instance, filename))
            
        # Assign files
        for file in files:
            self._add_file(S3Object.objects.get(pk=file['id']))

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
            message = message.format(instance.document_number, e)
            self._log(message)

        # Log Opening of an order
        message = u"Created Invoice #{0}.".format(instance.document_number)
        self._log(message)

        # Create Journal Entry in Accouting
        invoice_service.create_journal_entry(instance, company=employee.company)

        # Update Sales Order/ Acknowledgement status
        instance.acknowledgement.status = 'invoiced' if instance.acknowledgement.balance == 0 else 'partially invoiced'
        instance.acknowledgement.save()
        
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):        
        dd = timezone('Asia/Bangkok').normalize(validated_data.pop('due_date', instance.due_date))
        instance.project = validated_data.pop('project', instance.project)
        instance.acknowledgement = validated_data.pop('acknowledgement', instance.acknowledgement)
        instance.vat = validated_data.pop('vat', instance.vat)
        instance.discount = validated_data.pop('discount', instance.discount)
        instance.room = validated_data.pop('room', instance.room)

        if instance.due_date != dd:
            old_dd = instance.due_date
            instance.due_date = dd
           
            # Log Changing delivery date
            message = u"Invoice #{0} due date changed from {1} to {2}."
            message = message.format(instance.document_number, old_dd.strftime('%d/%m/%Y'), dd.strftime('%d/%m/%Y'))
            InvoiceLog.create(message=message, invoice=instance, user=employee)

        

        old_qty = sum([item.quantity for item in instance.items.all()])
        
        # Extract items data
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']

        item_serializer = ItemSerializer(instance=instance.items.all(), 
                                         data=items_data,
                                         context={'invoice': instance,
                                                  'request':self.context['request'],
                                                  'employee': self.context['request'].user}, 
                                         many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()

        #Update attached files
        files_data = validated_data.pop('files', None)
        if (files_data):
            files_data = [{'file': f} for f in files_data]
            files_serializer = FileSerializer(File.objects.filter(invoice=instance),
                                            data=files_data, 
                                            context={'request': self.context['request'],
                                                    'invoice': instance},
                                            many=True)
        

        # Store old total and calculate new total
        instance.calculate_totals()

        instance.save()

        try:
            instance.create_and_upload_pdf()
        except IOError as e:

        
            tb = traceback.format_exc()
            logger.error(tb)
            
            message = u"Unable to update PDF for invoice {0} because:\n{1}"
            message = message.format(instance.document_number, e)
            self._log(message, instance)
            

        try:
            instance.update_calendar_event()
        except Exception as e:
            logger.debug(e)
            message = u"Unable to update calendar event for invoice {0} because:\n{1}"
            message = message.format(instance.document_number, e)
            self._log(message, instance)
            

        instance.save()

        
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

    def create_journal_entry(self, instance):
        data = {
            'description': u'Invoice {0}'.format(invoice.document_number),
            'journal': {
                'id': journal_service.get(name='Revenue', company=company).id
            },
            'transactions': []
        }

        # Add to Receivable  
        receivable_acc = instance.customer.account_receivable or account_service.get(name='Accounts Receivable (A/R)', company=company)
        receivable_desc = u'Invoice {0}: {1}'.format(instance.document_number, instance.customer.name)
        data['transactions'].append(trx_service.create_trx_data(receivable_acc, 
                                                                receivable_desc, 
                                                                debit=instance.grand_total))

        # Add Sales VAT
        if invoice.vat_amount > 0:
            vat_acc = account_service.get(name='VAT Payable', company=company)
            vat_desc = u'Invoice {0}: {1}'.format(instance.document_number, instance.customer.name)
            data['transactions'].append(trx_service.create_trx_data(vat_acc, 
                                                                    vat_desc, 
                                                                    credit=instance.vat_amount))


        #Add Transactions for income for each item
        for item in instance.items.all():
            income_acc = account_service.get(name='Sales of Product Income', company=company)
            income_desc = u'Invoice {0}: {1}'.format(instance.document_number, item.description)
            data['transactions'].append(trx_service.create_trx_data(income_acc, 
                                                                    income_desc, 
                                                                    credit=item.total))

        serializer = JournalEntrySerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()

            invoice.journal_entry = serializer.instance
            invoice.save()
            
    def _add_file(self, file):
        """
        Adds a file to the acknowledgement
        """
        File.objects.create(invoice=self.instance, 
                            file=file)
        
        # Log addition of file
        msg = u"Added '{0}' to Invoice #{1} files"
        msg = msg.format(file.filename, self.instance.document_number)
        self._log(msg)

    def _log(self, message, instance=None):
        """
        Create Invoice link Log
        """
        if not isinstance(instance, self.Meta.model):
            instance = self.instance

        serializer = InvoiceLogSerializer(data={'message': message}, 
                                          context={'invoice': instance,
                                                   'request': self.context['request']})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
   

class InvoiceFieldSerializer(serializers.ModelSerializer):
    project = ProjectFieldSerializer(required=False, read_only=True)
    acknowledgement = AcknowledgementFieldSerializer(required=False, read_only=True)

    class Meta:
        model = Invoice
        fields = ('id', 'remarks', 'due_date', 'total', 'subtotal', 'time_created', 'project', 'acknowledgement')
        read_only_fields = ('project', 'acknowledgement')


