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


class PillowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pillow
        

class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        
                
class UpholsterySerializer(serializers.ModelSerializer):
    model = ModelSerializer()
    configuration = ConfigurationSerializer()
    pillows = PillowSerializer()
    
    class Meta:
        model = Upholstery
        
        
class TableSerializer(serializers.ModelSerializer):
    model = ModelSerializer()
    configuration = ConfigurationSerializer()
    
    class Meta:
        model = Table
        