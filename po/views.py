# Create your views here.

import json
import logging

from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
from utilities.http import process_api
from rest_framework import generics
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView

from po.serializers import PurchaseOrderSerializer
from po.models import PurchaseOrder
from projects.models import Project


logger = logging.getLogger(__name__)


class PurchaseOrderMixin(object):
    queryset = PurchaseOrder.objects.all().order_by('-id')
    serializer_class = PurchaseOrderSerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(PurchaseOrderMixin, self).handle_exception(exc)
    
    def post_save(self, obj, *args, **kwargs):
        
        obj.calculate_total()
        obj.save()
        #obj.create_and_upload_pdf()
        
        return obj
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['supplier', 'project']

        for field in fields:
            if field in request.data:
                try:
                    request.data[field] = request.data[field]['id']
                except (TypeError, KeyError) as e:
                    logger.warn(e)

        #Loop through data in order to prepare for deserialization
        for index, item in enumerate(request.data['items']):
            #Only reassign the 'id' if it is post
            try:
                request.data['items'][index]['supply'] = item['supply']['id']
            except (TypeError, KeyError):
                try:
                    request.data['items'][index]['supply'] = item['id']
                except (TypeError, KeyError):
                    pass
                    

            try:
                request.data['items'][index]['unit_cost'] = item['cost']
            except KeyError:
                pass
            
            
            if field == 'project':
                try:
                    if "codename" in request.data['project'] and "id" not in request.data['project']:
                        project = Project(codename=request.data['project']['codename'])
                        project.save()
                        request.data['project'] = project.id
                except (KeyError, TypeError):
                    pass
        
        return request
        
        
class PurchaseOrderList(PurchaseOrderMixin, generics.ListCreateAPIView):
    def post(self, request, *args, **kwargs):
        """
        Override the 'post' method
        """
        request = self._format_primary_key_data(request)
        return super(PurchaseOrderList, self).post(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(supplier__name__icontains=query) | 
                                       Q(pk__icontains=query) |
                                       Q(items__description__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit            
    
class PurchaseOrderDetail(PurchaseOrderMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method
        """
        request = self._format_primary_key_data(request)
        return super(PurchaseOrderDetail, self).put(request, *args, **kwargs)
        