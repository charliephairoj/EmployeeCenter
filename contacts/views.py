from contacts.models import Customer, Supplier
from rest_framework import viewsets
from contacts.serializers import CustomerSerializer, SupplierSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    def pre_save(self, instance):
        instance.is_customer = True
        return instance
    
    
class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    
    def pre_save(self, instance):
        instance.is_supplier = True
        return instance