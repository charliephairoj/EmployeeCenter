from rest_framework import serializers

from supplies.models import Supply, Fabric, Log
from contacts.serializers import SupplierSerializer


class SupplySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Supply
        fields = ('id', 'description')
        

class FabricSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Fabric
        fields = ('id', 'description', 'color', 'pattern')
        
        
class LogSerializer(serializers.ModelSerializer):
    supply = SupplySerializer()
    
    class Meta:
        model = Log
