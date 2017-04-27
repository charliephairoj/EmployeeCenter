import logging
from decimal import Decimal

from rest_framework import serializers
from rest_framework.fields import DictField

from estimates.models import Estimate, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer
from products.serializers import ProductSerializer
from contacts.models import Customer
from products.models import Product
from supplies.models import Fabric, Log
from projects.models import Project
from media.models import S3Object


logger = logging.getLogger(__name__)


class PillowSerializer(serializers.ModelSerializer):
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())

    class Meta:
        model = Pillow
        field = ('type', 'fabric', 'quantity')
        exclude = ('item',)

    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the item pass via the context
        """
        item = self.context['item']

        instance = self.Meta.model.objects.create(item=item, **validated_data)

        return instance


class ItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(required=False, queryset=Product.objects.all())
    pillows = PillowSerializer(required=False, many=True)
    unit_price = serializers.DecimalField(required=False, decimal_places=2, max_digits=12)
    comments = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    location = serializers.CharField(required=False, allow_null=True)
    fabric = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Fabric.objects.all())
    image = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=S3Object.objects.all())
    units = serializers.CharField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(decimal_places=2, max_digits=12, default=1)
    custom_price = serializers.DecimalField(decimal_places=2, max_digits=12, write_only=True, required=False,
                                            allow_null=True)
    fabric_quantity = serializers.DecimalField(decimal_places=2, max_digits=12,
                                               write_only=True, required=False,
                                               allow_null=True)
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Item
        field = ('description', 'id', 'width', 'depth', 'height')
        read_only_fields = ('total', 'type')
        exclude = ('estimate', )

    def create(self, validated_data):
        """
        Populates the instance after the parent 'restore_object' method is
        called.
        """
        estimate = self.context['estimate']
        pillow_data = validated_data.pop('pillows', None)
        product = validated_data['product']
        unit_price = validated_data.pop('unit_price', validated_data.pop('price', product.price))
        width = validated_data.pop('width', product.width)
        depth = validated_data.pop('depth', product.depth)
        height = validated_data.pop('height', product.height)
        fabric_quantity = validated_data.pop('fabric_quantity', None)

        instance = self.Meta.model.objects.create(estimate=estimate, unit_price=unit_price,
                                                  width=width, depth=depth,
                                                  height=height, **validated_data)

        #attach fabric quantity
        instance.fabric_quantity = fabric_quantity

        #Calculate the total price of the item
        if instance.is_custom_size and product.price == unit_price:
            instance._calculate_custom_price()
        else:
            instance.total = instance.quantity * instance.unit_price

        instance.save()

        if pillow_data:
            pillow_serializer = PillowSerializer(data=pillow_data, context={'item': instance}, many=True)

            if pillow_serializer.is_valid(raise_exception=True):
                pillow_serializer.save()

        return instance

    def update(self, instance, validated_data):
        """
        Updates the instance after the parent method is called
        """
        instance = super(ItemSerializer, self).update(instance, validated_data)

        #instance.image = validated_data.get('image', instance.image)
        instance.save()

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

        try:
            ret['image'] = {'url': instance.image.generate_url()}
        except AttributeError:
            pass

        return ret

"""
class FileSerializer(serializers.ModelSerializer):

    class Meta:
        model = File
        read_only_fields = ('acknowledgement', 'file')
"""

class EstimateSerializer(serializers.ModelSerializer):
    company = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    employee = serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    project = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Project.objects.all())
    items = ItemSerializer(many=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    po_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    shipping_method = serializers.CharField(required=False, allow_null=True)
    fob = serializers.CharField(required=False, allow_null=True)
    #vat = serializers.DecimalField(required=False, allow_null=True)
    discount = serializers.IntegerField(required=False, allow_null=True)
    #files = serializers.ListField(child=serializers.DictField(), write_only=True, required=False,
    #                              allow_null=True)

    class Meta:
        model = Estimate
        read_only_fields = ('total', 'subtotal', 'time_created')
        exclude = ('pdf',)


    def create(self, validated_data):
        """
        Override the 'create' method in order to create nested items
        """
        items_data = validated_data.pop('items')
        #files = validated_data.pop('files', [])

        for item_data in items_data:
            for field in ['product', 'fabric', 'image']:
                try:
                    item_data[field] = item_data[field].id
                except KeyError:
                    pass
                except AttributeError:
                    pass
                
        logger.debug(validated_data)
        
        customer_discount = validated_data['customer'].discount
        discount = validated_data.pop('discount', customer_discount)
       

        instance = self.Meta.model.objects.create(employee=self.context['request'].user, discount=discount,
                                                    **validated_data)
        instance.status = "open"

        item_serializer = ItemSerializer(data=items_data, context={'estimate': instance}, many=True)

        if item_serializer.is_valid(raise_exception=True):
            item_serializer.save()
        logger.debug(instance.discount)
        instance.calculate_totals()

        instance.create_and_upload_pdf()
     
        #Assign files
        #for file in files:
        #    File.objects.create(file=S3Object.objects.get(pk=file['id']),
        #                        acknowledgement=instance)

        """
        #Extract fabric quantities
        fabrics = {}

        for item in item_serializer.instance:
            if item.fabric:
                if item.fabric in fabrics:
                    fabrics[item.fabric] += Decimal(str(item.quantity)) * item.fabric_quantity
                else:
                    fabrics[item.fabric] = Decimal(str(item.quantity)) * item.fabric_quantity

        #Log Fabric Reservations
        for fabric in fabrics:
            self.reserve_fabric(fabric, fabrics[fabric], instance.id)
        """

        return instance

    def update(self, instance, validated_data):

        instance.vat = validated_data.pop('vat', instance.vat)
        instance.discount = validated_data.pop('discount', instance.discount)
        instance.delivery_date = validated_data.pop('delivery_date', instance.delivery_date)
        instance.project = validated_data.pop('project', instance.project)
        #Update attached files
        #files = validated_data.pop('files', [])
        #for file in files:
        #    try:
        #        File.objects.get(file_id=file['id'], acknowledgement=instance)
        #    except File.DoesNotExist:
        #        File.objects.create(file=S3Object.objects.get(pk=file['id']),
        #                            acknowledgement=instance)

        instance.status = validated_data.pop('status', instance.status)

        items_data = validated_data.pop('items')

        self._update_items(instance, items_data)

        instance.save()

        instance.calculate_totals()

        instance.create_and_upload_pdf()

        instance.save()

        return instance

    def to_representation(self, instance):
        """
        Override the default 'to_representation' method to customize the output data
        """
        ret = super(EstimateSerializer, self).to_representation(instance)

        ret['customer'] = {'id': instance.customer.id,
                           'name': instance.customer.name}

        ret['employee'] = {'id': instance.employee.id,
                           'name': "{0} {1}".format(instance.employee.first_name, instance.employee.last_name)}

        try:
            ret['project'] = {'id': instance.project.id,
                              'codename': instance.project.codename}
        except AttributeError:
            pass

        ret['files'] = []

        try:
            ret['files'] = [{'id': instance.id,
                             'filename': instance.pdf.key.split('/')[-1],
                             'url': instance.pdf.generate_url()}]
        except AttributeError as e:
            logger.warn(e)

        try:
            ret['files'] += [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url()} for file in instance.files.all()]
        except AttributeError as e:
            logger.warn(e)

        return ret

    def _update_items(self, instance, items_data):
        """
        Handles creation, update, and deletion of items
        """
        #Maps of id
        id_list = [item_data.get('id', None) for item_data in items_data]

        #Update or Create Item
        for item_data in items_data:

            try:
                item = Item.objects.get(pk=item_data['id'], estimate=instance)
            except KeyError as e:
                try:
                    item = Item(product=Product.objects.get(pk=item_data['product']))
                except TypeError as e:
                    item = Item(product=item_data['product'])
                
                
            item.estimate = instance
            item.width = item_data.get('width', item.width)
            item.depth = item_data.get('depth', item.depth)
            item.height = item_data.get('height', item.height)
            item.description = item_data.get('description', item.description)
            item.quantity = item_data.get('quantity', item.quantity)
            item.unit_price = item_data.get('unit_price', item.unit_price)
            item.total = item.quantity * item.unit_price

            try:
                item.image = S3Object.objects.get(pk=item_data['image'])
            except TypeError as e:
                item.image = item_data['image']
            except (S3Object.DoesNotExist, KeyError) as e:
                logger.warn(item_data['image'])
                logger.warn(e)
                
            item.save()
                
            """
            try:

                item = Item.objects.get(pk=item_data['id'])
                serializer = ItemSerializer(item, context={'customer': instance.customer, 'estimate': instance}, data=item_data)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()

                
                item.supply.supplier = instance.supplier
                item.discount = item_data.get('discount', None) or item.discount
                item.quantity = item_data.get('quantity', None) or item.quantity
                item.unit_cost = item_data.get('unit_cost', None) or item.unit_cost

                #Change the cost of the supply and log price change
                if item.unit_cost != item.supply.cost:
                    self._change_supply_cost(item.supply, item.unit_cost)

                item.calculate_total()
                item.save()
                
            except KeyError:
                item_data['product'] = item_data['product'].id
                serializer = ItemSerializer(data=item_data, context={'customer': instance.customer, 'estimate': instance})
                if serializer.is_valid(raise_exception=True):
                    item = serializer.save()
                    id_list.append(item.id)
            """
            
        #Delete Items
        for item in instance.items.all():
            if item.id not in id_list:
                item.delete()
