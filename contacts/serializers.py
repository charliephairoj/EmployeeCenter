from contacts.models import Customer, Supplier, Address
from rest_framework import serializers


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        field = ('address1', 'address2', 'city', 'region', 'country', 'zipcode')
        
        
class CustomerSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(read_only=True)
    name_th = serializers.Field(source="name_th")
    notes = serializers.CharField(source="notes", required=False)
    email = serializers.EmailField(source="email", required=False)
    
    class Meta:
        model = Customer
        field = ('name')
        
        
class SupplierSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer()
    
    class Meta:
        model = Supplier
        field = ('name', 'addresses')        
