from rest_framework import viewsets

from products.models import Upholstery, Table, Model, Configuration
from products.serializers import UpholsterySerializer, TableSerializer, ModelSerializer, ConfigurationSerializer


class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit configurations
    """
    queryset = Configuration.objects.all()
    serializer = ConfigurationSerializer()
    

class ModelViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit models
    """
    queryset = Model.objects.all()
    serializer = ModelSerializer()
    
    
class UpholsteryViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit upholstery
    """
    queryset = Upholstery.objects.all()
    serializer = UpholsterySerializer()
    
    
class TableSerializer(viewsets.ModelViewSet):
    """
    API endpoint to view and edit table
    """
    queryset = Table.objects.all()
    serializer = TableSerializer()