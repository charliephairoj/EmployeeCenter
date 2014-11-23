import logging
import decimal

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Product, Log
from po.models import PurchaseOrder, Item


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = serializers.PrimaryKeyRelatedField()
    
    class Meta:
        model = Item
        fields = ('id', 'quantity', 'discount', 'supply', 'unit_cost', 'description', 'total')
        read_only_fields = ('description', 'total')
            
    def restore_object(self, attrs, instance=None):
        """
        Override the 'restore_object' method
        """
        logger.debug('test')
        if not instance:
            return self.create(attrs, instance)
        else:
            return self.update(attrs, instance)
                    
    def create(self, attrs, instance):
        
        instance = super(ItemSerializer, self).restore_object(attrs, instance)
        
        #Set the description if not already set
        if not instance.description:
            instance.description = instance.supply.description
            
        instance.supply.supplier = Supplier.objects.get(pk=self.context.get('request').DATA['supplier'])
        
        #Change the price of the supply on the fly: will result in permanent price change and log of price change
        if instance.unit_cost != instance.supply.cost:
            self._change_supply_cost(instance.supply, instance.unit_cost)
            
        instance.calculate_total()

        return instance
        
    def update(self, attrs, instance):
        
        instance = super(ItemSerializer, self).restore_object(attrs, instance)
        
        instance.supply.supplier = Supplier.objects.get(pk=self.context.get('request').DATA['supplier'])
        
        #Change the price of the supply on the fly: will result in permanent price change and log of price change
        if instance.unit_cost != instance.supply.cost:
            self._change_supply_cost(instance.supply, instance.unit_cost)
            
        instance.calculate_total()
        
        logger.debug(instance.__dict__)
        
        return instance
    
    def _change_supply_cost(self, supply, cost):
        """
        Method to change the cost of a supply
        
        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        product = Product.objects.get(supply=supply, supplier=supply.supplier)
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
    supplier = serializers.PrimaryKeyRelatedField()
    project = serializers.PrimaryKeyRelatedField(required=False)
    items = ItemSerializer(many=True, allow_add_remove=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'subtotal', 'total', 'revision', 'pdf', 'discount', 'status')
        read_only_fields = ('pdf', 'revision')
        
    def restore_object(self, attrs, instance=None):
        """
        Override the 'restore_object' method
        """
        if instance:
            create = False
        else:
            create = True
            
        instance = super(PurchaseOrderSerializer, self).restore_object(attrs, instance)
        
        if not create:
            instance.revision += 1
            
        return instance
        
    def transform_supplier(self, obj, value):
        """
        Modify how supplier is serialized
        """
        return {'id': obj.supplier.id,
                'name': obj.supplier.name}
                
    def transform_pdf(self, obj, value):
        """
        Modify how pdf object is serialized
        """
        try:
            return {'url': obj.pdf.generate_url()}
        except AttributeError:
            return {'url': ''}
            
    def transform_project(self, obj, value):
        try:
            return {'id': obj.project.id,
                    'codename': obj.project.codename}
        except AttributeError:
            return None