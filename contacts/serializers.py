import logging

from contacts.models import Customer, Supplier, Address, SupplierContact
from rest_framework import serializers
from rest_framework.serializers import ValidationError


logger = logging.getLogger(__name__)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        field = ("id", 'address1', 'address2', 'city', 'region', 'country', 'zipcode')
        
    def create(self, validated_data):
        """
        Override 'create' method to assign contact from context
        """
        instance = self.Meta.model.objects.create(contact=self.context['contact'], **validated_data)
        
        return instance
        

class ContactSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = SupplierContact
        read_only_fields = ('supplier',)
        
    def create(self, validated_data):
        """
        Override 'create' method to assign contact from context
        """
        instance = self.Meta.model.objects.create(supplier=self.context['supplier'], **validated_data)
        
        return instance
        
        
class ContactMixin(object):

    def create(self, validated_data):
        """
        Override the base method 'create'.
        
        Calls the parent create and then also creates all the addresses and 
        contacts that are nested
        """
        addresses_data = validated_data.pop('addresses', None)
        contacts_data = validated_data.pop('contacts', None)
        
        try:
            first = validated_data.pop('first_name')
            try:
                last = validated_data.pop('last_name')
            except KeyError:
                last = ''
            name = "{0} {1}".format(first, last)
        except KeyError:
            name = validated_data.pop('name')
            
        instance = self.Meta.model.objects.create(name=name, **validated_data)
        
        if addresses_data:
            address_serializer = AddressSerializer(data=addresses_data, context={'contact': instance}, many=True)
            if address_serializer.is_valid(raise_exception=True):
                address_serializer.save()
                
        if contacts_data:
            contact_serializer = ContactSerializer(data=contacts_data, context={'supplier': instance}, many=True)
            if contact_serializer.is_valid(raise_exception=True):
                contact_serializer.save()
                        
        field = 'is_customer' if isinstance(instance, Customer) else 'is_supplier'
        setattr(instance, field, True)
        
        instance.save()

        return instance
        
    def _update_addresses(self, instance, addresses_data):
        """
        Create, Update and Deletes contacts
        """
        #Get list of ids
        id_list = [address_data.get('id', None) for address_data in addresses_data]
        
        #Create and update 
        for address_data in addresses_data:
            try:
                address = Adress.objects.get(pk=address_data['id'])
            except KeyError:
                address = Adress.objects.create()
                id_list.append(address.id)
                
            for field in address_data.keys():
                setattr(address, field, address_data[field])
                
            address.save()
            
        #Delete contacts
        for address in instance.addresses.all():
            if address.id not in id_list:
                address.delete()
        
        
class CustomerSerializer(ContactMixin, serializers.ModelSerializer):
    addresses = AddressSerializer(required=False,  many=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    fax = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Customer
        
    def update(self, instance, validated_data):
        """
        Override 'update' method
        """
        addresses_data = validated_data.pop('addresses', None)
        addresses_data = self.context['request'].data.get('addresses', None)
        
        if addresses_data:
            self._update_addresses(instance, addresses_data)
        
        for field in validated_data.keys():
            setattr(instance, field, validated_data[field])
            
        instance.save()
        
        return instance
    
                
class SupplierSerializer(ContactMixin, serializers.ModelSerializer):
    addresses = AddressSerializer(required=False, many=True)
    #name_th = serializers.CharField(required=False)
    contacts = ContactSerializer(required=False, many=True, partial=True)
    
    class Meta:
        model = Supplier
        
    def to_representation(self, instance):
        
        ret = super(SupplierSerializer, self).to_representation(instance)
        
        return ret
        
    def update(self, instance, validated_data):
        """
        Override 'update' method
        """
        addresses_data = validated_data.pop('addresses', None)
        addresses_data = self.context['request'].data.get('addresses', None)
        contacts_data = validated_data.pop('contacts', None)
        contacts_data = self.context['request'].data.get('contacts', None)

        if contacts_data:
            self._update_contacts(instance, contacts_data)
        
        if addresses_data:
            self._update_addresses(instance, addresses_data)
        
        for field in validated_data.keys():
            setattr(instance, field, validated_data[field])
            
        instance.save()
        
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
                
            contact.save()
            
        #Delete contacts
        for contact in instance.contacts.all():
            if contact.id not in id_list:
                contact.delete()
    
    def _update_addresses(self, instance, addresses_data):
        """
        Create, Update and Deletes contacts
        """
        #Get list of ids
        id_list = [address_data.get('id', None) for address_data in addresses_data]
        
        #Create and update 
        for address_data in addresses_data:
            try:
                address = Adress.objects.get(pk=address_data['id'])
            except KeyError:
                address = Adress.objects.create()
                id_list.append(address.id)
                
            for field in address_data.keys():
                setattr(address, field, address_data[field])
                
            address.save()
            
        #Delete contacts
        for address in instance.addresses.all():
            if address.id not in id_list:
                address.delete()
    
                
                
                
    
        
        
        
        
        