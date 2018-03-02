#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import json
import time
import dateutil
import unicodecsv as csv
from datetime import datetime, timedelta
from pytz import timezone

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction, connection
from django.db.models import Q
from django.conf import settings

from deals.models import Deal
from deals.serializers import DealSerializer


logger = logging.getLogger(__name__)


class DealMixin(object):
    queryset = Deal.objects.all().order_by('-id')
    serializer_class = DealSerializer
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['project', 'customer', 'contact', 'acknowledgement', 'quotation']
        
        for field in fields:
            if field in request.data:
                try:
                    request.data[field] = request.data[field]['id']
                except (TypeError, KeyError) as e:
                    pass
                    
                if field == 'project':
                    try:
                        if "codename" in request.data['project'] and "id" not in request.data['project']:
                            project = Project(codename=request.data['project']['codename'])
                            project.save()
                            request.data['project'] = project.id
                    except TypeError:
                        pass
                   
        return request

        
class DealList(DealMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        return super(DealList, self).post(request, *args, **kwargs)
         
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        max_date = datetime.now(timezone('Asia/Bangkok')) - timedelta(days=30)
        queryset = self.queryset.exclude(status__icontains='closed', last_modified__lt=max_date)
        
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status__icontains=status)
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(customer__name__icontains=query) | 
                                       Q(pk__icontains=query)).distinct('id')
                        
        #Filter by project
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id', None)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
            
        offset = self.request.query_params.get('offset', None)
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        
        if offset != None and limit:
            queryset = queryset[int(offset):limit + int(offset)]
        if offset == 0 and limit == 0:
            queryset = queryset[0:]
        else:
            queryset = queryset[0:50]
        
        queryset = queryset.select_related('customer', 'contact', 'employee')
        queryset = queryset.prefetch_related('customer__contacts', 'customer__addresses')
            
        return queryset
        

class DealDetail(DealMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
               
        return super(DealDetail, self).put(request, *args, **kwargs)
        
        
        
        
        