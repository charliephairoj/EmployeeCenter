# Create your views here.

import json
import logging

from django.http import HttpResponse
from django.db import connection
from django.db.models import Q
from django.conf import settings
from rest_framework import generics

from po.serializers import PurchaseOrderSerializer
from po.models import PurchaseOrder
from projects.models import Project


logger = logging.getLogger(__name__)


def purchase_order_stats(request):
    cursor = connection.cursor()
    query = """
    SELECT (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'processed') AS processed_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'processed') AS processed_sum,
    (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'received') AS received_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'received') AS received_sum,
    (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'paid') AS paid_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'paid') AS paid_sum,
    COUNT(id) AS total_count,
    SUM(total) AS total_sum
    FROM po_purchaseorder
    WHERE lower(status) != 'cancelled';
    """
    
    cursor.execute(query)
    row = cursor.fetchone()

    data = {'processed': {'count': row[0], 'amount': str(row[1])},
            'received': {'count': row[2], 'amount': str(row[3])},
            'paid': {'count': row[4], 'amount': str(row[5])},
            'total': {'count': row[6], 'amount': str(row[7])}}
    
    response = HttpResponse(json.dumps(data),
                            content_type="application/json")
    response.status_code = 200
    return response
    

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
        # obj.create_and_upload_pdf()
        
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

        # Loop through data in order to prepare for deserialization
        for index, item in enumerate(request.data['items']):
            # Only reassign the 'id' if it is post
            try:
                request.data['items'][index]['supply'] = item['supply']['id']
            except (TypeError, KeyError):
                try:
                    request.data['items'][index]['supply'] = item['id']
                except (TypeError, KeyError):
                    logger.error(item)

            try:
                request.data['items'][index]['unit_cost'] = item['cost']
            except KeyError:
                pass
            
            if field == 'project':
                try:
                    if "id" not in request.data['project']:
                        codename = request.data['project']['codename']
                        project = Project(codename=codename)
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
        
        # Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(supplier__name__icontains=query) |
                                       Q(pk__icontains=query) |
                                       Q(items__description__icontains=query))
            queryset = queryset.distinct('id')
                                       
        # Filter by project
        project_id = self.request.QUERY_PARAMS.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        # Last modified
        last_modified = self.request.QUERY_PARAMS.get('last_modified', None)
        if last_modified:
            logger.debug(last_modified)
            queryset = queryset.filter(last_modified__gte=last_modified)
                                      
        offset = int(self.request.query_params.get('offset', 0))
        settings_paginate_by = settings.REST_FRAMEWORK['PAGINATE_BY']
        limit = self.request.query_params.get('limit', settings_paginate_by)
        limit = int(limit)
        
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        settings_paginate_by = settings.REST_FRAMEWORK['PAGINATE_BY']
        limit = self.request.query_params.get('limit', settings_paginate_by)
        limit = int(limit)
        
        return self.queryset.count() if limit == 0 else limit


class PurchaseOrderDetail(PurchaseOrderMixin,
                          generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method
        """
        request = self._format_primary_key_data(request)
        return super(PurchaseOrderDetail, self).put(request, *args, **kwargs)
        