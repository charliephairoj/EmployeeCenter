import logging

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Log
from contacts.serializers import SupplierSerializer


logger = logging.getLogger(__name__)


class SupplySerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(source='quantity')
    products = serializers.PrimaryKeyRelatedField(read_only=True)
    supplier = serializers.PrimaryKeyRelatedField(write_only=True)
    notes = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    
    class Meta:
        model = Supply
        fields = ('id', 'description', 'width', 'depth', 'height', 'height_units',
                  'width_units', 'depth_units')
        
    def to_native(self, obj, *args, **kwargs):

        native_data = super(SupplySerializer, self).to_native(obj, *args, **kwargs)

        #Set the quantity
        try:
            native_data['quantity'] = obj.quantity
        except AttributeError:
            pass
            
        if self.init_data:
            if 'supplier' in self.init_data:
                obj.supplier = Supplier.objects.get(pk=self.init_data['supplier'])
                for field in ['cost', 'reference', 'purchasing_units', 'quantity_per_puchasing_units', 
                              'upc']:
                    try:
                        native_data[field] = getattr(obj, field)
                    except AttributeError:
                        pass
            else:
                native_data['suppliers'] = []
                for product in obj.products.all():
                    product_data = {}
                    for field in ['cost', 'reference', 'purchasing_units', 
                                  'quantity_per_puchasing_units', 'upc']:
                        try:
                            product_data[field] = getattr(product, field)
                        except AttributeError:
                            pass
                            
                    native_data['suppliers'].append(product_data)
            
        #Return the data
        return native_data
        
 
class FabricSerializer(SupplySerializer):
    
    class Meta:
        model = Fabric
        fields = ('id', 'description', 'width', 'depth', 'height', 'type', 'height_units',
                  'width_units', 'depth_units', 'notes', 'color', 'pattern')
        
        
class LogSerializer(serializers.ModelSerializer):
    supply = SupplySerializer()
    
    class Meta:
        model = Log
