import logging
import decimal
from decimal import Decimal
from datetime import datetime
from pytz import timezone

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Supply, Product, Log
from po.models import PurchaseOrder, Item
from projects.models import Project


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = serializers.PrimaryKeyRelatedField(queryset=Supply.objects.all())
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    class Meta:
        model = Item
        read_only_fields = ('total', 'sticker')
        exclude = ('purchase_order', )
                    
    def create(self, validated_data):
        """
        Override the 'create' method
        """
        supply = validated_data['supply']
        supply.supplier = self.context['supplier']
        purchase_order = self.context['po']
        description = validated_data.pop('description', None) or supply.description
        unit_cost = validated_data.pop('unit_cost', None) or supply.cost
        discount = validated_data.pop('discount', None) or supply.discount
        
        instance = self.Meta.model.objects.create(description=description, purchase_order=purchase_order,
                                                  unit_cost=unit_cost, **validated_data)
        instance.calculate_total()
        
        instance.save()
        
        if unit_cost != supply.cost:
            self._change_supply_cost(supply, unit_cost)
            
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method
        """
        instance.supply.supplier = self.context['supplier']
        instance.description = validated_data.pop('description', None) or instance.description
        instance.unit_cost = validated_data.pop('unit_cost', None) or instance.supply.cost
        instance.quantity = Decimal(validated_data.get('quantity'))
        instance.discount = validated_data.get('discount', None) or instance.discount
        instance.comments = validated_data.get('comments', None) or instance.comments
        instance.calculate_total()
        instance.save()
        
        #Check status change
        new_status = validated_data.get('status', instance.status)
        if new_status != instance.status and instance.status.lower() == "ordered":
            instance.status = new_status
            old_quantity = instance.supply.quantity
            instance.supply.quantity += float(str(instance.quantity))
            new_quantity = instance.supply.quantity
            instance.supply.save()
            self._log_quantity_change(instance.supply, old_quantity, new_quantity)
            
        if instance.unit_cost != instance.supply.cost:
            self._change_supply_cost(instance.supply, instance.unit_cost)
            
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
        
    def _log_quantity_change(self, obj, old_quantity, new_quantity, employee=None):
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
                      employee=employee,
                      message=u"{0}ed {1}{2} {3} {4}".format(action.capitalize(),
                                                             diff,
                                                             obj.units,
                                                             "to" if action == "ADD" else "from",
                                                             obj.description))
            
            #Save log                                               
            log.save()
        
        
class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    project = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Project.objects.all())
    items = ItemSerializer(many=True)
    order_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'subtotal', 'total', 'revision', 'pdf', 
                  'discount', 'status', 'terms', 'order_date')
                 
        read_only_fields = ('pdf', 'revision')
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' in order to customize output for supplier
        """
        ret = super(PurchaseOrderSerializer, self).to_representation(instance)

        ret['supplier'] = {'id': instance.supplier.id, 
                           'name': instance.supplier.name}
        
        try:
            ret['project'] = {'id': instance.project.id,
                              'codename': instance.project.codename}
        except AttributeError:
            pass
            
        try:
            ret['pdf'] = {'url': instance.pdf.generate_url()}
        except AttributeError:
            pass
            
        return ret
        
    def create(self, validated_data):
        """
        Override the 'create' method to customize how items are created and pass the supplier instance
        to the item serializer via context
        """
        items_data = validated_data.pop('items')
        for item_data in items_data:
            try:
                item_data['supply'] = item_data['supply'].id
            except AttributeError:
                item_data['supply'] = item_data['supply']['id']
                
        discount = validated_data.pop('discount', None) or validated_data['supplier'].discount
            
        instance = self.Meta.model.objects.create(employee=self.context['request'].user, discount=discount,
                                                  **validated_data)
        
        item_serializer = ItemSerializer(data=items_data, context={'supplier': instance.supplier, 'po':instance}, 
                                         many=True)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()

        instance.calculate_total()
        
        instance.create_and_upload_pdf()
        
        instance.save()
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method in order to increase the revision number and create a new version of the pdf
        """
        items_data = validated_data.pop('items')
        items_data = self.context['request'].data['items']
        for item_data in items_data:
            try:
                item_data['supply'] = item_data['supply'].id
            except AttributeError:
                try:
                    item_data['supply'] = item_data['supply']['id']
                except TypeError:
                    pass
                    
        self._update_items(instance, items_data)
        
        instance.order_date = datetime.now(timezone('Asia/Bangkok'))
        instance.revision += 1
        instance.discount = validated_data.pop('discount', None) or instance.discount
        instance.status = validated_data.pop('status', None) or instance.status
        
        instance.calculate_total()
        
        instance.create_and_upload_pdf()
        
        instance.save()
        
        return instance
        
    def _update_items(self, instance, items_data):
        """
        Handles creation, update, and deletion of items
        """
        #Maps of id
        id_list = [item_data.get('id', None) for item_data in items_data]

        #Update or Create Item
        for item_data in items_data:
            try:
                
                item = Item.objects.get(pk=item_data['id'])
                item_data['purchase_order'] = item.id
                serializer = ItemSerializer(item, context={'supplier': instance.supplier}, data=item_data)
                if serializer.is_valid(raise_exception=True):
                    item = serializer.save()
                
                """
                item.supply.supplier = instance.supplier
                item.discount = item_data.get('discount', None) or item.discount
                item.quantity = item_data.get('quantity', None) or item.quantity
                item.unit_cost = item_data.get('unit_cost', None) or item.unit_cost
                
                #Change the cost of the supply and log price change
                if item.unit_cost != item.supply.cost:
                    self._change_supply_cost(item.supply, item.unit_cost)
                    
                item.calculate_total()
                item.save()
                """
            except KeyError:
                serializer = ItemSerializer(data=item_data, context={'supplier': instance.supplier, 'po': instance})
                if serializer.is_valid(raise_exception=True):
                    item = serializer.save()
                    id_list.append(item.id)

        #Delete Items
        for item in instance.items.all():
            if item.id not in id_list:
                item.delete()
                
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
    
    
    
    
    
    