#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from contacts.models import Customer, Supplier, Address, SupplierContact, Contact
from po.models import PurchaseOrder
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from contacts.customer import service as customer_service
from contacts.supplier import service as supplier_service
from contacts.address import service as address_service

logger = logging.getLogger(__name__)


class PurchaseOrderFieldSerializer(serializers.ModelSerializer):
    order_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'grand_total',
                  'subtotal', 'total', 'revision', 'paid_date', 'receive_date', 'deposit',
                  'discount', 'status', 'terms', 'order_date', 'currency')
        depth = 1


class AddressListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        addr_mapping = {addr.id: addr for addr in instance}
        data_mapping = {item['id']: item for item in validated_data}

        # Perform creations and updates.
        ret = []
        for addr_id, data in data_mapping.items():
            addr = addr_mapping.get(addr_id, None)
            if addr is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(addr, data))

        # Perform deletions.
        for addr_id, addr in addr_mapping.items():
            if addr_id not in data_mapping:
                address_service.delete(addr)

        return ret

class AddressSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    address1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    #address2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    city = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    country = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    zipcode = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    territory = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Address
        fields = ("id", 'address1', 'city', 'territory', 'country', 'zipcode')
        list_serializer_class = AddressListSerializer
        
    def create(self, validated_data):
        """
        Override 'create' method to assign contact from context
        """
        return address_service.create(contact=self.context['contact'], **validated_data)

    def update(self, instance, validated_data):
        return address_service.update(instance, validated_data)
                

class ContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = SupplierContact
        read_only_fields = ('supplier',)
        fields = '__all__'
        
    def create(self, validated_data):
        """
        Override 'create' method to assign contact from context
        """
        instance = self.Meta.model.objects.create(supplier=self.context['supplier'], **validated_data)
        
        return instance
        
        
class ContactMixin(object):

    def _sync_contacts(self, instance, contacts_data):
        """
        Create, Update and Delete contacts
        """
        # List of 
        id_list = [c.get('id', None) for c in contacts_data]

        # Create and update contacts
        for contact_data in contacts_data:
            # Get or create new contact
            try:
                contact = Contact.objects.get(pk=contact_data['id'])
            except KeyError:
                contact = Contact.objects.create(name=contact_data['name'],
                                                 contact=instance)
                id_list.append(contact.id)
                
            
            contact.name = contact_data.pop('name', None)
            contact.email = contact_data.pop("email", None)
            contact.telephone = contact_data.pop('telephone', None)
            contact.job_title = contact_data.pop('job_title', None)
            contact.contact = instance
            contact.save()
            
        # Delete contacts
        for contact in instance.contacts.all():
            if contact.id not in id_list:
                contact.delete()
        
        
class CustomerSerializer(ContactMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True,)
    addresses = AddressSerializer(required=False,  many=True, allow_null=True)
    address = AddressSerializer(required=False, allow_null=True, write_only=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    contacts = serializers.ListField(child=serializers.DictField(), required=False, allow_null=True, write_only=True)
    bank = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    bank_account_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    currency = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    email = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    terms = serializers.CharField(required=False, default="50/net")

    class Meta:
        model = Customer
        exclude = ('contact', 'google_contact_id', 'type', 'job_title', 'trcloud_id', 'fax')

    def create(self, validated_data):
        """
        Override the base method 'create'.
        
        Calls the parent create and then also creates all the addresses and 
        contacts that are nested
        """
        addresses_data = validated_data.pop('addresses', 
                                            [validated_data.pop('address', [])])

        contacts_data = validated_data.pop('contacts', None)
        
        try:
            first = validated_data['first_name']
            try:
                last = validated_data['last_name']
            except KeyError:
                last = ''
            name = u"{0} {1}".format(first, last)
            validated_data.pop('name', None)
        except KeyError:
            name = validated_data.pop('name')
            
        instance = customer_service.create(user=self.context['request'].user, name=name, **validated_data)
        
        if addresses_data:
            # Delete any ids, as a new customer should not have a pre existing id
            try:
                for a in addresses_data:
                    try:
                        a.pop('id', None)
                    except (TypeError, KeyError, AttributeError) as e:
                        pass
            except Exception as e:
                pass

            address_serializer = AddressSerializer(data=addresses_data, context={'contact': instance}, many=True)
            if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()

        if contacts_data:
            self._sync_contacts(instance, contacts_data)
        
        return instance

    def update(self, instance, validated_data):
        """
        Override 'update' method
        """
        addresses_data = validated_data.pop('addresses', 
                                            [validated_data.pop('address', [])])
                    
        contacts_data = validated_data.pop('contacts', None)

        address_serializer = AddressSerializer(instance.addresses.all(), data=addresses_data, many=True)
        if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()
        
        if contacts_data:
            self._sync_contacts(instance, contacts_data)
            
        customer_service.update(instance, validated_data, self.context['request'].user)
        
        return instance


class CustomerFieldSerializer(ContactMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    email = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    addresses = AddressSerializer(required=False,  many=True, allow_null=True)

    class Meta:
        model = Customer
        fields = ('id', 'name', 'telephone', 'email', 'addresses')


class SupplierSerializer(ContactMixin, serializers.ModelSerializer):
    addresses = AddressSerializer(required=False, many=True, allow_null=True)
    address = AddressSerializer(required=False, write_only=True, allow_null=True)
    email = serializers.CharField(default="", allow_null=True, allow_blank=True)
    telephone = serializers.CharField(default="", allow_null=True, allow_blank=True)
    #name_th = serializers.CharField(required=False)
    contacts = ContactSerializer(required=False, many=True, write_only=True, allow_null=True)
    notes = serializers.CharField(default="", allow_null=True, allow_blank=True)
    bank = serializers.CharField(default="", allow_null=True, allow_blank=True)
    bank_account_number = serializers.CharField(default="", allow_null=True, allow_blank=True)
    purchase_orders = serializers.SerializerMethodField()
    terms = serializers.CharField(required=False, default="50/net")
    
    class Meta:
        model = Supplier
        exclude = ('contact', 'google_contact_id', 'trcloud_id', 'fax')

    def to_representation(self, instance):
        
        ret = super(SupplierSerializer, self).to_representation(instance)
        
        if "pk" in self.context['view'].kwargs or self.context['request'].method.lower() in ['put', 'post']:
            
            ret['contacts'] = ContactSerializer(SupplierContact.objects.filter(supplier=instance.id), many=True).data
            
        #ret['addresses'] = AddressSerializer(Address.objects.filter(contact=instance.id), many=True).data
            
        return ret

    def create(self, validated_data):
        """
        Override the base method 'create'.
        
        Calls the parent create and then also creates all the addresses and 
        contacts that are nested
        """
        addresses_data = validated_data.pop('addresses', 
                                            [validated_data.pop('address', [])])

        contacts_data = validated_data.pop('contacts', None)
        
        try:
            first = validated_data['first_name']
            try:
                last = validated_data['last_name']
            except KeyError:
                last = ''
            name = u"{0} {1}".format(first, last)
            validated_data.pop('name', None)
        except KeyError:
            name = validated_data.pop('name')
            
        instance = supplier_service.create(user=self.context['request'].user, name=name, **validated_data)
        
        if addresses_data:
            # Delete any ids, as a new supplier should not have a pre existing id
            try:
                for a in addresses_data:
                    try:
                        a.pop('id', None)
                    except (TypeError, KeyError, AttributeError) as e:
                        pass
            except Exception as e:
                pass

            address_serializer = AddressSerializer(data=addresses_data, context={'contact': instance}, many=True)
            if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()

        if contacts_data:
            self._sync_contacts(instance, contacts_data)

        return instance
        
    def update(self, instance, validated_data):
        """
        Override 'update' method
        """
        addresses_data = validated_data.pop('addresses', 
                                            [validated_data.pop('address', [])])
                            
        address_serializer = AddressSerializer(instance.addresses.all(), data=addresses_data, many=True)
        if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()

        contacts_data = validated_data.pop('contacts', None)
        try:
            if contacts_data is not None:
                self._update_contacts(instance, contacts_data)
        except Exception as e:
            logger.error(e)
            
       
            
        supplier_service.update(instance, validated_data, self.context['request'].user)
        
        return instance
        
    def _update_contacts(self, instance, contacts_data):
        """
        Create, Update and Deletes contacts
        """
        #Get list of ids
        id_list = [contact_data.get('id', None) for contact_data in contacts_data]
        #Create and update 
        for contact_data in contacts_data:
            try:
                contact = SupplierContact.objects.get(pk=contact_data['id'])
            except KeyError:
                contact = SupplierContact.objects.create(supplier=instance)
                id_list.append(contact.id)
                
            for field in contact_data.keys():
                setattr(contact, field, contact_data[field])
            contact.supplier = instance
            contact.save()
            
        #Delete contacts
        for contact in instance.contacts.all():
            if contact.id not in id_list:
                contact.delete()

    def get_purchase_orders(self, instance):
        request = self.context['request']

        if "pk" in self.context['view'].kwargs:
            year = (datetime.now() - timedelta(days=365)).year
            pos = instance.purchase_orders.filter(order_date__year__gte=year).order_by('-id')
            return PurchaseOrderFieldSerializer(pos, many=True).data
        else:
            return []


class SupplierFieldSerializer(ContactMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Supplier
        fields = ('id', 'name')
          
                
    
        
        
        
        
        