from contacts.models import Customer, Supplier, Address, SupplierContact
from rest_framework import serializers


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        field = ('address1', 'address2', 'city', 'region', 'country', 'zipcode')
        

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierContact
        read_only_fields = ('supplier',)
        
        
class CustomerSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(required=False,  many=True, allow_add_remove=True)
    name_th = serializers.CharField(required=False)
    
    class Meta:
        model = Customer
        field = ('name', 'id', 'email', 'fax')
        read_only_fields = ('is_customer',)
        
        
class SupplierSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(required=False, many=True, allow_add_remove=True)
    name_th = serializers.CharField(required=False)
    contacts = ContactSerializer(required=False, many=True, allow_add_remove=True)
    
    class Meta:
        model = Supplier
        field = ('name',)        
