import logging
import time
from datetime import datetime, timedelta
from pytz import timezone

from django.db.models import Q, Count, Value, Subquery, IntegerField, OuterRef, Prefetch
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.renderers import JSONRenderer

from contacts.models import Customer, Supplier
from contacts.serializers import CustomerSerializer, SupplierSerializer
from acknowledgements.models import Acknowledgement as A
from estimates.models import Estimate as Quotation
from po.models import PurchaseOrder as PO
from utilities.http import save_upload
from media.models import S3Object
from media.serializers import S3ObjectSerializer


logger = logging.getLogger(__name__)


def sync_customers(request):
    
    service = Customer.get_google_contacts_service(request.user)
    query = gdata.contacts.client.ContactsQuery()
    query.max_results = 10000
    feed = gd_client.GetContacts(q = query)
    print len(feed.entry)


@login_required
def customer_file(request, customer_id=None):

    if request.method.lower() == "post":

        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''

        filename = save_upload(request)

        if customer_id:
            key = u"customer/{0}/files/{1}".format(customer_id, filename.split('/')[-1])
        else: 
            key = u"customer/files/{0}".format(filename.split('/')[-1])
        
        obj = S3Object.create(filename,
                            key,
                            u"document.dellarobbiathailand.com",
                            key, 
                            secret)
        
        serializer = S3ObjectSerializer(obj)
        response = HttpResponse(JSONRenderer().render(serializer.data),
                                content_type="application/json")
                                
        response.status_code = 201
        return response

    # If any method other than POST
    else:
        response = HttpResponse('{"message": "Not Allowed"}', content_type='application/json; charset=utf-8')
        response.status_code = 405 
        return response


@login_required
def supplier_file(request, supplier_id=None):

    if request.method.lower() == "post":

        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''

        filename = save_upload(request)

        if supplier_id:
            key = u"supplier/{0}/files/{1}".format(supplier_id, filename.split('/')[-1])
        else: 
            key = u"supplier/files/{0}".format(filename.split('/')[-1])
        
        obj = S3Object.create(filename,
                            key,
                            u"document.dellarobbiathailand.com",
                            key, 
                            secret)
        
        serializer = S3ObjectSerializer(obj)
        response = HttpResponse(JSONRenderer().render(serializer.data),
                                content_type="application/json")
                                
        response.status_code = 201
        return response

    # If any method other than POST
    else:
        response = HttpResponse('{"message": "Not Allowed"}', content_type='application/json; charset=utf-8')
        response.status_code = 405 
        return response

    
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
        today = datetime.now(tz=timezone('Asia/Bangkok'))
        dt = today - timedelta(days=365)
        acks_count = A.objects.filter(customer=OuterRef('pk'),
                                     time_created__gte=dt) \
                              .exclude(status__in=[u'cancelled', u'paid', u'invoiced', u'closed']) \
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

        open_orders_qs = A.objects.filter(time_created__gte=dt)
        open_orders_qs = open_orders_qs.exclude(status__in=["paid", u'invoiced', u'cancelled'])

        open_quotations_qs = Quotation.objects.filter(time_created__gte=dt)
        open_quotations_qs = open_quotations_qs.exclude(status__in=["paid", u'invoiced', u'cancelled'])

        queryset = queryset.prefetch_related('addresses',
                                             'files',
                                             'contacts',
                                             'acknowledgements',
                                             'quotations',
                                             Prefetch('acknowledgements', 
                                                      queryset=open_orders_qs,
                                                      to_attr='open_orders'),
                                             Prefetch('quotations',
                                                      queryset=open_quotations_qs,
                                                      to_attr='open_quotations'))


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

    def get_queryset(self):
        """
        Override 'filter_queryset' method in order to customize filter
        """

        queryset = self.queryset
        
        today = datetime.now(tz=timezone('Asia/Bangkok'))
        dt = today - timedelta(days=365)
        open_orders_qs = A.objects.filter(time_created__gte=dt)
        open_orders_qs = open_orders_qs.exclude(status__in=["paid", u'invoiced', u'cancelled'])

        open_quotations_qs = Quotation.objects.filter(time_created__gte=dt)
        open_quotations_qs = open_quotations_qs.exclude(status__in=["paid", u'invoiced', u'cancelled'])

        queryset = queryset.prefetch_related('addresses',
                                             'files',
                                             'contacts',
                                             'acknowledgements',
                                             'quotations',
                                             Prefetch('acknowledgements', 
                                                      queryset=open_orders_qs,
                                                      to_attr='open_orders'),
                                             Prefetch('quotations',
                                                      queryset=open_quotations_qs,
                                                      to_attr='open_quotations'))


        return queryset


class SupplierMixin(object):
    queryset = Supplier.objects.all()
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
        
    def filter_queryset(self, queryset):
        """
        Override 'get_queryset' method in order to customize filter
        """
        pos_count = PO.objects.filter(supplier=OuterRef('pk'),
                                      order_date__year=2018) \
                              .exclude(status__in=[u'cancelled', u'paid', u'invoiced', u'closed']) \
                              .values('supplier') \
                              .annotate(num_pos=Count('*')) \
                              .values('num_pos')

        prepped_fn = Coalesce(
            Subquery(pos_count, 
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
        else:
            queryset = queryset[0:50]

        queryset = queryset.prefetch_related('addresses', 'contacts', 'purchase_orders')

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
                    
        
        
        
        
        
        
        
        
        
        