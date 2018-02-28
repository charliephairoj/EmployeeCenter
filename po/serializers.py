
import logging
import decimal
from decimal import Decimal
from datetime import datetime
from pytz import timezone
import httplib2

from django.template.loader import render_to_string
from administrator.models import User
from rest_framework import serializers
import boto.ses
from pytz import timezone

from contacts.models import Supplier
from supplies.models import Supply, Product, Log
from po.models import PurchaseOrder, Item, Log as POLog
from projects.models import Project, Room, Phase
from projects.serializers import RoomSerializer, PhaseSerializer, ProjectSerializer
from contacts.serializers import AddressSerializer, SupplierSerializer
from oauth2client.contrib.django_orm import Storage
from apiclient import discovery
from acknowledgements.models import Acknowledgement
from acknowledgements.serializers import AcknowledgementSerializer

from administrator.models import CredentialsModel


logger = logging.getLogger(__name__)


class ItemSerializer(serializers.ModelSerializer):
    supply = serializers.PrimaryKeyRelatedField(queryset=Supply.objects.all())
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    units = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Item
        read_only_fields = ('total', 'sticker')
        exclude = ('purchase_order', )
        depth = 1

    def create(self, validated_data):
        """
        Override the 'create' method
        """
        supply = validated_data['supply']
        supply.supplier = self.context['supplier']
        purchase_order = self.context['po']
        logger.debug(validated_data)
        logger.debug(u"{0}: {1}:{2}".format(supply.description, 
                                           validated_data.get('unit_cost'),
                                           supply.cost))

        # Confirm that the supply has a product
        if Product.objects.filter(supplier=purchase_order.supplier, supply=supply).count() == 0:
            p = Product.objects.create(supplier=purchase_order.supplier,
                                       supply=supply,
                                       purchasing_units=validated_data.get('units', supply.units),
                                       cost=validated_data.get('unit_cost', 0))

        description = validated_data.pop('description', supply.description)
        unit_cost = validated_data.pop('unit_cost', supply.cost)
        discount = validated_data.pop('discount', supply.discount)
        units = validated_data.pop('units', supply.units)

        instance = self.Meta.model.objects.create(description=description, purchase_order=purchase_order,
                                                  unit_cost=unit_cost, **validated_data)
        instance.calculate_total()

        instance.save()

        logger.debug("{0}:{1}".format(unit_cost, supply.cost))
        if unit_cost != supply.cost:
            self._change_supply_cost(supply, unit_cost)

        logger.debug(supply.cost)

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
        instance.unit_cost = validated_data.pop('unit_cost', instance.supply.cost)
        instance.quantity = Decimal(validated_data.get('quantity'))
        instance.discount = validated_data.get('discount', instance.discount)
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

        logger.debug(instance.unit_cost)
        logger.debug(instance.supply.cost)
        if instance.unit_cost != instance.supply.cost:
            self._change_supply_cost(instance.supply, instance.unit_cost, units)

        return instance

    def to_representation(self, instance):

        ret = super(ItemSerializer, self).to_representation(instance)

        """
        try:
            product = Product.objects.get(supply=instance.supply,
                                          supplier=instance.purchase_order.supplier)

            ret['units'] = product.purchasing_units

        except Product.DoesNotExist as e:
            logger.warn(e)
            logger.debug(u"{0} : {1}".format(instance.supply.id, instance.description))
            product = None
        except Product.MultipleObjectsReturned:
            product = Product.objects.filter(supply=instance.supply,
                                          supplier=instance.purchase_order.supplier).order_by('id')[0]
            ret['units'] = product.purchasing_units
        """
        try:
            ret['image'] = {'url': instance.supply.image.generate_url(),
                            'id': instance.supply.image.id}
        except AttributeError as e:
            pass
           

        return ret

    def _change_supply_cost(self, supply, cost, units="pc"):
        """
        Method to change the cost of a supply

        This will change the supply's product cost, respective of supplier, in the database
        and will log the event as 'PRICE CHANGE'
        """
        logger.debug(cost)
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
    supplier = SupplierSerializer() #serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    project = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Project.objects.all())
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all(),
                                              allow_null=True,
                                              required=False)
    phase = serializers.PrimaryKeyRelatedField(queryset=Phase.objects.all(),
                                               allow_null=True,
                                               required=False)

    acknowledgement = serializers.PrimaryKeyRelatedField(queryset=Acknowledgement.objects.all(),
                                                         required=False,
                                                         allow_null=True)
    items = ItemSerializer(many=True)
    order_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('company', 'vat', 'supplier', 'id', 'items', 'project', 'grand_total', 'room',
                  'subtotal', 'total', 'revision', 'pdf', 'paid_date', 'receive_date', 'deposit',
                  'discount', 'status', 'terms', 'order_date', 'currency', 'phase', 'comments', 
                  'acknowledgement')

        read_only_fields = ('pdf', 'revision')

    def to_internal_value(self, data):
        ret = super(EstimateSerializer, self).to_internal_value(data)

        try:
            ret['supplier'] = Supplier.objects.get(pk=data['supplier']['id'])
        except (Customer.DoesNotExist, KeyError) as e:
            ret['supplier'] = Supplier.objects.create(**data['supplier'])

        try:
            ret['project'] = Project.objects.get(pk=data['project']['id'])
        except (Project.DoesNotExist, KeyError) as e:

            try:
                ret['project'] = Project.objects.create(**data['project'])
            except KeyError as e:
                pass

        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError, TypeError) as e:
            pass

        return ret

    def to_representation(self, instance):
        """
        Override the 'to_representation' in order to customize output for supplier
        """
        ret = super(PurchaseOrderSerializer, self).to_representation(instance)

        """
        ret['supplier'] = {'id': instance.supplier.id,
                           'name': instance.supplier.name,
                           'email': instance.supplier.email,
                           'telephone': instance.supplier.telephone,
                           'fax': instance.supplier.fax,
                           'addresses': AddressSerializer(instance.supplier.addresses, many=True).data}
        """
        
        try:
            ret['project'] = ProjectSerializer(instance.project).data
        except AttributeError:
            pass

        try:
            ret['acknowledgement'] = ProjectSerializer(instance.acknowledgement).data
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

        try:
            iam_credentials = self.context['request'].user.aws_credentials
            key = iam_credentials.access_key_id
            secret = iam_credentials.secret_access_key
        except AttributeError as e:
            pass


        try:
            ret['pdf'] = {'url': instance.pdf.generate_url(),
                          'filename': instance.pdf.key.split('/')[-1],
                          'id': instance.pdf.id}
        except AttributeError:
            pass

        try:
            ret['auto_print_pdf'] = {'url': instance.auto_print_pdf.generate_url()}
        except AttributeError:
            pass

        try:
            ret['logs'] = [{'message': log.message,
                            #'employee': get_employee(log),
                            'timestamp': log.timestamp} for log in instance.logs]
        except Exception as e:
            logger.debug(e)


        if instance.approval_pass:
            if instance.approval_pass == instance.create_approval_pass():
                ret['approval_pass'] = instance.approval_pass

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method to customize how items are created and pass the supplier instance
        to the item serializer via context
        """
        employee = self.context['request'].user

        items_data = validated_data.pop('items')
        for item_data in items_data:
            try:
                item_data['supply'] = item_data['supply'].id
            except AttributeError:
                item_data['supply'] = item_data['supply']['id']

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

        instance = self.Meta.model.objects.create(employee=employee, 
                                                  currency=data['currency'],
                                                  terms=data['terms'],
                                                  discount=data['discount'],
                                                  receive_date=receive_date,
                                                  status="AWAITING APPROVAL",
                                                  **validated_data)

        item_serializer = ItemSerializer(data=items_data, context={'supplier': instance.supplier, 'po':instance},
                                         many=True)
        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()

        instance.calculate_total()

        instance.create_and_upload_pdf()

        # Create approval key and salt
        instance.approval_key = instance.create_approval_key()
        instance.approval_salt = instance.create_approval_key()

        instance.save()

        

        # Create a calendar event
        try:
            instance.create_calendar_event(employee)
        except Exception as e:
            message = "Unable to create calendar event because: {0}"
            message = message.format(e)
            type_label = "PURCHASE ORDER EMAIL ERROR"
            POLog.create(message=message, purchase_order=instance, user=employee, type=type_label)

        # Log Opening of an order
        message = "Purchase Order #{0} was created.".format(instance.id)
        log = POLog.create(message=message, purchase_order=instance, user=employee)

        try:
            instance.email_approver()
            # Log Opening of an order
            message = "Purchase Order #{0} sent for approval.".format(instance.id)
            log = POLog.create(message=message, purchase_order=instance, user=employee)
        except Exception as e:
            message = "Unable to email approver because: {0}"
            message = message.format(e)
            type_label = "PURCHASE ORDER EMAIL ERROR"
            POLog.create(message=message, purchase_order=instance, user=employee, type=type_label)

        # What is this line for? Unsure.
        #p = Product.objects.get(supplier=instance.supplier, supply=instance.items.all()[0].supply)

        return instance

    def update(self, instance, validated_data):
        """
        Override the 'update' method in order to increase the revision number and create a new version of the pdf
        """

        employee = self.context['request'].user
        
        instance.current_user = employee

        status = validated_data.pop('status', instance.status)
        instance.project = validated_data.pop('project', instance.project)
        instance.room = validated_data.pop('room', instance.room)
        instance.phase = validated_data.pop('phase', instance.phase)
        receive_date = timezone('Asia/Bangkok').normalize(validated_data.pop('receive_date'))

        if receive_date != instance.receive_date:
            old_rd = instance.receive_date
            instance.receive_date = receive_date
           
            # Log changing receive date
            message = "Purchase Order #{0} receive date changed from {1} to {2}."
            message = message.format(instance.id, old_rd.strftime('%d/%m/%Y'), receive_date.strftime('%d/%m/%Y'))
            POLog.create(message=message, purchase_order=instance, user=employee)

        # Process if status has changed
        if status.lower() != instance.status.lower():

            old_status = instance.status
            instance.status = status

            if old_status.lower() == "received" and instance.status.lower() != "received":
                self.receive_order(instance, validated_data)

            instance.save()


            message = "The status of purchase order #{0} has been changed from {1} to {2}.".format(instance.id, 
                                                                                                   old_status.lower(),
                                                                                                   instance.status.lower())
            log = POLog.objects.create(message=message, purchase_order=instance, user=employee)



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

        instance.revision += 1
        """
        instance.vat = validated_data.pop('vat', instance.vat)
        instance.discount = validated_data.pop('discount', instance.discount)
        instance.deposit = validated_data.pop('deposit', instance.deposit)
        """

        fields = ['vat', 'discount', 'deposit', 'currency', 'terms']
        for field in fields:
            old_val = getattr(instance, field)
            new_val = validated_data.pop(field, old_val)
            
            if new_val != old_val:
                setattr(instance, field, new_val)

                # Log changing of values
                message = "Purchase Order #{0}: {1} changed from {2} to {3}."
                message = message.format(instance.id, field, old_val, new_val)
                POLog.create(message=message, purchase_order=instance, user=employee)

        instance.status = status
        instance.calculate_total()

        instance.create_and_upload_pdf()

        instance.save()

        try:
            instance.update_calendar_event()
        except Exception as e:
            message = "Unable to create calendar event because: {0}"
            message = message.format(e)
            POLog.objects.create(message=message, purchase_order=instance, user=employee)

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
            products = Product.objects.filter(supply=item.supply, supplier=po.supplier)
            product = products.order_by('id')[0]
        except Product.DoesNotExist as e:
            msg = "There is no product for supply {0}: {1} and supplier {2}: {3}\n\n{4}"
            msg = msg.format(item.supply.id,
                             item.supply.description,
                             po.supplier.id,
                             po.supplier.name,
                             e)
            product = Product.objects.create(supply=item.supply, 
                                             supplier=po.supplier,
                                             unit_cost=item.unit_cost)

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
        logger.debug(items_data)
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
            except(KeyError, Item.DoesNotExist) as e:

                logger.debug(e)
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
                  message=u"Received {0}{1} of {2} from {3}".format(item.quantity,
                                                                   supply.purchasing_units,
                                                                   supply.description,
                                                                   item.purchase_order.supplier.name))
        log.save()

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

   