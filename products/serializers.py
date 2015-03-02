import logging

from rest_framework import serializers

from products.models import Product, Configuration, Model, Upholstery, Pillow, Table
from media.models import S3Object
from contacts.serializers import CustomerSerializer


logger = logging.getLogger(__name__)


class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        field = ('id', 'configuration')

        
class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        field = ('id', 'name', 'model')
        exclude = ('image_url', 'bucket', 'image_key')


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
    pillows = PillowSerializer(required=False, many=True)
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
                                
        try:
            ret['image'] = {'id': instance.id,
                            'url': instance.image.generate_url()}
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
              
        try:
            ret['image'] = {'url': instance.image.generate_url()}
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
    
        
        