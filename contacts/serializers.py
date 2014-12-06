import logging

from contacts.models import Customer, Supplier, Address, SupplierContact
from rest_framework import serializers
from rest_framework.serializers import ValidationError


logger = logging.getLogger(__name__)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        field = ("id", 'address1', 'address2', 'city', 'region', 'country', 'zipcode')
        
        

class ContactSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SupplierContact
        fields = ("id", 'name', 'email', 'primary', 'telephone')
        read_only_fields = ('supplier',)
        
        
class ContactMixin(object):
    
    def create(self, validated_data):
        """
        Override the base method 'create'.
        
        Calls the parent create and then also creates all the addresses and 
        contacts that are nested
        """
        try:
            addresses_data = validated_data.pop('addresses')
        except KeyError:
            addresses_data = []
        
        try:
            contacts_data = validated_data.pop('contacts')
        except KeyError:
            contacts_data = []
                
        instance = self.Meta.model(**validated_data)
        
        for address_data in addresses_data:
            Address(contact=instance, **address_data)
            
        for contact_data in contacts_data:
            SupplierContact(supplier=instance, **contact_data)
        
        setattr(instance, 'is_{0}'.format(instance.__str__().lower()), True)
        
        instance.save()
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the base method 'update'
        
        Calls the parent 'update' method and then updates or creates all the addresses and
        contacts that are nested
        """

        try:
            addresses_data = validated_data.pop('addresses')
        except KeyError:
            addresses_data = []
        
        try:
            contacts_data = validated_data.pop('contacts')
        except KeyError:
            contacts_data = []
                        
        for address_data in addresses_data:
            try:
                address = Address.objects.get(pk=address_data['id'])
                for field_name in address_data.keys():
                    settattr(address, field_name, address_data[field_name])
            except KeyError:
                Address.objects.create(contact=instance, **address_data)
            
        for contact_data in contacts_data:
            try:
                contact = SupplierContact.objects.get(pk=contact_data['id'])
                for field_name in contact_data.keys():
                    settattr(contact, field_name, contact_data[field_name])
            except KeyError:
                SupplierContact.objects.create(supplier=instance, **contact_data)
        
        for field_name in validated_data.keys():
            setattr(instance, field_name, validated_data[field_name])
        
        instance.save()
        
        return instance
        
        
class CustomerSerializer(ContactMixin, serializers.ModelSerializer):
    addresses = AddressSerializer(required=False,  many=True)
    #name_th = serializers.CharField(required=False)
    
    class Meta:
        model = Customer
        field = ('name', 'id', 'email', 'fax')
        
        
class SupplierSerializer(ContactMixin, serializers.ModelSerializer):
    addresses = AddressSerializer(required=False, many=True)
    #name_th = serializers.CharField(required=False)
    contacts = ContactSerializer(required=False, many=True)
    
    class Meta:
        model = Supplier
        field = ('name', 'id', 'fax', 'telephone')
        depth = 1    

    def validate_contacts(self, value):
        logger.debug(self.data)
        logger.debug(value)
        return value