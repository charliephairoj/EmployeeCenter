import logging
import json
import time

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from acknowledgements.models import Acknowledgement, Item, Pillow
from acknowledgements.serializers import AcknowledgementSerializer, ItemSerializer
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
        

class AcknowledgementMixin(object):
    queryset = Acknowledgement.objects.all().order_by('-id')
    serializer_class = AcknowledgementSerializer
    
    def handle_exception(self, exc):
        """
        Custom Exception Handler
        
        Exceptions are logged as error via logging, 
        which will send an email to the system administrator
        """
        logger.error(exc)        
        
        return super(AcknowledgementMixin, self).handle_exception(exc)
    
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
        fields = ['project', 'customer', 'fabric', 'items']
        
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

        
class AcknowledgementList(AcknowledgementMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        request = self._condense_pillows(request)
        
        return super(AcknowledgementList, self).post(request, *args, **kwargs)
         
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(customer__name__icontains=query) | 
                                       Q(pk__icontains=query))
                                      
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

class AcknowledgementDetail(AcknowledgementMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    paginate_by = 10
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        request = self._condense_pillows(request)
        
        return super(AcknowledgementDetail, self).put(request, *args, **kwargs)
    
class AcknowledgementViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows acknowledgements to be view or editted
    """
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    
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