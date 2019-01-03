import logging
import json
import time
from datetime import datetime, timedelta
from pytz import timezone

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Prefetch
from django.conf import settings
from django.contrib.auth.decorators import login_required

from estimates.models import Estimate, Item, Pillow
from estimates.serializers import EstimateSerializer, ItemSerializer
from contacts.serializers import CustomerSerializer
from contacts.models import Customer
from projects.models import Project
from utilities.http import save_upload
from media.models import S3Object
from media.serializers import S3ObjectSerializer
from administrator.models import User


logger = logging.getLogger(__name__)


@login_required
def estimate_item_image(request, q_id=None):

    if request.method == "POST":
        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''
        
        filename = save_upload(request)

        if q_id:
            key = u"estimate/{0}/item/image/{1}".format(q_id, filename.split('/')[-1])
        else: 
            key = u"estimate/item/image/{0}".format(filename.split('/')[-1])

        obj = S3Object.create(filename,
                        key,
                        'media.dellarobbiathailand.com',
                        key, 
                        secret)

        serializer = S3ObjectSerializer(obj)
        response = HttpResponse(JSONRenderer().render(serializer.data),
                                content_type="application/json")
        response.status_code = 201
        return response


@login_required
def estimate_file(request, q_id=None):

    if request.method == "POST":

        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''

        filename = save_upload(request)

        if q_id:
            key = u"estimate/{0}/files/{1}".format(q_id, filename.split('/')[-1])
        else: 
            key = u"estimate/files/{0}".format(filename.split('/')[-1])
        
        obj = S3Object.create(filename,
                            key,
                            u"document.dellarobbiathailand.com",
                            key, 
                            secret)
        
        serializer = S3ObjectSerializer(obj)
        response = HttpResponse(JSONRenderer().render(serializer.data),
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
        fields = ['fabric', 'items']
        
        for f in [('customer', Customer), ('project', Project), ('employee', User)]:
            try:
                pass#request.data[f[0]] = f[1].objects.get(pk=request.data[f[0]]['id'])
            except (AttributeError, KeyError, IndexError) as e:
                pass

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
                            request.data['items'][index]['product'] = {'id': item['id']}
                            del request.data['items'][index]['id']
                        except KeyError as e:
                            request.data['items'][index]['product'] = {'id': 10436}
                        
                        """
                        try:
                            request.data['items'][index]['image'] = item['image']['id']
                        except (KeyError, TypeError) as e:
                            request.data['items'][index]['image'] = None
                        """
                         
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
        fields = ['fabric', 'items']
        for f in [('customer', Customer), ('project', Project), ('employee', User)]:
            try:
                pass#request.data[f[0]] = f[1].objects.get(pk=request.data[f[0]]['id'])
            except (AttributeError, KeyError, IndexError) as e:
                pass

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
                            try:
                                request.data['items'][index]['product'] = {'id': item['id']}
                                del request.data['items'][index]['id']
                            except KeyError as e:
                                request.data['items'][index]['product'] = {'id': 10436}


                        """    
                        try:
                            request.data['items'][index]['image'] = item['image']['id']
                        except (KeyError, TypeError) as e:
                            request.data['items'][index]['image'] = None
                        """

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

        elif offset is None and limit:
            queryset = queryset[0:limit]
        else:
            queryset = queryset[0:50]
        
        queryset = queryset.select_related('customer', 'pdf', 'acknowledgement', 'employee', 'project', 'deal',
                                           )
        
        queryset = queryset.prefetch_related('items',
                                             'items__pillows',
                                             'items__image',
                                             'items__product',
                                             'customer__addresses', 
                                             'files',) 
        #queryset = queryset.prefetch_related(Prefetch('items', queryset=Item.objects.select_related('image').prefetch_related('pillows')))
        queryset = queryset.defer('acknowledgement__items', 'acknowledgement__customer', 'acknowledgement__project',
                                  'project__customer', 'items', 'customer__contact', 'project__estimates')
                                  
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
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
                
        queryset = queryset.select_related('customer', 'pdf', 'acknowledgement', 'employee', 'project', 'deal',
                                           )
        
        queryset = queryset.prefetch_related('items',
                                             'items__pillows',
                                             'items__image',
                                             'items__product',
                                             'customer__addresses', 
                                             'files',) 
        #queryset = queryset.prefetch_related(Prefetch('items', queryset=Item.objects.select_related('image').prefetch_related('pillows')))
        queryset = queryset.defer('acknowledgement__items', 'acknowledgement__customer', 'acknowledgement__project',
                                  'project__customer', 'items', 'customer__contact', 'project__estimates')
        
        return queryset
    
