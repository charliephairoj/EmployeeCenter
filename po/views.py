# Create your views here.

import json
import logging

from django.http import HttpResponse
from django.db.models import Q
from utilities.http import process_api
from rest_framework import generics

from po.serializers import PurchaseOrderSerializer
from po.models import PurchaseOrder
from projects.models import Project


logger = logging.getLogger(__name__)


class PurchaseOrderMixin(object):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    
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
            if field in request.DATA:
                if 'id' in request.DATA[field]:
                    request.DATA[field] = request.DATA[field]['id']

        #Loop through data in order to prepare for deserialization
        for index, item in enumerate(request.DATA['items']):
            #Only reassign the 'id' if it is post
            try:
                request.DATA['items'][index]['supply'] = item['supply']['id']
            except KeyError:
                pass

            try:
                request.DATA['items'][index]['unit_cost'] = item['cost']
            except KeyError:
                pass
            
            
            if field == 'project':
                try:
                    if "codename" in request.DATA['project'] and "id" not in request.DATA['project']:
                        project = Project(codename=request.DATA['project']['codename'])
                        project.save()
                        request.DATA['project'] = project.id
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
                                      
        return queryset
        
    
class PurchaseOrderDetail(PurchaseOrderMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method
        """
        request = self._format_primary_key_data(request)
        return super(PurchaseOrderDetail, self).put(request, *args, **kwargs)
        
        
        
        
