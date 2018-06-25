#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from decimal import Decimal
import traceback

import boto
from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import DictField
from pytz import timezone

from administrator.models import User
from administrator.serializers import UserFieldSerializer
from acknowledgements.models import Acknowledgement, Item, Pillow, Component, File, Log as AckLog
from contacts.serializers import CustomerFieldSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from projects.serializers import ProjectFieldSerializer, RoomFieldSerializer, PhaseFieldSerializer
from media.serializers import S3ObjectFieldSerializer
from contacts.models import Customer
from products.models import Product
from supplies.models import Fabric, Log
from projects.models import Project, Phase, Room
from media.models import S3Object


logger = logging.getLogger(__name__)


class ComponentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Component
        fields = ('id', 'description', 'quantity')

    def create (self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']
        instance = self.Meta.model.objects.create(item=item, **validated_data)
        return instance

    def to_representation(self, instance):
        ret = super(ComponentSerializer, self).to_representation(instance)
        
        return ret


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    fabric_quantity = serializers.DecimalField(required=False, allow_null=True, decimal_places=2, max_digits=12)

    class Meta:
        model = Pillow
        fields = ('type', 'fabric', 'quantity', 'fabric_quantity')

    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']

        instance = self.Meta.model.objects.create(item=item, **validated_data)

        return instance

    def to_representation(self, instance):
        ret = super(PillowSerializer, self).to_representation(instance)

        try:
            ret['fabric'] = {'id': instance.fabric.id,
                             'description': instance.fabric.description}
        except AttributeError:
            pass

        return ret


class ItemListSerializer(serializers.ListSerializer):
    pass


class ItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(required=False, queryset=Product.objects.all())
    pillows = PillowSerializer(required=False, many=True)
    components = ComponentSerializer(required=False, many=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, default=0)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    #location = serializers.CharField(required=False, allow_null=True)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = S3ObjectFieldSerializer(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    custom_price = serializers.DecimalField(decimal_places=2, max_digits=12, write_only=True, required=False,
                                            allow_null=True)
    fabric_quantity = serializers.DecimalField(decimal_places=2, max_digits=12, required=False,
                                               allow_null=True)
    id = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.CharField(required=False, allow_null=True)

    grades = {'A1': 15,
              'A2': 20,
              'A3': 25,
              'A4': 30,
              'A5': 35,
              'A6': 40}

    class Meta:
        model = Item
        fields = ('description', 'id', 'width', 'depth', 'height', 'fabric_quantity', 'unit_price', 'total', 'product',
                  'pillows', 'comments', 'image', 'units', 'fabric', 'custom_price', 'quantity', 'components', 'type')
        read_only_fields = ('total',)
        list_serializer_class = ItemListSerializer

    def to_internal_value(self, data):
        ret = super(ItemSerializer, self).to_internal_value(data)

        try:
            ret['image'] = S3Object.objects.get(pk=data['image']['id'])
        except (KeyError, S3Object.DoesNotExist, TypeError) as e:
            pass
        
        return ret

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        acknowledgement = self.context['acknowledgement']
        components_data = validated_data.pop('components', None)
        pillow_data = validated_data.pop('pillows', None)
        product = validated_data['product']
        fabric = validated_data.pop('fabric', None)

        try:
            unit_price = validated_data.pop('price', None) or product.calculate_price(self._grades[fabric.grade])
        except AttributeError:
            unit_price = validated_data.pop('price', product.price)
        width = validated_data.pop('width', None) or product.width
        depth = validated_data.pop('depth', None) or product.depth
        height = validated_data.pop('height', None) or product.height
        fabric_quantity = validated_data.pop('fabric_quantity', None)

        instance = self.Meta.model.objects.create(acknowledgement=acknowledgement,
                                                  width=width, depth=depth,
                                                  height=height, fabric=fabric, **validated_data)

        #attach fabric quantity
        instance.fabric_quantity = fabric_quantity

        #Calculate the total price of the item
        if instance.is_custom_size and product.price == unit_price:
            instance._calculate_custom_price()
        else:
            instance.total = (instance.quantity or 1) * (instance.unit_price or 0)

        instance.save()

        if pillow_data:
            pillow_serializer = PillowSerializer(data=pillow_data, context={'item': instance}, many=True)

            if pillow_serializer.is_valid(raise_exception=True):
                pillow_serializer.save()

        if components_data:
            component_serializer = ComponentSerializer(data=components_data, context={'item': instance}, many=True)

            if component_serializer.is_valid(raise_exception=True):
                component_serializer.save()

        return instance

    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """

        # Update attributes from client side details
        acknowledgement = self.context['acknowledgement']
        employee = self.context['employee']
        new_qty = validated_data.pop('quantity', instance.quantity)
        new_price = validated_data.pop('unit_price', instance.unit_price)
        instance.fabric = validated_data.pop('fabric', instance.fabric)
        instance.fabric_quantity = validated_data.pop('fabric_quantity', instance.fabric_quantity)
        instance.comments = validated_data.pop('comments', instance.comments)
        
        if new_qty != instance.quantity:
            # Log Changing delivery date
            message = u"{0} quantity changed from {1} to {2}"
            message = message.format(instance.description, instance.quantity, new_qty)
            AckLog.create(message=message, acknowledgement=instance.acknowledgement, user=employee)
            instance.quantity = new_qty

        if new_price != instance.unit_price:
            # Log Changing delivery date
            message = u"{0} unit price changed from {1} to {2}"
            message = message.format(instance.description, instance.unit_price, new_price)
            AckLog.create(message=message, acknowledgement=instance.acknowledgement, user=employee)
            instance.unit_price = new_price

        # Set the price of the total for this item
        instance.total = instance.quantity * instance.unit_price
        instance.save()

        pillows = validated_data.pop('pillows', [])
        for pillow_data in pillows:
            try:
                pillow = Pillow.objects.get(type=pillow_data['type'], item=instance, fabric=pillow_data['fabric'])
                serializer = PillowSerializer(pillow, data=pillow_data)
            except Pillow.DoesNotExist as e:
                serializer = PillowSerializer(data=pillow_data, context={'item': instance})

            if serializer.is_valid(raise_exception=True):
                serializer.save()

        components = validated_data.pop('components', [])
        for component_data in components:
            try:
                component = Component.objects.get(id=component_data['id'], item=instance)
                serializer = ComponentSerializer(component, data=component_data)
            except KeyError as e:
                logger.debug(e)
                serializer = ComponentSerializer(data=component_data, context={'item': instance})

            if serializer.is_valid(raise_exception=True):
                serializer.save()

        return instance

    def to_representation(self, instance):
        """
        Override the 'to_representation' method to transform the output for related and nested items
        """
        ret = super(ItemSerializer, self).to_representation(instance)

        try:
            ret['fabric'] = {'id': instance.fabric.id,
                             'description': instance.fabric.description}
        except AttributeError:
            pass
        return ret

class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = File
        read_only_fields = ('acknowledgement', 'file')


class AcknowledgementSerializer(serializers.ModelSerializer):
    item_queryset = Item.objects.exclude(deleted=True)

    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer = CustomerFieldSerializer()
    employee = UserFieldSerializer(required=False, read_only=True)
    project = ProjectFieldSerializer(required=False, allow_null=True)
    room = RoomFieldSerializer(allow_null=True, required=False)
    phase = PhaseFieldSerializer(allow_null=True, required=False)
    items = ItemSerializer(item_queryset, many=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shipping_method = serializers.CharField(required=False, allow_null=True)
    fob = serializers.CharField(required=False, allow_null=True)
    files = serializers.ListField(child=serializers.DictField(), write_only=True, required=False,
                                  allow_null=True)
    delivery_date = serializers.DateTimeField(required=True)

    class Meta:
        model = Acknowledgement
        read_only_fields = ('total', 'subtotal', 'time_created')
        write_only_fields = ('items')
        exclude = ('acknowledgement_pdf', 'production_pdf', 'original_acknowledgement_pdf', 'label_pdf', 'trcloud_id',
                   'trcloud_document_number')
        depth = 3

    def to_internal_value(self, data):
        ret = super(AcknowledgementSerializer, self).to_internal_value(data)
        logger.debug(data)

        try:
            ret['customer'] = Customer.objects.get(pk=data['customer']['id'])
        except (Customer.DoesNotExist, KeyError) as e:
            ret['customer'] = Customer.objects.create(**data['customer'])

        try:
            ret['project'] = Project.objects.get(pk=data['project']['id'])
        except (Project.DoesNotExist, KeyError, TypeError) as e:

            try:
                ret['project'] = Project.objects.create(**data['project'])
            except (TypeError) as e:
                logger.warn(e)
                logger.debug(ret['project'])
                try:
                    del ret['project']
                except Exception as e:
                    logger.warn(e)
            except KeyError as e:
                pass

        try:
            ret['acknowledgement'] = Acknowledgement.objects.get(pk=data['acknowledgement']['id'])
        except (Acknowledgement.DoesNotExist, KeyError, TypeError) as e:
            logger.warn(e)

        logger.debug("\n\nEstimate to internal value\n\n")

        return ret

    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """
        items_data = validated_data.pop('items')
        files = validated_data.pop('files', [])
        
        # Get user 
        employee = self.context['request'].user
        if settings.DEBUG:
            employee = User.objects.get(pk=1)
        
        for item_data in items_data:
            for field in ['product', 'fabric']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass

        discount = validated_data.pop('discount', validated_data['customer'].discount)
        delivery_date = timezone('Asia/Bangkok').normalize(validated_data.pop('delivery_date'))

        instance = self.Meta.model.objects.create(employee=employee, discount=discount,
                                                  status='acknowledged', _delivery_date=delivery_date,
                                                  **validated_data)

        item_serializer = ItemSerializer(data=items_data, context={'acknowledgement': instance}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()


        instance.calculate_totals()

        instance.create_and_upload_pdfs()
        
        # Add pdfs to files list
        filenames = ['acknowledgement_pdf', 'production_pdf', 'label_pdf']
        for filename in filenames:
            try:
                File.objects.create(file=getattr(instance, filename),
                                    acknowledgement=instance)
            except Exception as e:
                logger.warn(e)

        # Assign files
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                acknowledgement=instance)


        # Extract fabric quantities
        fabrics = {}

        for item in item_serializer.instance:
            if item.fabric:
                if item.fabric in fabrics:
                    fabrics[item.fabric] += Decimal(str(item.quantity)) * (item.fabric_quantity or Decimal('0'))
                else:
                    try:
                        fabrics[item.fabric] = Decimal(str(item.quantity)) * (item.fabric_quantity or Decimal('0'))
                    except TypeError:
                        fabrics[item.fabric] = Decimal('0')

            #Extract fabric from the pillows
            for pillow in item.pillows.all():
                if pillow.fabric:
                    if pillow.fabric in fabrics:

                        # There is no need to multiple by pillow quantity. The fabric quantity for the pillow already includes the fabric quantity
                        # for the total pillows of that particular type
                        try:
                            fabrics[pillow.fabric] += Decimal(str(item.quantity)) * pillow.fabric_quantity
                        except TypeError:
                            pass

                    else:
                        try:
                            fabrics[pillow.fabric] = Decimal(str(item.quantity)) * (pillow.fabric_quantity or Decimal('0'))
                        except TypeError:
                            fabrics[pillow.fabric] = Decimal('0')

        # Log Fabric Reservations
        for fabric in fabrics:
            self.reserve_fabric(fabric, fabrics[fabric], instance.id)

        # Create a calendar event
        try:
            instance.create_calendar_event(employee)
        except Exception as e:
            message = u"Unable to create calendar event for acknowledgement {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = AckLog.create(message=message, 
                                acknowledgement=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR")

        # Log Opening of an order
        message = u"Created Acknowledgement #{0}.".format(instance.id)
        log = AckLog.create(message=message, acknowledgement=instance, user=employee)

        if instance.vat > 0:
            try:
                pass #instance.create_in_trcloud() 
            except Exception as e:
                message = u"Unable to create acknowledgement because:\n{0}"
                message = message.format(e)
                log = AckLog.create(message=message, 
                                    acknowledgement=instance, 
                                    user=employee,
                                    type="TRCLOUD")
                
        return instance

    def update(self, instance, validated_data):

        # Get user 
        employee = self.context['request'].user
        if settings.DEBUG:
            employee = User.objects.get(pk=1)
        
        instance.current_user = employee
        dd = timezone('Asia/Bangkok').normalize(validated_data.pop('delivery_date', instance.delivery_date))
        instance.project = validated_data.pop('project', instance.project)
        instance.room = validated_data.pop('room', instance.room)
        status = validated_data.pop('status', instance.status)

        if instance.delivery_date != dd:
            old_dd = instance.delivery_date
            instance.delivery_date = dd
           
            # Log Changing delivery date
            message = u"Acknowledgement #{0} delivery date changed from {1} to {2}."
            message = message.format(instance.id, old_dd.strftime('%d/%m/%Y'), dd.strftime('%d/%m/%Y'))
            AckLog.create(message=message, acknowledgement=instance, user=employee)

        if status.lower() != instance.status.lower():

            message = u"Updated Acknowledgement #{0} from {1} to {2}."
            message = message.format(instance.id, instance.status.lower(), status.lower())
            AckLog.create(message=message, acknowledgement=instance, user=employee)

            instance.status = status

        old_qty = sum([item.quantity for item in instance.items.all()])
        
        # Extract items data
        items_data = validated_data.pop('items')
        items_data = self.initial_data['items']
        fabrics = {}

        #Update items individually
        for item_data in items_data:
            logger.debug(item_data)

            try:
                item_data['product'] = item_data['product'].id
            except AttributeError as e:
                
                pass
                
            except KeyError as e:
                pass

            item = Item.objects.get(pk=item_data['id'])
            serializer = ItemSerializer(item, data=item_data, context={'acknowledgement': instance,
                                                                       'employee': employee})

            if serializer.is_valid(raise_exception=True):
                serializer.save()

            # Update the fabric for this item if 'fabric' key exists
            try:
                item.fabric = item_data['fabric']
                item.save()
            except KeyError as e:
                logger.warn(e)

            # Loop and update pillows if 'pillows' key exists
            try:
                for pillow_data in item_data['pillows']:
                        # Retrieve or create new pillow if it does not exist
                        try:
                            pillow = item.pillows.get(type=pillow_data['type'], fabric=pillow_data['fabric'])
                        except Pillow.DoesNotExist:
                            pillow = Pillow(type=pillow_data['type'], fabric=pillow_data['fabric'], item=item)

                        # Set pillow attributes
                        pillow.fabric = pillow_data['fabric']
                        pillow.fabric_quantity = pillow_data['fabric_quantity']
                        pillow.quantity = pillow_data['quantity']

                        pillow.save()

            except KeyError:
                pass


            # Extract fabric quantities from items
            if item.fabric:

                if item.fabric in fabrics:
                    try:
                        fabrics[item.fabric] += Decimal(str(item.quantity)) * item.fabric_quantity
                    except TypeError:
                        fabrics[item.fabric] += 0

                else:
                    try:
                        fabrics[item.fabric] = Decimal(str(item.quantity)) * (item.fabric_quantity or Decimal('0'))
                    except TypeError:
                        fabrics[item.fabric] = Decimal('0')

                #Extract fabric from the pillows
                for pillow in item.pillows.all():
                    if pillow.fabric:
                        if pillow.fabric in fabrics:

                            # There is no need to multiple by pillow quantity. The fabric quantity for the pillow already includes the fabric quantity
                            # for the total pillows of that particular type
                            try:
                                fabrics[pillow.fabric] += Decimal(str(item.quantity)) * pillow.fabric_quantity
                            except TypeError:
                                pass

                        else:
                            try:
                                fabrics[pillow.fabric] = Decimal(str(item.quantity)) * (pillow.fabric_quantity or Decimal('0'))
                            except TypeError:
                                fabrics[pillow.fabric] = Decimal('0')

        # Log Fabric Reservations
        for fabric in fabrics:
            self.reserve_fabric(fabric, fabrics[fabric], instance.id)

        #Update attached files
        files = validated_data.pop('files', [])
        for file in files:
            try:
                File.objects.get(file_id=file['id'], acknowledgement=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                    acknowledgement=instance)

        #if instance.status.lower() in ['acknowledged', 'in production', 'ready to ship']:

        # Store old total and calculate new total
        old_total = instance.total
        instance.calculate_totals()

        try:
            instance.create_and_upload_pdfs()
        except IOError as e:

        
            tb = traceback.format_exc()
            logger.error(tb)
            
            message = u"Unable to update PDF for acknowledgement {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = AckLog.create(message=message, 
                                acknowledgement=instance, 
                                user=employee,
                                type="PDF CREATION ERROR")


        try:
            instance.update_calendar_event()
        except Exception as e:
            logger.debug(e)
            message = u"Unable to update calendar event for acknowledgement {0} because:\n{1}"
            message = message.format(instance.id, e)
            log = AckLog.create(message=message, 
                                acknowledgement=instance, 
                                user=employee,
                                type="GOOGLE CALENDAR ERROR")

        instance.save()

        if instance.vat > 0 and instance.trcloud_id:
            try:
                pass #instance.update_in_trcloud()
            except Exception as e:
                message = u"Unable to update acknowledgement {0} because:\n{1}"
                message = message.format(instance.id, e)
                log = AckLog.create(message=message, 
                                    acknowledgement=instance, 
                                    user=employee,
                                    type="TRCLOUD ERROR")
           
        return instance

    def to_representation(self, instance):
        """
        Override the default 'to_representation' method to customize the output data
        """
        ret = super(AcknowledgementSerializer, self).to_representation(instance)

        
        """
        # Retrieve and serialize logs for the acknowledgements
        def get_employee(log):
            try:
                return u"{0} {1}".format(log.employee.first_name, log.employee.last_name)
            except Exception as e:
                return "NA"

        try:
            ret['logs'] = [{'message': log.message,
                            'employee': get_employee(log),
                            'timestamp': log.timestamp} for log in instance.logs.all()]
        except Exception as e:
            logger.warn(e)
        """

        # Retrieve more acknowledgement data if the request is specific
        pk = self.context['view'].kwargs.get('pk', None)
        if pk or self.context['request'].method.lower() in ['post', 'put']:

            ret['items'] = ItemSerializer(instance.items.all(), many=True).data

            try:
                address = instance.customer.addresses.all()[0]
                ret['customer']['latitude'] = address.latitude
                ret['customer']['longitude'] = address.longitude
            except (IndexError, KeyError):
                pass

            ret['employee'] = {'id': instance.employee.id,
                               'name': u"{0} {1}".format(instance.employee.first_name, instance.employee.last_name)}



            

            try:
                iam_credentials = self.context['request'].user.aws_credentials
                key = iam_credentials.access_key_id
                secret = iam_credentials.secret_access_key
            except:
                key, secret = ('', '')

            try:
                ret['files'] = [{'id': file.id,
                                 'filename': file.key.split('/')[-1],
                                 'type': file.key.split('.')[-1],
                                 'url': file.generate_url(key, secret)} for file in instance.files.all()]
            except AttributeError:
                pass

        return ret

    def reserve_fabric(self, fabric, quantity, acknowledgement_id, employee=None):
        """
        Internal method to apply the new quantity to the obj and
        create or update a log of the quantity change
        """



        #Create log to track quantity changes
        try:
            log = Log.objects.get(acknowledgement_id=acknowledgement_id, supply_id=fabric.id)
        except Log.DoesNotExist:
            log = Log(supply=fabric, acknowledgement_id=acknowledgement_id)

        # Get log quantity for fabric cut later
        original_qty = log.quantity or 0

        # Set log attributes
        log.action = "RESERVE"
        log.quantity = quantity
        log.employee = employee
        log.message = u"Reserve {0}{1} of {2} for Ack#{3}".format(quantity,
                                                                  fabric.units,
                                                                  fabric.description,
                                                                  acknowledgement_id)

        # Save log
        log.save()


class AcknowledgementFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = Acknowledgement
        fields = ('company', 'id', 'remarks', 'fob', 'shipping_method', 'delivery_date', 'total', 'subtotal', 'time_created')