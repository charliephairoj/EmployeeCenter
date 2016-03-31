import logging

from rest_framework import serializers

from products.models import Product, Configuration, Model, Upholstery, Pillow, Table, Image, Supply as ProductSupply
from supplies.models import Supply
from media.models import S3Object
from contacts.serializers import CustomerSerializer


logger = logging.getLogger(__name__)


class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        field = ('id', 'configuration')

        
class ModelSerializer(serializers.ModelSerializer):
    images = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    class Meta:
        model = Model
        field = ('id', 'model', 'images', 'has_back_pillows', 'frame', 'upholstery', 'suspension', 'cushion', 'legs')
        exclude = ('image_url', 'bucket', 'image_key')
        
    def create(self, validated_data):
        images = validated_data.pop('images', [])
        image = validated_data.pop('image', None)
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        for image_data in images:
            try:
                image = Image.objects.get(id=image_data['id'])
            except Image.DoesNotExist:
                image = Image.objects.create(id=image_data['id'])
            image.model = instance
            image.save()
             
        return instance
        
    def update(self, instance, validated_data):
        
        images = validated_data.pop('images', [])
        image = validated_data.pop('image', None)
        
        instance = super(ModelSerializer, self).update(instance, validated_data)
        
        for image_data in images:
            # Retrieve or create if it does not exist
            try:
                image = Image.objects.get(id=image_data['id'])
                
                if not image.key:
                    obj = S3Object.objects.get(pk=image_data['id'])
                    image.key = obj.key
                    image.id = obj.id
                    image.bucket = obj.bucket
            except Image.DoesNotExist:
                obj = S3Object.objects.get(pk=image_data['id'])
                image = Image()
                image.key = obj.key
                image.id = obj.id
                image.bucket = obj.bucket
                
            assert image.key
            assert image.bucket
            
            # Update the image
            image.model = instance
            image.primary = image_data.pop('primary', False)
            image.web_active = image_data.pop('web_active', False)
            image.configuration = image_data.pop('configuration', False)
            
            assert image.key
            assert image.bucket
            
            image.save()
            
        return instance
        
    def to_representation(self, instance):
        
        ret = super(ModelSerializer, self).to_representation(instance)
        
        iam_credentials = self.context['request'].user.aws_credentials
        key = None #iam_credentials.access_key_id
        secret = None #iam_credentials.secret_access_key
        
        try:
            ret['images'] = [{'id': image.id,
                              'url': image.generate_url(key, secret),
                              'key': image.key,
                              'bucket': image.bucket,
                              'primary': image.primary,
                              'web_active': image.web_active,
                              'configuration': image.configuration} for image in instance.images.all().order_by('-primary')]
        except (AttributeError, IndexError):
            pass
            
        return ret
        

class PillowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pillow
        field = ('id', 'type', 'quantity')
        

class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        
                
class UpholsterySerializer(serializers.ModelSerializer):
    model = serializers.PrimaryKeyRelatedField(queryset=Model.objects.all())
    configuration = serializers.PrimaryKeyRelatedField(queryset=Configuration.objects.all())
    pillows = PillowSerializer(required=False, many=True, write_only=True)
    image = serializers.PrimaryKeyRelatedField(required=False, queryset=S3Object.objects.all(),
                                               allow_null=True)
    collection = serializers.CharField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    depth = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)
    
    class Meta:
        model = Upholstery
        read_only_fields = ('description', 'type')
        exclude = ('image_key', 'bucket', 'schematic', 'schematic_key', 'image_url')
    
    def to_representation(self, instance):
        """
        Override the 'to_representation' method'
        
        "Will call parent method and then change some of the data"
        """
        ret = super(UpholsterySerializer, self).to_representation(instance)
        
        ret['model'] = {'id': instance.model.id,
                        'model': instance.model.model,
                        'name': instance.model.name}
                        
        ret['configuration'] = {'id': instance.configuration.id,
                                'configuration': instance.configuration.configuration}
                       
        ret['pillows'] = [{'id': pillow.id,
                           'type': pillow.type,
                           'quantity': pillow.quantity} for pillow in instance.pillows.all()]
                         
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
               
        try:
            ret['image'] = {'id': instance.image.id,
                            'url': instance.image.generate_url(key, secret)}
        except AttributeError:
            pass
        
        
        try:
            ret['prices'] = [{'grade': price.grade, 'price':price.price} for price in instance.prices.all()]
        except AttributeError:
            pass
             
        return ret
            
    def create(self, validated_data):
        """
        Implement the 'create' method
        
        Sets the description by combining the model number and configuration.
        Also sets the configuration and model for the product
        """
        model = validated_data.pop('model')
        
        config = validated_data.pop('configuration')
        
        try:    
            image_data = validated_data.pop('image')
            image = S3Object.objects.get(pk=image_data['id'])
        except (KeyError, S3Object.DoesNotExist):
            image = None
            
        instance = Upholstery.objects.create(description="{0} {1}".format(model.model, config.configuration),
                                             model=model, configuration=config, image=image, **validated_data)
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Implemenet the 'update' method
        
        removes the configuration and model data, and then updates the instance
        """
        del validated_data['model']
        del validated_data['configuration']
        
        try:
            for p_data in validated_data['pillows']:
                try:
                    pillow = Pillow.objects.get(product=instance, type=p_data['type'].lower())
                except Pillow.DoesNotExist as e:
                    pillow = Pillow.objects.create(product=instance, type=p_data['type'].lower())
                pillow.quantity = p_data['quantity']
                if pillow.quantity == 0:
                    pillow.delete()
                else:    
                    pillow.save()
        except KeyError:
            pass
            
        for field_name in validated_data.keys():
            setattr(instance, field_name, validated_data[field_name])
            
        instance.save()
        
        return instance
        
        
class TableSerializer(serializers.ModelSerializer):
    model = serializers.PrimaryKeyRelatedField(queryset=Model.objects.all())
    configuration = serializers.PrimaryKeyRelatedField(queryset=Configuration.objects.all())
    collection = serializers.CharField(required=False, allow_null=True)
    units = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Table
        read_only_fields = ('description', 'type', 'color', 'finish')
        exclude = ('image_key', 'bucket', 'schematic', 'schematic_key', 'image_url', 'export_price')
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method'
        
        "Will call parent method and then change some of the data"
        """
        ret = super(TableSerializer, self).to_representation(instance)
        
        ret['model'] = {'id': instance.model.id,
                        'model': instance.model.model,
                        'name': instance.model.name}
                        
        ret['configuration'] = {'id': instance.configuration.id,
                                'configuration': instance.configuration.configuration}
              
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            ret['image'] = {'url': instance.image.generate_url(key, secret)}
        except AttributeError:
            pass
            
        return ret
        
    def create(self, validated_data):
        """
        Implement the 'create' method
        
        Sets the description by combining the model number and configuration.
        Also sets the configuration and model for the product
        """
        model = validated_data.pop('model')
        
        config = validated_data.pop('configuration')
        
        try:    
            image_data = validated_data.pop('image')
            image = S3Object.objects.get(pk=image_data['id'])
        except (KeyError, S3Object.DoesNotExist):
            image = None
            
        instance = Table.objects.create(description="{0} {1}".format(model.model, config.configuration),
                                             model=model, configuration=config, image=image, **validated_data)
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Implemenet the 'update' method
        
        removes the configuration and model data, and then updates the instance
        """
        del validated_data['model']
        del validated_data['configuration']
        
        for field_name in validated_data.keys():
            setattr(instance, field_name, validated_data[field_name])
            
        return instance
        

class ProductSupplySerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    supply = serializers.PrimaryKeyRelatedField(queryset=Supply.objects.all(), allow_null=True, required=False)
    
    class Meta:
        model = ProductSupply
        field = ('id', 'description', 'cost', 'quantity')

    def to_representation(self, instance):
        """
        Override the 'to_representation' method'
        
        "Will call parent method and then change some of the data"
        """
        ret = super(ProductSupplySerializer, self).to_representation(instance)
        
        try:
            ret['supply'] = {'id': instance.supply.id,
                             'description': instance.supply.description,
                             'cost': instance.supply.products.all()[0].cost}
                             
        except AttributeError:
            pass
            
        return ret
    
        
        