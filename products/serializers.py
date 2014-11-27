from rest_framework import serializers

from products.models import Product, Configuration, Model, Upholstery, Pillow, Table
from contacts.serializers import CustomerSerializer


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
        

class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        
                
class UpholsterySerializer(serializers.ModelSerializer):
    model = serializers.PrimaryKeyRelatedField()
    configuration = serializers.PrimaryKeyRelatedField()
    pillows = PillowSerializer(required=False)
    image = serializers.PrimaryKeyRelatedField(required=False)

    class Meta:
        model = Upholstery
        read_only_fields = ('description', 'type')
        exclude = ('image_key', 'bucket', 'schematic', 'schematic_key', 'image_url')
        
    def restore_object(self, attrs, instance):
        
        instance = super(UpholsterySerializer, self).restore_object(attrs, instance)
        
        instance.description = "{0} {1}".format(instance.model.model, 
                                                instance.configuration.configuration)
                                                
        return instance
        
    def transform_model(self, obj, value):
        return {'id': obj.model.id,
                'model': obj.model.model,
                'name': obj.model.name}        
                
    def transform_configuration(self, obj, value):
        return {'id': obj.configuration.id,
                'configuration': obj.configuration.configuration}
        
        
class TableSerializer(serializers.ModelSerializer):
    model = serializers.PrimaryKeyRelatedField(required=False)
    configuration = serializers.PrimaryKeyRelatedField(required=False)
    
    class Meta:
        model = Table
        read_only_fields = ('description', 'type', 'color')
        exclude = ('image_key', 'bucket', 'schematic', 'schematic_key', 'image_url')
        
    def restore_object(self, attrs, instance):
        
        instance = super(TableSerializer, self).restore_object(attrs, instance)
        
        instance.description = "{0} {1}".format(instance.model.model, 
                                                instance.configuration.configuration)
                                                
        return instance
        
    def transform_model(self, obj, value):
        return {'id': obj.model.id,
                'model': obj.model.model,
                'name': obj.model.name}        
                
    def transform_configuration(self, obj, value):
        return {'id': obj.configuration.id,
                'configuratio': obj.configuration.configuration}    
    
        
        
        