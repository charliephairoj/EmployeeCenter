#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
from datetime import datetime
from pytz import timezone

from django.template.loader import render_to_string
from rest_framework import serializers
import boto.ses

from administrator.models import User
from administrator.serializers import LogFieldSerializer
from contacts.models import Supplier
from supplies.models import Supply, Product, Log
from po.models import PurchaseOrder, Item, Log as POLog, File
from projects.models import Project, Room, Phase
from projects.serializers import RoomFieldSerializer, PhaseFieldSerializer, ProjectFieldSerializer
from contacts.serializers import AddressSerializer, SupplierSerializer, SupplierFieldSerializer
from acknowledgements.models import Acknowledgement
from acknowledgements.serializers import AcknowledgementFieldSerializer
from media.serializers import S3ObjectFieldSerializer
from supplies.serializers import SupplyFieldSerializer
from media.models import S3Object
from po.purchase_order import service as po_service
from supplies import service as supply_service
from administrator.user import service as user_service
from contacts.supplier import service as supplier_service


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = SupplyFieldSerializer(required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    units = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    id = serializers.IntegerField(required=False, allow_null=True)
    image = serializers.SerializerMethodField()
    cost = serializers.DecimalField(default=0, allow_null=True, decimal_places=2, max_digits=15)

    class Meta:
        model = Item
        read_only_fields = ('total', 'sticker')
        exclude = ('purchase_order', )
        depth = 2

    def to_internal_value(self, data):

        # Create supply
        if "supply" not in data:
            if "id" in data:
                data['supply'] = {'id': data['id']}
                del data['id']
        


        ret = super(ItemSerializer, self).to_internal_value(data)

        """
        Processing supply object deserialization

        1.  Get by ID
        2.  If Supply Does Not Exist by ID raise warning
        3.  If Key Error
            3.1 If data has "id" but not "supply" try getting by id
                3.1.1 If Supply.DoesNotExist try searching by item id
        """

        user = user_service.get_by_context(self)
        try:
            supplier = supplier_service.get(pk=self.parent.parent.initial_data['supplier']['id'])
        except (AttributeError, KeyError) as e:
            supplier = self.context['supplier']
        
        try:
            ret['supply'] = supply_service.get(pk=data['supply']['id'])
        except Supply.DoesNotExist as e:
            
            raise ValueError("supply with id should be findable with id of {0}".format(data['supply']['id']))

        except KeyError as e:

            if "supply" not in data and "id" in data:
                try:
                    ret['supply'] = supply_service.get(data['id'])
                except Supply.DoesNotExist as e:
                    try:
                        ret['supply'] = po_service.get_item(pk=data['id']).supply
                    except Item.DoesNotExist as e:
                        pass

            try:
                ret['supply'] = supply_service.get_by_description_and_supplier(description=data['description'],
                                                                               supplier=supplier)
            except Product.DoesNotExist as e:

                # Create a new Supply
                ret['supply'] = supply_service.create_supply_and_product(user, 
                                                                         supplier,
                                                                         **data)

            except KeyError as e:
                ret['supply'] = supply_service.create_supply_and_product(user, 
                                                                         supplier,
                                                                         **data)
            except Product.MultipleObjectsReturned as e:
                ret['supply'] = Product.objects.filter(supply__description=data['description'],              
                                                       supplier=supplier).order_by('-id')[0].supply

        if "description" not in ret:
            ret['description'] = ret['supply'].description

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method for Item Serializer
        """
        supply = validated_data.pop('supply')
        supply.supplier = self.context['supplier']
        purchase_order = self.context['po']

        logger.debug(u"{0}: {1}:{2}".format(supply.description, 
                                           validated_data.get('unit_cost'),
                                           supply.cost))

        # Confirm that the supply has a product
        if Product.objects.filter(supplier=purchase_order.supplier, supply=supply).count() == 0:
            p = supply_service.create_product(supplier=purchase_order.supplier,
                                              supply=supply,
                                              purchasing_units=validated_data.get('units', supply.units),
                                              cost=validated_data.get('unit_cost', 0))

        description = validated_data.pop('description', supply.description)
        # Attemp to get 'unit_cost' in the following order:
        # 1. key: 'unit_cost'
        # 2. key: 'cost'
        # 3. supply.cost
        unit_cost = Decimal(validated_data.pop('unit_cost', validated_data.pop('cost', supply.cost)))
        discount = validated_data.pop('discount', supply.discount)
        units = validated_data.pop('units', supply.units)

        instance = po_service.create_item(purchase_order=purchase_order,
                                          supply=supply,
                                          description=description,
                                          unit_cost=unit_cost,
                                          **validated_data)

        if unit_cost != supply.cost:
            self._change_supply_cost(supply, unit_cost)

        return instance

    def update(self, instance, validated_data):
        """
        Override the 'update' method
        """

        instance.supply.supplier = self.context['supplier']

        # Confirm that the supply has a product
        if Product.objects.filter(supplier=instance.supply.supplier, supply=instance.supply).count() == 0:
            p = Product.objects.create(supplier=instance.supply.supplier,
                                       supply=instance.supply,
                                       purchasing_units=validated_data.get('units', instance.supply.units),
                                       cost=validated_data.get('unit_cost', 0))

        instance.description = validated_data.pop('description', instance.description)
        instance.unit_cost = Decimal(validated_data.pop('unit_cost', validated_data.pop('cost', instance.supply.cost)))
        instance.quantity = Decimal(validated_data.get('quantity', instance.quantity))
        instance.discount = validated_data.get('discount', instance.discount)
        instance.comments = validated_data.get('comments', instance.comments)
        units = validated_data.pop('units', instance.supply.units)
        instance.save()

        instance.calculate_total()
        instance.save()

        #Check status change
        new_status = validated_data.get('status', instance.status)

        if new_status != instance.status and instance.status.lower() in ["awaiting approval", "ordered"]:
            instance.status = new_status
            instance.save()
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
            self._change_supply_cost(instance.supply, instance.unit_cost, units)

        
        assert instance == instance.purchase_order.items.get(pk=instance.pk)


        return instance

    def get_image(self, instance):
        """
        Get Supply Image
        """
        try:
            return S3ObjectFieldSerializer(instance.supply.image).data
        except AttributeError as e:
            logger.warn(e)
            return None

    def _change_supply_cost(self, supply, cost, units="pc"):
        """
        Method to change the cost of a supply

        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        try:
            product = Product.objects.get(supply=supply, supplier=supply.supplier)
        except Product.MultipleObjectsReturned as e:
            logger.debug(e)
            product = Product.objects.filter(supply=supply, supplier=supply.supplier).order_by('id')[0]
        except Product.DoesNotExist as e:
            logger.debug(e)
            logger.debug(supply.supplier.__dict__)
            logger.debug(supply.__dict__)
            product = Product.objects.create(supplier=supply.supplier, supply=supply,
                                             purchasing_units=units, cost=cost)

        old_price = product.cost
        product.cost = cost
        product.purchasing_units = units
        product.save()

        log = Log(supply=supply,
                  supplier=supply.supplier,
                  action="PRICE CHANGE",
                  quantity=None,
                  cost=product.cost,
                  message=u"Price change from {0:.2f}{2} to {1:.2f}{2} for {3} [Supplier: {4}]".format(old_price,
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
    supplier = SupplierSerializer()
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    phase = PhaseFieldSerializer(allow_null=True, required=False)
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    items = ItemSerializer(many=True)
    order_date = serializers.DateTimeField(read_only=True)
    pdf = S3ObjectFieldSerializer(read_only=True)
    auto_print_pdf = S3ObjectFieldSerializer(read_only=True)
    logs = LogFieldSerializer(many=True, read_only=True)
    approval_pass = serializers.SerializerMethodField(read_only=True)
    files = S3ObjectFieldSerializer(many=True, allow_null=True, required=False)
    comments = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    terms = serializers.CharField(allow_null=False, required=True)

    # Payment Documents
    deposit_document = S3ObjectFieldSerializer(required=False, allow_null=True)
    balance_document = S3ObjectFieldSerializer(required=False, allow_null=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ('company', 'vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'room',
                  'subtotal', 'total', 'revision', 'paid_date', 'receive_date', 'deposit',
                  'discount', 'status', 'terms', 'order_date', 'currency', 'phase', 'comments', 
                  'acknowledgement', 'pdf', 'auto_print_pdf', 'logs', 'approval_pass', 'files',
                  'deposit_document', 'balance_document', 'terms')
        depth = 1
        read_only_fields = ('pdf', 'revision', 'auto_print_pdf', 'logs', 'approval_pass')

    def to_internal_value(self, data):
        ret = super(PurchaseOrderSerializer, self).to_internal_value(data)

        try:
            ret['supplier'] = Supplier.objects.get(pk=data['supplier']['id'])
        except (Supplier.DoesNotExist, KeyError) as e:
            try:
                ret['supplier'] = Supplier.objects.get(name=data['supplier']['name'])
            except Supplier.DoesNotExist as e:
                ret['supplier'] = Supplier.objects.create(**data['supplier'])
            except Supplier.MultipleObjectsReturned as e:
                logger.warn(e)

        library = {'project': Project, 
                   'room': Room,
                   'phase': Phase}
        for key  in library:
            try:
                ret[key] = library[key].objects.get(pk=data[key]['id'])
            except (library[key].DoesNotExist, KeyError, TypeError) as e:

                try:
                    ret[key] = library[key].objects.create(**data[key])
                except (KeyError, TypeError) as e:
                    pass
        
        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError, TypeError) as e:
            try:
                del ret['acknowledgement']
            except KeyError as e: 
                pass

        for doc_type in ['deposit_document', 'balance_document']:
            try:
                ret[doc_type] = S3Object.objects.get(pk=data[doc_type]['id'])
            except (KeyError, S3Object.DoesNotExist, TypeError) as e:
                try:
                    del ret[doc_type]
                except KeyError:
                    pass

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method to customize how items are created and pass the supplier instance
        to the item serializer via context
        """
        employee = self.context['request'].user

        #Discard status
        status = validated_data.pop('status', 'AWAITING APPROVAL')
        items_data = validated_data.pop('items')
        files = validated_data.pop('files', [])


        data = {}
        for key in ['currency', 'discount', 'terms']:
            try:
                data[key] = validated_data.pop(key, getattr(validated_data['supplier'], key))
            except AttributeError as e:
                data[key] = getattr(validated_data['supplier'], key)
                
        #currency = validated_data.pop('currency', validated_data['supplier'].currency)
        #discount = validated_data.pop('discount', None) or validated_data['supplier'].discount
        #terms = validated_data.pop('terms', validated_data['supplier'].terms)
        receive_date = timezone('Asia/Bangkok').normalize(validated_data.pop('receive_date'))

        instance = po_service.create(employee=employee, 
                                     currency=data['currency'],
                                     terms=data['terms'],
                                     discount=data['discount'],
                                     receive_date=receive_date,
                                     status="AWAITING APPROVAL",
                                     **validated_data)

        raw_items_data = self.initial_data['items']
        # Format items data by moving supply id to supply attribute
        for item_data in raw_items_data:
            if "id" in item_data:
                item_data['supply'] = {'id': item_data['id']}
                del item_data['id']

        item_serializer = ItemSerializer(data=raw_items_data, 
                                         context={
                                            'supplier': instance.supplier, 
                                            'po':instance,
                                            'request': self.context['request']
                                         },
                                         many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
        
        po_service.post_create(employee=employee, 
                               po=instance, 
                               files=files)

        return instance

    def update(self, instance, validated_data):
        """
        Update Purchase Order

        1. Get current user
        2. Update associated models
        3. Update Order terms and details
        4. Attach files
        5. Attach Payment Documents
        6. Update Status
        7. Update Items
        8. Calcuate a new total
        9. Create a new pdf
        """

        
        # Get the current user
        try:
            employee = self.context['request'].user
        except KeyError as e:
            employee = self.context['employee']
        
        instance.current_user = employee

        # Section: Update order terms and details
        # 
        # We loop through properties, apply changes 
        # and log the changes        
        fields = ['vat',
                  'discount',
                  'deposit',
                  'currency',
                  'terms',
                  'acknowledgement',
                  'project',
                  'room',
                  'phase']
        for field in fields:
            old_val = getattr(instance, field)
            new_val = validated_data.pop(field, old_val)
            
            if new_val != old_val:
                setattr(instance, field, new_val)

                self._log_change(field, old_val, new_val)

        receive_date = timezone('Asia/Bangkok').normalize(validated_data.pop('receive_date'))
        if receive_date != instance.receive_date:
            old_rd = instance.receive_date
            instance.receive_date = receive_date
            
            self._log_change('receive date', old_rd.strftime('%d/%m/%Y'), receive_date.strftime('%d/%m/%Y'))

        instance.save()
        
        # Section: Update payment documents
        # 
        # We loop through properties, apply changes 
        # and log the changes
        if employee.has_perm('po.change_purchaseorder_deposit_document'):
            instance.deposit_document = validated_data.pop('deposit_document', instance.deposit_document)

        if employee.has_perm('po.change_purchaseorder_balance_document'):
            instance.balance_document = validated_data.pop('balance_document', instance.balance_document)

        #Update attached files
        files = validated_data.pop('files', [])
        for file_obj in files:
            try:
                File.objects.get(file_id=file_obj['id'], purchase_order=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file_obj['id']),
                                    purchase_order=instance)
        
        instance.save()
        
        # Process if status has changed
        new_status = validated_data.pop('status', instance.status)
        old_status = instance.status

        if new_status.lower() != old_status.lower():

            # Check permissions
            if old_status.lower() == 'awaiting approval' and new_status.lower() != 'received':
                if employee.has_perm('po.approve_purchaseorder'):
                    instance.approve(user=employee)

                    self._log_change('status', old_status, new_status)
                else:
                    logger.warn(u"{0} is not qualified.".format(employee.username))
            else:

                instance.status = new_status

                if old_status.lower() != "ordered" and instance.status.lower() == "received":
                    self.receive_order(instance, validated_data)

                instance.save()

                self._log_change('status', old_status, new_status)

        
        items_data = self.initial_data['items']#validated_data.pop('items', self.context['request'].data['items'])


        self._update_items(instance, items_data)

            
        instance.calculate_totals()

        instance.revision += 1

        instance.save()

        instance.create_and_upload_pdf()

        instance.save()

        try:
            instance.update_calendar_event()
        except Exception as e:
            try:
                message = "Unable to create calendar event because: {0}"
                message = message.format(e)
                POLog.objects.create(message=message, purchase_order=instance, user=employee)
            except ValueError as e:
                logger.warn(e)

        return instance
    
    def get_approval_pass(self, instance):
        """
        Returns the approval pass if this order has been approved
        """
        if instance.approval_pass:
            if instance.approval_pass == instance.create_approval_pass():
                return instance.approval_pass

        return None

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

        for item_data in validated_data['items']:
            item_data['status'] = "RECEIVED"

        self._email_purchaser(instance)

        return instance


    def _apply_new_quantity(self, item, po):
        # Retrieve product responding to this item and supplier
        try:
            product = Product.objects.get(supply=item.supply,
                                          supplier=po.supplier)
        except Product.MultipleObjectsReturned as e:
            logger.warn(e)
            products = Product.objects.filter(supply=item.supply, supplier=po.supplier)
            product = products.order_by('id')[0]
        except Product.DoesNotExist as e:
            msg = u"There is no product for supply {0}: {1} and supplier {2}: {3}\n\n{4}"
            msg = msg.format(item.supply.id,
                             item.supply.description,
                             po.supplier.id,
                             po.supplier.name,
                             e)
            try:           
                product = Product.objects.create(supply=item.supply, 
                                             supplier=po.supplier,
                                             cost=item.unit_cost)
            except TypeError as e:
                product = Product.objects.create(supply=item.supply, 
                                             supplier=po.supplier,
                                             cost=item.cost)

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
                item = po_service.get_item(pk=item_data['id'], purchase_order=instance)
                item_data['purchase_order'] = instance
                serializer = ItemSerializer(item, 
                                            context={
                                                'supplier': instance.supplier, 
                                                'po': instance,
                                                'request': self.context['request']
                                            },
                                            data=item_data)
            except(KeyError, Item.DoesNotExist) as e:
                serializer = ItemSerializer(data=item_data,
                                            context={
                                                'supplier': instance.supplier,
                                                'po': instance,
                                                'request': self.context['request']
                                            })
            
            if serializer.is_valid(raise_exception=True):
                saved_item = serializer.save()
                if saved_item.id not in id_list:
                    instance.items.add(saved_item)
                    id_list.append(saved_item.id)

        logger.debug(id_list)
        #Delete Items
        for d_item in instance.items.all():
            if d_item.id not in id_list:
                logger.debug(u'Deleting item {0}'.format(d_item.id))
                d_item.delete()

        # Check correct quantity of items
        assert len(filter(lambda x: x if x is not None else False, id_list)) == instance.items.all().count()

    def _change_supply_cost(self, supply, cost):
        """
        Method to change the cost of a supply

        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        try:
            product = Product.objects.get(supply=supply, supplier=supply.supplier)
        except Product.MultipleObjectsReturned:
            product = Product.objects.filter(supply=supply, supplier=supply.supplier).order_by('id')[0]

        old_price = product.cost
        product.cost = cost
        product.save()

        log = Log(supply=supply,
                  supplier=supply.supplier,
                  action="PRICE CHANGE",
                  quantity=None,
                  cost=product.cost,
                  message=u"Price change from {0:.2f}{2} to {1:.2f}{2} for {3} [Supplier: {4}]".format(old_price,
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
                  message=u"Received {0:.0f}{1} of {2} from {3}".format(item.quantity,
                                                                   supply.purchasing_units,
                                                                   supply.description,
                                                                   item.purchase_order.supplier.name))
        log.save()

    def _log_change(self, prop, old_value, new_value, instance=None, employee=None):
        # Note: Log Changes to specified properties
        if instance is None:
            instance = self.instance

        if employee is None:
            employee = self.context['request'].user

        message = u"Purchase Order #{0}: {1} changed from {2} to {3}."
        message = message.format(instance.id, prop, old_value, new_value)
        POLog.create(message=message, purchase_order=instance, user=employee)

    def _email_purchaser(self, purchase_order):
        logger.debug(purchase_order.employee)
        if purchase_order.employee.email:
            conn = boto.ses.connect_to_region('us-east-1')
            recipients = [purchase_order.employee.email, 'charliep@alineagroup.co']

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

   

class PurchaseOrderFieldSerializer(serializers.ModelSerializer):
    project = ProjectFieldSerializer(required=False, allow_null=True)
    acknowledgement = AcknowledgementFieldSerializer(required=False, allow_null=True)
    order_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('id', 'project', 'grand_total',
                  'subtotal', 'total', 'revision', 'paid_date', 'receive_date', 'deposit',
                  'discount', 'status', 'terms', 'order_date', 'currency')
        depth = 1
