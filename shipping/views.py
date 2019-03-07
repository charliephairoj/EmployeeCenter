#!/usr/bin/python
# -*- coding: utf-8 -*-
# Create your views here.
import json
import os
import time
import dateutil.parser
import logging

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from rest_framework import generics
from django.db.models import Q
from django.conf import settings

from shipping.models import Shipping
from shipping.serializers import ShippingSerializer
from acknowledgements.models import Acknowledgement
from contacts.models import Customer
from contacts.serializers import CustomerSerializer
from projects.models import Project, Room, Phase


logger = logging.getLogger(__name__)


class ShippingMixin(object):
    queryset = Shipping.objects.all().order_by('-id')
    serializer_class = ShippingSerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
                            
        
        for index, item in enumerate(request.data['items']):
            try:
                request.data['items'][index]['item'] = {'id': item['id']}
                del request.data['items'][index]['id']
            except KeyError as e:
                logger.warn(e)
        
        return request

    def _format_primary_key_data_for_put(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        project = None
        room = None
        fields = ['items']
        
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError:
                    pass
                    
                if field == 'items':
                    for index, item in enumerate(request.data['items']):
                        try:
                            request.data['items'][index]['fabric'] = item['fabric']['id']
                        except (KeyError, TypeError):
                            pass
                            
                        try:
                            request.data['items'][index]['image'] = item['image']['id']
                        except (KeyError, TypeError) as e:
                            request.data['items'][index]['image'] = None
                            
                # Create a project if it does not exist
                elif field == 'project':
                    try:
                        project = Project.objects.get(pk=request.data[field]['id'])
                    except KeyError as e:
                        project = Project(codename=request.data[field]['codename'])
                        project.save()
                        request.data[field]['id'] = project.id
                    except TypeError as e:
                        pass
                    
                # Create a room if it does not exist
                elif field == 'room':
                    try: 
                        room = Room.objects.get(pk=request.data[field]['id'])
                    except (KeyError, AttributeError) as e:
                        room = Room(description=request.data[field]['description'],
                                    project=project)
                        room.save()
                        request.data[field]['id'] = room.id
                    except TypeError as e:
                        pass


        

        return request
    
    
class ShippingList(ShippingMixin, generics.ListCreateAPIView):
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(pk__icontains=query) | 
                                       Q(customer__name__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]

        queryset = queryset.select_related('acknowledgement',
                                           'pdf',
                                           'customer',
                                           'employee',
                                           'project')
        queryset = queryset.prefetch_related('items',
                                             'customer__addresses',
                                             'items__item')
            
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit        
        
class ShippingDetail(ShippingMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
