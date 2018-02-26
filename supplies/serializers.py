from decimal import Decimal
from datetime import datetime
import logging

from rest_framework import serializers

from contacts.models import Supplier
from supplies.models import Supply, Product, Fabric, Log
from hr.models import Employee
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
        logger.debug(validated_data)

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
            product_mapping[product.supplier.id] = product

        data_mapping = {}
        for item in validated_data:
            try:
                logger.debug(item)
                data_mapping[int(item['supplier'].id)] = item
            except KeyError as e:
                pass

        # Perform creations and updates.
        ret = []
        for product_id, data in data_mapping.items():
            product = product_mapping.get(product_id, None)
            if product is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(product, data))

        # Perform deletions.
        """
        for product_id, product in product_mapping.items():
            if product_id not in data_mapping:
                product.delete()
        """

        return ret


class ProductSerializer(serializers.ModelSerializer):
    upc = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    id = serializers.CharField(write_only=True, required=False)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    purchasing_units = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    quantity_per_purchasing_unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cost = serializers.DecimalField(decimal_places=4, max_digits=16, required=False)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), required=False)
    class Meta:
        model = Product
        read_only_fields = ['supply']
        list_serializer_class = ProductListSerializer
        fields = '__all__'

    def create(self, validated_data):
        """
        Override the 'create' method in order to assign the supply passed via context
        """
        logger.debug(validated_data)
        supply = self.context['supply']

        instance = self.Meta.model.objects.create(supply=supply, **validated_data)
        instance.supplier = validated_data['supplier']
        instance.save()
        
        return instance


class SupplyListSerializer(serializers.ListSerializer):

    def update(self, instance, validated_data):
        """
        Update multiple supplies

        Currently can only update the quantity
        """
        ret = []
        #Update the quantity for each supply
        for data in validated_data:
            supply = Supply.objects.get(pk=data['id'])

            self.child.update(supply, data)

            ret.append(supply)

        return ret


class SupplySerializer(serializers.ModelSerializer):
    quantity = serializers.DecimalField(decimal_places=2, max_digits=12, required=False)
    description_th = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    suppliers = ProductSerializer(source="products", required=False, many=True, write_only=True)
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), write_only=True, required=False, allow_null=True)
    id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Supply
        list_serializer_class = SupplyListSerializer
        #read_only_fields = ['suppliers']
        exclude = ['quantity_th', 'quantity_kh', 'shelf']

    def to_representation(self, instance):
        """
        Override the 'to_representation' method to allow integration of products into
        output data
        """
        ret = super(SupplySerializer, self).to_representation(instance)

        try:
            iam_credentials = self.context['request'].user.aws_credentials
            key = iam_credentials.access_key_id
            secret = iam_credentials.secret_access_key
        except AttributeError as e:
            logger.warn(e)

        view = self.context['view']
        if view.kwargs.get('pk', None) or self.context['request'].method.lower() in ['put', 'post']:
            ret['suppliers'] = [{'id': product.id,
                                 'supplier': {'id': product.supplier.id,
                                              'name': product.supplier.name},
                                 'cost': product.cost,
                                 'reference': product.reference,
                                 'purchasing_units': product.purchasing_units,
                                 'quantity_per_purchasing_unit': product.quantity_per_purchasing_unit,
                                 'upc': product.upc} for product in instance.products.all()]

            #Add sticker url or create stickers if they do not exists
            """
            try:
                ret['sticker'] = {'id': instance.sticker.id,
                                  'url': instance.sticker.generate_url(key, secret)}
            except AttributeError:
                instance.create_stickers(key, secret)
                ret['sticker'] = {'id': instance.sticker.id,
                                  'url': instance.sticker.generate_url(key, secret)}
            """

        # Apply data attributes from the product associate between the supply and supplier if it exists
        try:
            if 'supplier_id' in self.context['request'].query_params:
                instance.supplier = Supplier.objects.get(pk=self.context['request'].query_params['supplier_id'])

                ret['unit_cost'] = instance.cost
                ret['cost'] = instance.cost
                ret['reference'] = instance.reference

        except (KeyError, ValueError) as e:
            logger.debug(e)

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
        elif 'products' in validated_data:
            suppliers_data = validated_data.pop('products')
        else:

            data = {}
            for field in ['cost', 'reference', 'purchasing_units', 'quantity_per_purchasing_units', 'upc']:
                try:
                    logger.debug(field)
                    logger.debug(self.context['request'])
                    data[field] = self.context['request'].data[field]
                except KeyError:
                    pass
                except TypeError:
                    try:
                        data[field] = self.context['request'].data[self.context['index']][field]
                    except KeyError:
                        pass

            try:
                data['supplier'] = self.context['request'].data['supplier']
            except KeyError:
                try:
                    data['supplier'] = self.context['request'].data['suppliers'][0]
                except KeyError as e:
                    logger.warn(e)
            except TypeError as e:
                try:
                    data['supplier'] = self.context['request'].data[self.context['index']]['supplier']
                except KeyError:
                    try:
                        data['supplier'] = self.context['request'].data[self.context['index']]['suppliers'][0]
                    except KeyError:
                        pass

            suppliers_data = [data]
        logger.debug(suppliers_data)
        #iam_credentials = self.context['request'].user.aws_credentials
        #key = iam_credentials.access_key_id
        #secret = iam_credentials.secret_access_key
        logger.debug(validated_data)
        instance = self.Meta.model.objects.create(**validated_data)
        #instance.create_stickers(key, secret)
        logger.debug(instance.__dict__)
        product_serializer = ProductSerializer(data=suppliers_data, context={'supply': instance}, many=True)
        if product_serializer.is_valid(raise_exception=True):
            product_serializer.save()

        return instance

    def update(self, instance, validated_data):
        """
        Override the 'update' method in order to customize create, update and delete of products
        """
        logger.debug(validated_data)
        try:
            products_data = validated_data.pop('suppliers')
        except KeyError:
            products_data = validated_data.pop('products', None)

        old_quantity = instance.quantity
        new_quantity = validated_data['quantity']
        employee = validated_data.pop('employee', None)

        for field in validated_data.keys():
            setattr(instance, field, validated_data[field])

        if products_data:
            product_serializer = ProductSerializer(data=products_data, context={'supply': instance}, many=True)
            if product_serializer.is_valid(raise_exception=True):
                product_serializer.save()

        instance.save()

        assert instance.quantity == new_quantity
        self._log_quantity(instance, old_quantity, new_quantity, employee)
        assert instance.quantity == new_quantity

        return instance

    def _log_quantity(self, obj, old_quantity, new_quantity, employee=None):
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


class FabricSerializer(SupplySerializer):
    content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    grade = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    handling = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    repeat = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    suppliers = ProductSerializer(source="products", required=False, many=True, write_only=True)

    class Meta:
        model = Fabric
        write_only_fields = ('suppliers', )
        fields = '__all__'

    def create(self, validated_data):
        """
        Override the 'create' method in order to customize creation of products
        """
        if 'supplier' in validated_data:
            suppliers_data = [validated_data.pop('supplier')]
        elif 'suppliers' in validated_data:
            suppliers_data = validated_data.pop('suppliers')
        elif 'products' in validated_data:
            suppliers_data = validated_data.pop('products')
        else:

            data = {}
            for field in ['cost', 'reference', 'purchasing_units', 'quantity_per_purchasing_units', 'upc']:
                try:
                    data[field] = self.context['request'].data[field]
                except KeyError:
                    pass

            try:
                data['supplier'] = self.context['request'].data['supplier']
            except KeyError:
                data['supplier'] = self.context['request'].data['suppliers'][0]

            suppliers_data = [data]


        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key

        instance = self.Meta.model.objects.create(**validated_data)
        instance.description = u"{0} Col: {1}".format(instance.pattern, instance.color)
        instance.create_stickers(key, secret)

        # Set the purchasing units to the same as units for this fabric
        suppliers_data[0]['purchasing_units'] = instance.units

        product_serializer = ProductSerializer(data=suppliers_data, context={'supply': instance}, many=True)
        if product_serializer.is_valid(raise_exception=True):
            product_serializer.save()

        return instance

    def to_representation(self, instance):
        ret = super(FabricSerializer, self).to_representation(instance)

        ret['reserved'] = sum([log.quantity or 0 for log in instance.reserved_fabric_logs])

        return ret


class LogSerializer(serializers.ModelSerializer):
    supply = SupplySerializer(required=False, allow_null=True)

    class Meta:
        model = Log
        fields = '__all__'

    def update(self, instance, validated_data):

        quantity = Decimal(str(validated_data.pop('quantity', instance.quantity)))
        action = validated_data.pop('action', instance.action)

        #Determine if should update or not
        if action.lower() == 'cut':
            old_qty = instance.supply.quantity
            try:
                instance.supply.quantity -= quantity
            except TypeError:
                instance.supply.quantity -= float(quantity)

            assert instance.supply.quantity != old_qty, "The quantities are wrong: {0} : {1} : {2}".format(instance.supply.quantity, old_qty, quantity)

            instance.supply.save()

            #Adjust log
            instance.action = "SUBTRACT"
            instance.quantity = quantity
            instance.timestamp = datetime.now()
            instance.message = "{0}{1} of {2} cut for Ack #{3}".format(instance.quantity,
                                                                       instance.supply.units,
                                                                       instance.supply.description,
                                                                       instance.acknowledgement_id)
            instance.save()

        elif action.lower() == 'cancel':

            instance.supply.save()

            instance.timestamp = datetime.now()
            instance.action = "CANCELLED"
            instance.message = "Cancelled reservation of {0} for Ack #{1}".format(instance.supply.description,
                                                                                  instance.acknowledgement_id)
            instance.save()

        return instance
