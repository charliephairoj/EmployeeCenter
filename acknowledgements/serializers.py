from rest_framework import serializers

from acknowledgements.models import Acknowledgement, Item, Pillow
from contacts.serializers import CustomerSerializer
from supplies.serializers import FabricSerializer


class PillowSerializer(serializers.ModelSerializer):
    fabric = FabricSerializer()
    
    class Meta:
        model = Pillow
        field = ('type', 'quantity', 'fabric')
        
        
class ItemSerializer(serializers.ModelSerializer):
    pillows = PillowSerializer()
    
    class Meta:
        model = Item
        field = ('description')
        
        
class AcknowledgementSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    user = serializers.RelatedField()
    project = serializers.RelatedField(required=False)
    acknowledgement_pdf = serializers.RelatedField(required=False)
    production_pdf = serializers.RelatedField(required=False)
    original_acknowledgement_pdf = serializers.RelatedField(required=False)
    label_pdf = serializers.RelatedField(required=False)
    items = ItemSerializer(read_only=True)
    remarks = serializers.CharField(required=False)
    shipping_method = serializers.CharField(required=False)
    fob = serializers.CharField(required=False)
    
    class Meta:
        model = Acknowledgement
        field = ('id', 'discount', 'time_created', 'delivery_date', 'status', 'remarks', 'subtotal',
                 'vat', 'total')
                 


    