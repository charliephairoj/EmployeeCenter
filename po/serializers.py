
import logging
import decimal
from decimal import Decimal
from datetime import datetime
from pytz import timezone
import httplib2

from rest_framework import serializers
import boto.ses

from contacts.models import Supplier
from supplies.models import Supply, Product, Log
from po.models import PurchaseOrder, Item, Log as POLog
from projects.models import Project, Room, Phase
from projects.serializers import RoomSerializer, PhaseSerializer, ProjectSerializer
from contacts.serializers import AddressSerializer
from oauth2client.contrib.django_orm import Storage
from apiclient import discovery

from administrator.models import CredentialsModel


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = serializers.PrimaryKeyRelatedField(queryset=Supply.objects.all())
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    units = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    
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
        units = validated_data.pop('units', supply.units)
        
        instance = self.Meta.model.objects.create(description=description, purchase_order=purchase_order,
                                                  unit_cost=unit_cost, **validated_data)
        instance.calculate_total()
        
        instance.save()
        
        if unit_cost != supply.cost:
            self._change_supply_cost(supply, unit_cost)
            
        # Confirm that the supply has a product
        if Product.objects.filter(supplier=purchase_order.supplier, supply=supply).count() == 0:
            p = Product.objects.create(supplier=purchase_order.supplier, supply=supply, 
                                       purchasing_units=instance.units, cost=unit_cost)
            
            
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method
        """
        
        instance.supply.supplier = self.context['supplier']
        instance.description = validated_data.pop('description', None) or instance.description
        instance.unit_cost = validated_data.pop('unit_cost', instance.supply.cost)
        instance.quantity = Decimal(validated_data.get('quantity'))
        instance.discount = validated_data.get('discount', None) or instance.discount
        instance.comments = validated_data.get('comments', instance.comments)   
        units = validated_data.pop('units', instance.supply.units)     
        
        instance.calculate_total()
        instance.save()        
        
        #Check status change
        new_status = validated_data.get('status', instance.status)
        if new_status != instance.status and instance.status.lower() == "ordered":
            instance.status = new_status
            old_quantity = instance.supply.quantity
            
            #Fix for if adding decimal and supply together
            try:
                instance.supply.quantity += float(str(instance.quantity))
            except TypeError:
                instance.supply.quantity += Decimal(str(instance.quantity))
                
            new_quantity = instance.supply.quantity
            instance.supply.save()
            self._log_quantity_change(instance.supply, old_quantity, new_quantity)
            
        if instance.unit_cost != instance.supply.cost:
            self._change_supply_cost(instance.supply, instance.unit_cost, instance.units)
            
        return instance
    
    def to_representation(self, instance):
        
        ret = super(ItemSerializer, self).to_representation(instance)
        
        try:
            product = Product.objects.get(supply=instance.supply,
                                          supplier=instance.purchase_order.supplier)
                                          
            ret['units'] = product.purchasing_units
            
        except Product.DoesNotExist as e:
            logger.warn(e)
            logger.debug(u"{0} : {1}".format(instance.supply.id, instance.description))
        
        except Product.MultipleObjectsReturned:
            product = Product.objects.filter(supply=instance.supply,
                                          supplier=instance.purchase_order.supplier).order_by('id')[0]     
            ret['units'] = product.purchasing_units
            
        return ret
        
    def _change_supply_cost(self, supply, cost, units="pc"):
        """
        Method to change the cost of a supply
        
        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        try:
            product = Product.objects.get(supply=supply, supplier=supply.supplier)
        except Product.MultipleObjectsReturned:
            product = Product.objects.filter(supply=supply, supplier=supply.supplier).order_by('id')[0]
        except Product.DoesNotExist:
            product = Product.objects.create(supplier=supply.supplier, supply=supply, 
                                             purchasing_units=instance.units, cost=cost)
            
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
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(),
                                              allow_null=True,
                                              required=False)
    phase = serializers.PrimaryKeyRelatedField(queryset=Phase.objects.all(),
                                               allow_null=True,
                                               required=False)
    items = ItemSerializer(many=True)
    order_date = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'room',
                  'subtotal', 'total', 'revision', 'pdf', 'paid_date', 'receive_date', 'deposit',
                  'discount', 'status', 'terms', 'order_date', 'currency', 'phase', 'comments')
                 
        read_only_fields = ('pdf', 'revision')
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' in order to customize output for supplier
        """
        ret = super(PurchaseOrderSerializer, self).to_representation(instance)

        ret['supplier'] = {'id': instance.supplier.id, 
                           'name': instance.supplier.name,
                           'addresses': AddressSerializer(instance.supplier.addresses.all(), many=True).data}
        
        try:
            ret['project'] = ProjectSerializer(instance.project).data
        except AttributeError:
            pass
            
        try:
            ret['phase'] = {'id': instance.phase.id,
                            'description': instance.phase.description}
        except AttributeError:
            pass
            
        try:
            ret['room'] = {'id': instance.room.id,
                           'description': instance.room.description}
        except AttributeError:
            pass
            
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            ret['pdf'] = {'url': instance.pdf.generate_url(key, secret)}
        except AttributeError:
            pass
            
        try:
            ret['auto_print_pdf'] = {'url': instance.auto_print_pdf.generate_url(key, secret)}
        except AttributeError:
            pass
            
        try:
            ret['logs'] = [{'message': log.message,
                            #'employee': get_employee(log),
                            'timestamp': log.timestamp} for log in instance.logs.all()]
        except Exception as e:
            logger.debug(e)
            
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

        currency = validated_data.pop('currency', validated_data['supplier'].currency)
        discount = validated_data.pop('discount', None) or validated_data['supplier'].discount
        terms = validated_data.pop('terms', validated_data['supplier'].terms)
        
        instance = self.Meta.model.objects.create(employee=self.context['request'].user, discount=discount,
                                                  **validated_data)
        instance.currency = currency
        instance.terms = terms

        item_serializer = ItemSerializer(data=items_data, context={'supplier': instance.supplier, 'po':instance}, 
                                         many=True)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()

        instance.calculate_total()
        
        instance.create_and_upload_pdf()
        
        instance.save()
        
        # Log Opening of an order
        message = "Order #{0} was processed.".format(instance.id)
        log = POLog.objects.create(message=message, purchase_order=instance, employee=self.context['request'].user)
                
        return instance
        
    def update(self, instance, validated_data):
        """
        Override the 'update' method in order to increase the revision number and create a new version of the pdf
        """    
        status = validated_data.pop('status', instance.status)
        instance.project = validated_data.pop('project', instance.project)
        instance.room = validated_data.pop('room', instance.room)
        instance.phase = validated_data.pop('phase', instance.phase)
        instance.currency = validated_data.pop('currency', instance.currency)
        
        if status.lower() != instance.status.lower() and status.lower():
            
            if status.lower() == "received" and instance.status.lower() != "received":
                self.receive_order(instance, validated_data)
                
            if instance.status.lower() == 'paid':
                instance.paid_date = datetime.now()
                
            if status.lower() == 'cancelled':
                instance.status = status
                
            employee = self.context['request'].user
            message = "Purchase Order #{0} has been {1}.".format(instance.id, status.lower())
            log = POLog.objects.create(message=message, purchase_order=instance, employee=employee)
            
            # Check if a high level event has ocurrred. If yes, then the status will not change
            statuses = ['processed', 'deposited', 'received', 'invoiced', 'paid', 'cancelled']
            for status in statuses:
                if instance.logs.filter(message__icontains=status).exists():
                    pass #instance.status = status
            
            
            instance.save()
             
        else:  
            items_data = validated_data.pop('items', self.context['request'].data['items'])

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
            instance.vat = validated_data.pop('vat', instance.vat)
            instance.discount = validated_data.pop('discount', instance.discount)
            instance.deposit = validated_data.pop('deposit', instance.deposit)
            instance.status = status
            instance.calculate_total()
        
            instance.create_and_upload_pdf()
        
            instance.save()
        
        return instance
    
    def receive_order(self, instance, validated_data):
        """
        Will received the order and then process the items and the corresponding supplies.
        The quantities for the supplies will automatically increase based on the supplies received
        """
        for item in instance.items.all():
            item.status = "RECEIVED"
            self._apply_new_quantity(item, instance)
                
            item.supply.save()
            item.save()
            self._log_receiving_item(item)
            
        if instance.status.lower() != 'paid':
            instance.status = "RECEIVED"
        instance.receive_date = datetime.now()
        instance.save()
        
        self._email_purchaser(instance)
        
        return instance
        

    def _apply_new_quantity(self, item, po):
        # Retrieve product responding to this item and supplier
        try:
            product = Product.objects.get(supply=item.supply, 
                                          supplier=po.supplier)
        except Product.MultipleObjectsReturned as e:
            logger.warn(e)
            product = Product.objects.filter(supply=item.supply, supplier=po.supplier)[0]
            
        
        #Calculate the quantity to add to current supply qty
        try:
            qty_to_add = Decimal(str(item.quantity)) * product.quantity_per_purchasing_unit
        except TypeError:
            qty_to_add = float(str(item.quantity)) * product.quantity_per_purchasing_unit
         
        #Change the supply's current quantity   
        try:
            item.supply.quantity += Decimal(str(qty_to_add))
        except TypeError:
            item.supply.quantity += float(str(qty_to_add))
                
        return item
        
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
        
    def _log_receiving_item(self, item):
        supply = item.supply
        supply.supplier = item.purchase_order.supplier
        
        log = Log(supply=item.supply,
                  supplier=item.purchase_order.supplier,
                  action="ADD",
                  quantity=item.quantity,
                  message=u"Received {0}{1} of {2} from {3}".format(item.quantity,
                                                                   supply.purchasing_units,
                                                                   supply.description,
                                                                   item.purchase_order.supplier.name))
        log.save()
        
    def _email_purchaser(self, purchase_order):
        logger.debug(purchase_order.employee)
        if purchase_order.employee.email:
            conn = boto.ses.connect_to_region('us-east-1')
            recipients = [purchase_order.employee.email]
            
            #Build the email body
            body = u"""<table><tr><td><h1>Purchase Order Received</h1></td><td></td><td></td></tr>
                             <tr><td>Purchase Order #</td><td>{0}</td><td></td></tr>
                             <tr><td>Supplier</td><td>{1}</td><td></td></tr>
                             <tr><td><h3>Description</h3></td><td><h3>Quantity</h3></td><td><h3>Status</h3></td</tr>
                   """.format(purchase_order.id,
                              purchase_order.supplier.name)
            #Loop through all items to add to the body
            for item in purchase_order.items.all():
                supply = item.supply
                color = u"green" if item.status.lower() == "received" else "red"
                supply.supplier = purchase_order.supplier
                body += u"""<tr><td>{0}</td><td>{1:,.2f}{2}</td><td style="color:{3}">{4}</td></tr>
                        """.format(item.description,
                                   item.quantity,
                                   supply.purchasing_units,
                                   color,
                                   item.status)
            #Closing table tag
            body += u"</table>"                
                    
            #Send email    
            conn.send_email('inventory@dellarobbiathailand.com',
                            u'Purchase Order from {0} Received'.format(purchase_order.supplier.name),
                            body,
                            recipients,
                            format='html')
                               
        
        
        
        
        
        