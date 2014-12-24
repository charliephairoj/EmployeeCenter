from io import BytesIO
import logging
from decimal import Decimal
import json
import time


from rest_framework import viewsets
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Log, Product
from supplies.PDF import SupplyPDF
from utilities.http import save_upload
from auth.models import S3Object
from supplies.serializers import SupplySerializer, FabricSerializer, LogSerializer



logger = logging.getLogger(__name__)


def supply_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "supply/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
        response.status_code = 201
        return response
        
        
@login_required
def shopping_list(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="supply-shopping-list.pdf"'
    buffer = BytesIO()
    
    pdf = SupplyPDF(filename=buffer)
    pdf.create()
    
    data = buffer.getvalue()
    buffer.close()
    response.write(data)
    return response
    

class SupplyMixin(object):
    queryset = Supply.objects.all().order_by('description')
    serializer_class = SupplySerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(SupplyMixin, self).handle_exception(exc)
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['supplier', 'image', 'suppliers', 'sticker']
        
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError:
                    pass
                    
                #format for supplier in suppliers list
                if field == 'suppliers':
                    for index, supplier in enumerate(request.data[field]):
                        try:
                            request.data[field][index]['supplier'] = supplier['supplier']['id']
                        except (KeyError, TypeError):
                            try:
                                request.data[field][index]['supplier'] = supplier['id']
                            except KeyError:
                                pass
        return request
    
    
class SupplyList(SupplyMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(SupplyList, self).post(request, *args, **kwargs)
        
        return response
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(products__supplier__name__icontains=query) | 
                                       Q(description__icontains=query) |
                                       Q(products__reference__icontains=query))
        
        #Filter based on supplier
        s_id = self.request.QUERY_PARAMS.get('supplier_id', None)
        if s_id:
            queryset = queryset.filter(products__supplier_id=s_id)
        
        #Filter based on product upc code
        upc = self.request.QUERY_PARAMS.get('upc', None)
        if upc:
            queryset = queryset.filter(products__upc=upc)

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
    
    

class SupplyDetail(SupplyMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(SupplyDetail, self).put(request, *args, **kwargs)
        
        return response


class SupplyTypeList(viewsets.ModelViewSet):
    def type(self, request, *args, **kwargs):
        data = [s for s in Supply.objects.values_list('type', flat=True).distinct()]
        return Response(data=data, status=status.HTTP_200_OK)
        
    
supply_type_list = SupplyTypeList.as_view({
    'get': 'type'
})
    

class FabricList(SupplyList):
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer
    

class FabricDetail(SupplyDetail):
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer
            
    
class FabricViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit models
    """
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer
    
    
class LogViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit upholstery
    """
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    
    def get_queryset(self):
        
        queryset = self.queryset
        
        supply_id = self.request.QUERY_PARAMS.get('supply', None)

        if supply_id:
            queryset = queryset.filter(supply_id=supply_id)
            
        action = self.request.QUERY_PARAMS.get('action', None)

        if supply_id:
            queryset = queryset.filter(action=action)
            
        return queryset
