from django.db.models import Q
from rest_framework import viewsets

from contacts.models import Customer, Supplier
from contacts.serializers import CustomerSerializer, SupplierSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Customer.objects.all().order_by('name')
    serializer_class = CustomerSerializer
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))
                                      
        return queryset
    
    
class SupplierViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))
                                      
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        if self.request.query_params.get('limit', None) == 0:
            return 1000
            
        return 20
        
        
        
        
        
        
        
        
        
        
        