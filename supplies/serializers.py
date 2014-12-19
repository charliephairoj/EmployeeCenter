from decimal import Decimal
import logging

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Supply, Product, Fabric, Log
from contacts.serializers import SupplierSerializer


logger = logging.getLogger(__name__)

class ProductListSerializer(serializers.ListSerializer):
    
    def create(self, validated_data):
        """
        Override the 'create' method
        
        We separate the data with ids, which will be used to update existing products. After
        the existing products are updated or deleted, then new products are created for data
        without ids
        """
        """
        #Extract data for existing products
        data_to_update = []
        for index, product in enumerate(validated_data):
            if "id" in product:
                data_to_update.append(validated_data.pop(index))
        
        #Update existing products with extracted data
        self.update(Product.objects.filter(supply=self.context['supply']), data_to_update)
        
        #Create new products for data without ids
        return super(ProductListSerializer, self).create(validated_data)
        """
        return self.update(Product.objects.filter(supply=self.context['supply']), validated_data)
        
    def update(self, instance, validated_data):
        """
        Implement 'update' method
        
        This method will both create and update existing products, based on whether there is an
        id present in the data
        """
        
        # Maps for id->instance and id->data item.
        """
        try:
            product_mapping = {product.id: product for product in instance}
            data_mapping = {int(item.get('id', 0)): item for item in validated_data}
        except SyntaxError as e:
            """
        product_mapping = {}
        for product in instance:
            product_mapping[product.id] = product
    
        data_mapping = {}
        for item in validated_data:
            data_mapping[int(item.get('id', 0))] = item
            
        # Perform creations and updates.
        ret = []
        for product_id, data in data_mapping.items():
            product = product_mapping.get(product_id, None)
            logger.debug(product)
            if product is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(product, data))

        # Perform deletions.
        for product_id, product in product_mapping.items():
            if product_id not in data_mapping:
                product.delete()

        return ret
        
    
class ProductSerializer(serializers.ModelSerializer):
    upc = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    id = serializers.CharField(write_only=True, required=False)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    purchasing_units = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quantity_per_purchasing_unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Product
        read_only_fields = ['supply']
        list_serializer_class = ProductListSerializer
        
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
    type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    suppliers = ProductSerializer(source="products", required=False, many=True)
    
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
            
        old_quantity = instance.quantity
        new_quantity = validated_data['quantity']

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
