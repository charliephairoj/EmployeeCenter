import logging
import time
import json

from rest_framework import viewsets
from rest_framework import generics
from django.db.models import Q
from django.conf import settings
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError

from products.models import Upholstery, Table, Model, Configuration, Supply as ProductSupply
from products.serializers import UpholsterySerializer, TableSerializer, ModelSerializer, ConfigurationSerializer, ProductSupplySerializer
from media.models import S3Object
from utilities.http import save_upload

logger = logging.getLogger(__name__)


def model_public(request):
    if request.method.lower() == "get":
        models = Model.objects.filter(web_active=True, type='upholstery').order_by('name')
        mdoels = models.prefetch_related('images')
        models_data = [{'name': model.name,
                        'model': model.model,
                        'images': [img.generate_url(time=31560000) for img in model.images.filter(web_active=True).order_by('-primary')]}
                        for model in models]
        response = HttpResponse(json.dumps(models_data), 
                                content_type="application/json")
        response.status_code = 200
        return response


def bed_public(request):
    if request.method.lower() == "get":
        models = Model.objects.filter(web_active=True, type='bed').order_by('name')
        models = models.prefetch_related('images')
        models_data = [{'name': model.name,
                        'model': model.model,
                        'images': [img.generate_url(time=31560000) for img in model.images.filter(web_active=True).order_by('-primary')]}
                        for model in models]
        response = HttpResponse(json.dumps(models_data), 
                                content_type="application/json")
        response.status_code = 200
        return response
        
        
def product_image(request):
    if request.method == "POST":
        try:
            filename = request.FILES['file'].name
        except MultiValueDictKeyError:
            filename = request.FILES['image'].name

        filename = save_upload(request, filename=filename)

        obj = S3Object.create(filename,
                        "acknowledgement/item/image/{0}_{1}".format(time.time(), filename.split('/')[-1]),
                        'media.dellarobbiathailand.com')
                        
        
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url(),
                                            'key': obj.key,
                                            'bucket':obj.bucket}),
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
        queryset = self.queryset.all().order_by('configuration')
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(configuration__icontains=query))
                                      
        offset = self.request.query_params.get('offset', None)
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        logger.debug(offset)
        logger.debug(limit)
        if offset is not None and limit:
            logger.debug('yay')
            queryset = queryset[int(offset) - 1:limit + (offset - 1)]
        elif limit == 0:
            queryset = queryset[0:]
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

        #queryset = queryset.select_related()
        queryset = queryset.prefetch_related('images')
            
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
        fields = ['model', 'configuration', 'image', 'schematic']
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
                        
        logger.debug(request.data)       
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
        
        # Filter by model id
        model_id = self.request.query_params.get('model_id', None)
        if model_id:
            queryset = queryset.filter(model_id=model_id)
        
        # Filter based on query
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
            
        queryset = queryset.select_related('model', 'configuration', 'image', 'schematic')
        queryset = queryset.prefetch_related('model__images', 'pillows', 'supplies')
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
        
        