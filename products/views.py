import logging
import time
import json

from rest_framework import viewsets
from rest_framework import generics
from django.db.models import Q
from django.conf import settings
from django.http import HttpResponse

from products.models import Upholstery, Table, Model, Configuration, Supply as ProductSupply
from products.serializers import UpholsterySerializer, TableSerializer, ModelSerializer, ConfigurationSerializer, ProductSupplySerializer
from media.models import S3Object
from utilities.http import save_upload

logger = logging.getLogger(__name__)


def product_image(request):
    if request.method == "POST":
        credentials = request.user.aws_credentials
        key = credentials.access_key_id
        secret = credentials.secret_access_key
        
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "acknowledgement/item/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com',
                        key,
                        secret)
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url(key, secret)}),
                                content_type="application/json")
        response.status_code = 201
        return response
        
        
class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit configurations
    """
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(configuration__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            

class ModelMixin(object):
    """
    API endpoint to view and edit models
    """
    queryset = Model.objects.all()
    serializer_class = ModelSerializer
    
    
class ModelList(ModelMixin, generics.ListCreateAPIView):
   
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(name__icontains=query) |
                                       Q(model__icontains=query) |
                                       Q(collection__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            

class ModelDetail(ModelMixin, generics.RetrieveUpdateDestroyAPIView):   
    pass
    
                
class UpholsteryMixin(object):
    queryset = Upholstery.objects.all()
    serializer_class = UpholsterySerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['model', 'configuration', 'image']
        try:
            del request.data['pillows']
        except KeyError:
            pass
            
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError as e:
                    logger.warn(e)
                        
                    
        return request
        
                    
class UpholsteryList(UpholsteryMixin, generics.ListCreateAPIView):
 
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(UpholsteryList, self).post(request, *args, **kwargs)
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(description__icontains=query) |
                                       Q(model__model__icontains=query) |
                                       Q(model__name__icontains=query) |
                                       Q(configuration__configuration__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', self.request.query_params.get('page_size', settings.REST_FRAMEWORK['PAGINATE_BY'])))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit
            
                    
class UpholsteryDetail(UpholsteryMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(UpholsteryDetail, self).put(request, *args, **kwargs) 
    
    
class UpholsteryViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit table
    """
    queryset = Upholstery.objects.all()
    serializer_class = UpholsterySerializer
    
    
class TableMixin(object):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['model', 'configuration', 'image']
        
        for field in fields:
            try:
                if field in request.data:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
            except TypeError:
                pass
                    
        return request
        
                    
class TableList(TableMixin, generics.ListCreateAPIView):
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(TableList, self).post(request, *args, **kwargs)
        
        
class TableDetail(TableMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(TableDetail, self).put(request, *args, **kwargs)
        
        
class TableViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit table
    """
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    
    
class SupplyMixin(object):
    queryset = ProductSupply.objects.all()
    serializer_class = ProductSupplySerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['product', 'supply']
        
        for field in fields:
            try:
                if field in request.data:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
            except TypeError:
                pass
                    
        return request
        
                    
class ProductSupplyList(SupplyMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        product_id = self.request.query_params.get('product__id', None)
        if product_id:
            queryset = queryset.filter(product__id=product_id)
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            
        return queryset
        
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(ProductSupplyList, self).post(request, *args, **kwargs)
        
        
class ProductSupplyDetail(SupplyMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return super(ProductSupplyDetail, self).put(request, *args, **kwargs)
        
        