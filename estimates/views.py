import logging
import json
import time
from datetime import datetime, timedelta
from pytz import timezone

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Prefetch
from django.conf import settings

from estimates.models import Estimate, Item, Pillow
from estimates.serializers import EstimateSerializer, ItemSerializer
from contacts.serializers import CustomerSerializer
from contacts.models import Customer
from projects.models import Project
from utilities.http import save_upload
from media.models import S3Object


logger = logging.getLogger(__name__)


def acknowledgement_item_image(request):
    if request.method == "POST":
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "acknowledgement/item/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com')
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url()}),
                                content_type="application/json")
        response.status_code = 201
        return response
        
def acknowledgement_file(request):
    try:
        file = request.FILES['image']
    except MultiValueDictKeyError:
        file = request.FILES['file']
    
    filename = file.name

    #Save file
    with open(filename, 'wb+' ) as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    
    obj = S3Object.create(filename,
                          "acknowledgement/files/{0}".format(filename),
                          "media.dellarobbiathailand.com")
    
    response = HttpResponse(json.dumps({'id': obj.id,
                                        'filename': filename,
                                        'type': filename.split('.')[-1],
                                        'url': obj.generate_url()}), 
                            content_type="application/json")
                            
    response.status_code = 201
    return response
    

class EstimateMixin(object):
    queryset = Estimate.objects.all().order_by('-id')
    serializer_class = EstimateSerializer
    
    def _condense_pillows(self, request):
        """
        Condense the pillows by combining pillows of the same type and fabric
        """
        #Condense pillow data
        for item in request.data['items']:
            #Sort pillows
            if "pillows" in item:
                pillows = {}
                for pillow in item['pillows']:
                    try:
                        fabric_id = pillow['fabric']['id'] if 'id' in pillow['fabric'] else pillow['fabric']
                    except KeyError:
                        fabric_id = None

                    if (pillow['type'], fabric_id) in pillows:
                        pillows[(pillow['type'], fabric_id)]['quantity'] += 1
                    else: 
                        pillows[(pillow['type'], fabric_id)] = {'quantity': 1}
                
                item['pillows'] = []
                for pillow in pillows:
                    pillow_data = {'type': pillow[0],
                                   'fabric': pillow[1]}
                                   
                    if pillows[pillow]['quantity']:
                        pillow_data['quantity'] = pillows[pillow]['quantity']
                        
                    item['pillows'].append(pillow_data)
                    
        return request
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['employee', 'fabric', 'items']
        
        for field in fields:
            if field in request.data:
                if 'id' in request.data[field]:
                    request.data[field] = request.data[field]['id']
               
                    
                if field == 'items':
                    for index, item in enumerate(request.data['items']):
                        try:
                            request.data['items'][index]['fabric'] = item['fabric']['id']
                        except (KeyError, TypeError):
                            pass
                            
                        try:
                            request.data['items'][index]['product'] = item['id']
                            del request.data['items'][index]['id']
                        except KeyError as e:
                            request.data['items'][index]['product'] = 10436
                            
                        try:
                            request.data['items'][index]['image'] = item['image']['id']
                        except (KeyError, TypeError) as e:
                            request.data['items'][index]['image'] = None
                            
                elif field == 'project':
                    try:
                        if "codename" in request.data['project'] and "id" not in request.data['project']:
                            project = Project(codename=request.data['project']['codename'])
                            project.save()
                            request.data['project'] = project.id
                    except TypeError:
                        pass
                   
        return request
        
    def _format_primary_key_data_for_put(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['employee', 'fabric', 'items']
        
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError:
                    if field == 'acknowledgement':
                        request.data[field] = None
                    
                if field == 'items':
                    for index, item in enumerate(request.data['items']):
                        try:
                            request.data['items'][index]['fabric'] = item['fabric']['id']
                        except (KeyError, TypeError):
                            pass
                            
                        if 'product' not in request.data['items'][index]:
                            request.data['items'][index]['product'] = 10436
                            
                        try:
                            request.data['items'][index]['image'] = item['image']['id']
                        except (KeyError, TypeError) as e:
                            request.data['items'][index]['image'] = None
                            
                elif field == 'project':
                    try:
                        if "codename" in request.data['project'] and "id" not in request.data['project']:
                            project = Project(codename=request.data['project']['codename'])
                            project.save()
                            request.data['project'] = project.id
                            
                    except TypeError:
                        pass
                   
        return request

        
class EstimateList(EstimateMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        request = self._condense_pillows(request)
        
        return super(EstimateList, self).post(request, *args, **kwargs)
         
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        
        max_date = datetime.now(timezone('Asia/Bangkok')) - timedelta(days=30)
        queryset = self.queryset.exclude(status__icontains='cancelled', last_modified__lt=max_date)

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(customer__name__icontains=query) | 
                                       Q(pk__icontains=query)).distinct('id')
                                       
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id', None)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
                                      
        offset = self.request.query_params.get('offset', None)
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        
        if offset is not None and limit:
            queryset = queryset[int(offset):int(limit) + (int(offset))]
        elif offset is not None and limit == 0:
            queryset = queryset[int(offset):]
        else:
            queryset = queryset[0:50]

        queryset = queryset
        queryset = queryset.select_related('customer', 'pdf', 'acknowledgement', 'employee', 'project',
                                           )
        
        queryset = queryset.prefetch_related('items', 'items__pillows', 'items__image', 'project__rooms', 'project__phases',
                                             'project__rooms__files', 'customer__addresses') 
        #queryset = queryset.prefetch_related(Prefetch('items', queryset=Item.objects.select_related('image').prefetch_related('pillows')))
        queryset = queryset.defer('acknowledgement__items', 'acknowledgement__customer', 'acknowledgement__project',
                                  'project__customer', 'items', 'customer__contact')
                                  
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit    

class EstimateDetail(EstimateMixin, generics.RetrieveUpdateDestroyAPIView):
    paginate_by = 10
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data_for_put(request)
        
        try:
            request = self._condense_pillows(request)
        except Exception:
            pass
            
        return super(EstimateDetail, self).put(request, *args, **kwargs)
    
class AcknowledgementViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Estimate.objects.all()
    serializer_class = EstimateSerializer
    
    def create(self, request):
        data = request.data
        customer = self._get_customer(request.data['customer']['id'])
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
           
            serializer.save()
        else:
            print serializer.errors
        logger.debug(serializer.data)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
    def _get_customer(self, customer_id):
        return Customer.objects.get(pk=customer_id)
        

class AcknowledgementItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgement items to be viewed or editted
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer