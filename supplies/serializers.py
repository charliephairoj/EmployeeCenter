from decimal import Decimal
import logging

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Supply, Product, Fabric, Log
from contacts.serializers import SupplierSerializer


logger = logging.getLogger(__name__)


class ProductSerializer(serializers.ModelSerializer):
    upc = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Product
        read_only_fields = ['supply']
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the supply passed via context
        """
        supply = self.context['supply']
        
        instance = self.Meta.model.objects.create(supply=supply, **validated_data)

        return instance
        
class SupplySerializer(serializers.ModelSerializer):
    quantity = serializers.DecimalField(decimal_places=2, max_digits=12, required=False)
    description_th = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    type = serializers.CharField(required=False)
    #suppliers = ProductSerializer(source="products", required=False, many=True)
    
    class Meta:
        model = Supply
        #read_only_fields = ['suppliers']
        exclude = ['quantity_th', 'quantity_kh']
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method to allow integration of products into 
        output data
        """
        ret = super(SupplySerializer, self).to_representation(instance)
        
        view = self.context['view']
        if view.lookup_field in view.kwargs or self.context['request'].method.lower() in ['put', 'post']:
            ret['suppliers'] = [{'id': product.id,
                                 'supplier': {'id': product.supplier.id,
                                              'name': product.supplier.name},
                                 'cost': product.cost,
                                 'reference': product.reference,
                                 'purchasing_units': product.purchasing_units,
                                 'quantity_per_purchasing_unit': product.quantity_per_purchasing_unit,
                                 'upc': product.upc} for product in instance.products.all()]
        else:
            try:
                if 'supplier_id' in self.context['request'].query_params:
                    instance.supplier = Supplier.objects.get(pk=self.context['request'].query_params['supplier_id'])
            
                    ret['unit_cost'] = instance.cost
                    ret['cost'] = instance.cost
                    ret['reference'] = instance.reference
            
            except KeyError:
                pass
            
        ret['quantity'] = instance.quantity
           
        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url()}
        except AttributeError: 
            pass
            
        return ret
        
    def create(self, validated_data):
        """
        Override the 'create' method in order to customize creation of products
        """
        if 'supplier' in validated_data:
            suppliers_data = [validated_data.pop('supplier')]
        elif 'suppliers' in validated_data:
            suppliers_data = validated_data.pop('suppliers')
        else:

            data = {}
            for field in ['cost', 'reference', 'purchasing_units', 'quantity_per_purchasing_units', 'upc']:
                try:
                    data[field] = self.context['request'].data[field]
                except KeyError:
                    pass
            data['supplier'] = self.context['request'].data['supplier']
                    
            suppliers_data = [data]
            
        instance = self.Meta.model.objects.create(**validated_data)
        
        product_serializer = ProductSerializer(data=suppliers_data, context={'supply': instance}, many=True)
        if product_serializer.is_valid(raise_exception=True):
            product_serializer.save()
            
        return instance
    def update(self, instance, validated_data):
        """
        Override the 'update' method in order to customize create, update and delete of products
        """
        try:
            products_data = validated_data.pop('suppliers')
        except KeyError:
            products_data = validated_data.pop('products', None)
            
        logger.debug(products_data)
        old_quantity = instance.quantity
        new_quantity = validated_data['quantity']
        logger.debug(validated_data)
        logger.debug(products_data)
        for field in validated_data.keys():
            setattr(instance, field, validated_data[field])
        
        if products_data:
            product_serializer = ProductSerializer(data=products_data, context={'supply': instance}, many=True)
            if product_serializer.is_valid(raise_exception=True):
                product_serializer.save()
        
        instance.save()
        
        self._log_quantity(instance, old_quantity, new_quantity)
        
        return instance
        
    def _log_quantity(self, obj, old_quantity, new_quantity):
        """
        Internal method to apply the new quantity to the obj and
        create a log of the quantity change
        """
        new_quantity = Decimal(str(new_quantity))
        
        #Type change to ensure that calculations are only between Decimals
        old_quantity = Decimal(str(old_quantity))
        
        if new_quantity < 0:
            raise ValueError('Quantity cannot be negative')
            
        if new_quantity != old_quantity:
            if new_quantity > old_quantity:
                action = 'ADD'
                diff = new_quantity - old_quantity
            elif new_quantity < old_quantity:
                action = 'SUBTRACT'
                diff = old_quantity - new_quantity
            
            #Create log to track quantity changes
            log = Log(supply=obj, 
                      action=action,
                      quantity=diff,
                      message=u"{0}ed {1}{2} {3} {4}".format(action.capitalize(),
                                                             diff,
                                                             obj.units,
                                                             "to" if action == "ADD" else "from",
                                                             obj.description))
            
            #Save log                                               
            log.save()
        
 
class FabricSerializer(SupplySerializer):
    content = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Fabric
        
        
class LogSerializer(serializers.ModelSerializer):
    supply = SupplySerializer()
    
    class Meta:
        model = Log
