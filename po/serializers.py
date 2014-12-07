import logging
import decimal

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Product, Log
from po.models import PurchaseOrder, Item
from projects.models import Project


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    
    class Meta:
        model = Item
        fields = ('id', 'quantity', 'discount', 'supply', 'unit_cost', 'description', 'total')
        read_only_fields = ('description', 'total')
            
    def restore_object(self, attrs, instance=None):
        """
        Override the 'restore_object' method
        """
        if not instance:
            return self.create(attrs, instance)
        else:
            return self.update(attrs, instance)
                    
    def create(self, validated_data):
        """
        Override the 'create' method
        """
        supply = validated_data['supply']
        supply.supplier = self.context['supplier']
        description = validated_data.pop('description', None) or supply.description
        unit_cost = validated_data.pop('unit_cost', None) or supply.cost
            
        #Change the price of the supply on the fly: will result in permanent price change and log of price change
        try:
            if instance.unit_cost != instance.supply.cost and instance.unit_cost > 0:
                self._change_supply_cost(instance.supply, instance.unit_cost)
        except ValueError as e:
            logger.debug(e)
            logger.debug(instance.supply.supplier)
            
        instance.calculate_total()

        return instance
        
    def update(self, attrs, instance):
        
        instance = super(ItemSerializer, self).restore_object(attrs, instance)
        
        instance.supply.supplier = Supplier.objects.get(pk=self.context.get('request').DATA['supplier'])
        
        #Change the price of the supply on the fly: will result in permanent price change and log of price change
        try:
            if instance.unit_cost != instance.supply.cost and instance.unit_cost > 0:
                self._change_supply_cost(instance.supply, instance.unit_cost)
        except ValueError:
            logger.debug(instance.supply.supplier)
            
        instance.calculate_total()
        
        logger.debug(instance.__dict__)
        
        return instance
    
    def _change_supply_cost(self, supply, cost):
        """
        Method to change the cost of a supply
        
        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        try:
            product = Product.objects.get(supply=supply, supplier=supply.supplier)
        except Product.MultipleObjectsReturned:
            logger.debug(supply.__dict__)
            logger.debug(supply.supplier)
            raise ValueError('ok')
            
        old_price = product.cost
        product.cost = cost
        product.save()
        
        log = Log(supply=supply,
                  supplier=supply.supplier,
                  action="PRICE CHANGE",
                  quantity=None,
                  cost=product.cost,
                  message=u"Price change from {0}{2} to {1}{2} for {3} [Supplier: {4}]".format(old_price,
                                                                                              product.cost,
                                                                                              supply.supplier.currency,
                                                                                              supply.description,
                                                                                              supply.supplier.name))
        log.save()
        
        
class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    project = serializers.PrimaryKeyRelatedField(required=False, queryset=Project.objects.all())
    items = ItemSerializer(many=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'subtotal', 'total', 'revision', 'pdf', 'discount', 'status')
        read_only_fields = ('pdf', 'revision')
        
    def create(self, validated_data):
        """
        Override the 'create' method to customize how items are created and pass the supplier instance
        to the item serializer via context
        """
        items_data = validated_data.pop('items')
        for item_data in items_data:
            try:
                item_data['supply'] = item_data['supply']['id']
            except KeyError:
                item_data['supply'] = item_data['id']
            
        instance = self.Meta.model.objects.create(**validated_data)
        
        item_serializer = ItemSerializer(data=items_data, context={'supplier': instance.supplier}, many=True)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
            
        return instance
        
    def update(self, instance, validted_data):
        """
        Override the 'update' method in order to increase the revision number and create a new version of the pdf
        """
        revision += instance.revision
        
        instance.save()
        
        return instance
    
    
    
    
    
    