from rest_framework import serializers

from shipping.models import Shipping, Item
from acknowledgements.models import Acknowledgement
from contacts.serializers import CustomerSerializer


class ItemSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    comments = serializers.CharField(required=False)
    
    class Meta:
        model = Item
        read_only_fields = ('shipping',)
    
class ShippingSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True)
    customer = CustomerSerializer()
    acknowledgement = serializers.PrimaryKeyRelatedField(queryset=Acknowledgement.objects.all())
    comments = serializers.CharField(required=False)
    
    class Meta:
        model = Shipping
        read_only_fields = ('employee', 'pdf')
        
    def transform_customer(self, obj, value):
        return {'id': obj.customer.id,
                'name': obj.customer.name}
                
    def transform_pdf(self, obj, value):
        try:
            return {'url': obj.pdf.generate_url()}
        except AttributeError:
            return None


    
