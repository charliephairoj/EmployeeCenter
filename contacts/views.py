import logging
import time

from django.db.models import Q, Count, Value, Subquery, IntegerField, OuterRef
from django.db.models.functions import Coalesce

from django.conf import settings
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import authentication, permissions

from contacts.models import Customer, Supplier
from contacts.serializers import CustomerSerializer, SupplierSerializer
from acknowledgements.models import Acknowledgement as A


logger = logging.getLogger(__name__)


def sync_customers(request):
    
    service = Customer.get_google_contacts_service(request.user)
    query = gdata.contacts.client.ContactsQuery()
    query.max_results = 10000
    feed = gd_client.GetContacts(q = query)
    print len(feed.entry)
    
class CustomerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    authentication_classes = (authentication.SessionAuthentication,)

    def filter_queryset(self, queryset):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = queryset.annotate(num_open_orders=Count('acknowledgement')) \
                           .order_by('-num_open_orders')

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))

        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        elif not offset and limit:
            queryset = queryset[:limit]
            
        queryset = queryset.prefetch_related('addresses', 'contacts', 'acknowledgements')

        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit    


class CustomerMixin(object):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(CustomerMixin, self).handle_exception(exc)
    
    
class CustomerList(CustomerMixin, generics.ListCreateAPIView):
        

    def filter_queryset(self, queryset):
        """
        Override 'get_queryset' method in order to customize filter
        """
        
        acks_count = A.objects.filter(customer=OuterRef('pk'),
                                time_created__year=2018) \
                              .exclude(status__in=[u'cancelled', u'paid', u'invoiced']) \
                              .values('customer') \
                              .annotate(num_acks=Count('*')) \
                              .values('num_acks')

        prepped_fn = Coalesce(
            Subquery(acks_count, 
                     output_field=IntegerField()
            ), 
            Value('0')
        )


        queryset = queryset.annotate(num_open_orders=prepped_fn) \
                           .order_by('-num_open_orders')

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        elif not offset and limit:
            queryset = queryset[:limit]
        else:
            queryset = queryset[0:50]
            
        queryset = queryset.prefetch_related('addresses', 'contacts', 'acknowledgements')

        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            

class CustomerDetail(CustomerMixin, generics.RetrieveUpdateDestroyAPIView):
    pass


class SupplierMixin(object):
    queryset = Supplier.objects.all().order_by('-last_modified')
    serializer_class = SupplierSerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(SupplierMixin, self).handle_exception(exc)
    
    
class SupplierList(SupplierMixin, generics.ListCreateAPIView):
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()

        queryset = queryset.order_by('name')
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]

        queryset = queryset.prefetch_related('addresses', 'contacts')

        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            

class SupplierDetail(SupplierMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
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
        queryset = self.queryset.all()
        
        queryset = queryset.order_by('name')

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(email__icontains=query) |
                                       Q(telephone__icontains=query) |
                                       Q(notes__icontains=query))
        
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
                                      
        queryset = queryset.prefetch_related('addresses', 'contacts')
                                      
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        if self.request.query_params.get('limit', None) == 0:
            return 1000
        else:
            return int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
                    
        
        
        
        
        
        
        
        
        
        