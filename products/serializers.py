from rest_framework import serializers

from products.models import Configuration, Model, Upholstery, Pillow, Table
from contacts.serializers import CustomerSerializer


class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        field = ('id', 'configuration')
        
        
class ModelSerializer(serializers.ModelSerializers):
    class Meta:
        model = Model
        field = ('id', 'name', 'model')
        
        
class UpholsterySerializer(serializers.ModelSerializers):
    model = ModelSerializer()
    configuration = ConfigurationSerializer()
    pillows = PillowSerializer()
    
    class Meta:
        model = Upholstery
        
        
class PillowSerializer(serializers.ModelSerializers):
    class Meta:
        model = Pillow
        
        
class Table(serializers.ModelSerializers):
    model = ModelSerializer()
    configuration = ConfigurationSerializer()
    
    class Meta:
        model = Table
        