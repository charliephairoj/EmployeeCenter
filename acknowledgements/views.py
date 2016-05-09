#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import json
import time
import dateutil
import unicodecsv as csv

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import transaction, connection
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


def acknowledgement_stats(request):
    cursor = connection.cursor()
    query = """
    SELECT (SELECT COUNT(id) 
            FROM acknowledgements_acknowledgement where lower(status) = 'acknowledged'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'acknowledged'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'in production'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'in production'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'ready to ship'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'ready to ship'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'shipped'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'shipped'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'invoiced'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'invoiced'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'paid'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'paid'),
           (SELECT COUNT(id) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'deposit received'),
           (SELECT SUM(total) 
                       FROM acknowledgements_acknowledgement where lower(status) = 'deposit received'),
           COUNT(id),
           SUM(total)
    FROM acknowledgements_acknowledgement AS a
    WHERE lower(status) != 'cancelled';
    """
    
    cursor.execute(query)
    row = cursor.fetchone()
    
    data = {'acknowledged': {'count': row[0], 'amount': str(row[1])},
            'in_production': {'count':row[2], 'amount': str(row[3])},
            'ready_to_ship': {'count': row[4], 'amount': str(row[5])},
            'shipped': {'count':row[6], 'amount': str(row[7])},
            'invoiced': {'count': row[8], 'amount': str(row[9])},
            'paid': {'count': row[10], 'amount': str(row[11])},
            'deposit_received': {'count': row[12], 'amount': str(row[13])},
            'total': {'count': row[-2], 'amount': str(row[-1])}}
            
    response = HttpResponse(json.dumps(data),
                            content_type="application/json")
    response.status_code = 200
    return response
    
    
def acknowledgement_item_image(request):
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
        
def acknowledgement_file(request):
    try:
        file = request.FILES['image']
    except Exception:
        file = request.FILES['file']
    
    filename = file.name

    #Save file
    with open(filename, 'wb+' ) as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    credentials = request.user.aws_credentials
    key = credentials.access_key_id
    secret = credentials.secret_access_key
    
    obj = S3Object.create(filename,
                          u"acknowledgement/files/{0}".format(filename),
                          u"media.dellarobbiathailand.com",
                          key, 
                          secret)
    
    response = HttpResponse(json.dumps({'id': obj.id,
                                        'filename': filename,
                                        'type': filename.split('.')[-1],
                                        'url': obj.generate_url(key, secret)}), 
                            content_type="application/json")
                            
    response.status_code = 201
    return response
    

def acknowledgement_download(request):
    
    # Get the start and ending date to filter
    start_date = dateutil.parser.parse(request.GET.get('start'))
    end_date = dateutil.parser.parse(request.GET.get('end'))
    logger.warn(start_date)
    logger.warn(end_date)
    
    # Get the Acknowledgements
    acknowledgements = Acknowledgement.objects.filter(time_created__gte=start_date, 
                                          time_created__lte=end_date)
    
    # Create the respones and write headers 
    filename = 'Acknowledgements_{0}_{1}'.format(start_date.strftime('%Y-%m-%d'),
                                                 end_date.strftime('%Y-%m-%d'))       
    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(filename)
    
    # Write BOM to make UTF-8     
    response.write("\xEF\xBB\xBF")

    # Write to file
    writer = csv.writer(response, encoding='cp874')
    writer.writerow(['id', 'date', 'customer', 'vat', 'total'])
    
    for acknowledgement in acknowledgements:
        writer.writerow([acknowledgement.id,
                         acknowledgement.time_created,
                         u'{0}'.format(acknowledgement.customer.name),
                         '{0}'.format(acknowledgement.vat),
                         '{0}'.format(acknowledgement.total)])
                         
    return response
    
    
class AcknowledgementMixin(object):
    queryset = Acknowledgement.objects.all().order_by('-id')
    serializer_class = AcknowledgementSerializer
  
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
                    except (KeyError, TypeError):
                        fabric_id = None

                    if (pillow['type'], fabric_id) in pillows:
                        pillows[(pillow['type'], fabric_id)]['quantity'] += 1
                        pillows[(pillow['type'], fabric_id)]['fabric_quantity'] += pillow['fabric_quantity']
                    else: 
                        try:
                            pillows[(pillow['type'], fabric_id)] = {'quantity': 1, 'fabric_quantity': pillow['fabric_quantity']}
                        except KeyError:
                            pillows[(pillow['type'], fabric_id)] = {'quantity': 1, 'fabric_quantity': 0}
                
                item['pillows'] = []
                for pillow in pillows:
                    pillow_data = {'type': pillow[0],
                                   'fabric': pillow[1]}
                                   
                    if pillows[pillow]['quantity']:
                        pillow_data['quantity'] = pillows[pillow]['quantity']
                    
                    try:
                        pillow_data['fabric_quantity'] = pillows[pillow]['fabric_quantity']
                    except KeyError:
                        pass
                        
                    item['pillows'].append(pillow_data)
                    
        return request
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['project', 'customer', 'fabric', 'items', 'room', 'phase']
        
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
        fields = ['project', 'customer', 'fabric', 'items', 'room', 'phase']
        
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
        queryset = self.queryset.all()
        
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
            
        #Filter if decoroom
        user = self.request.user
        if user.groups.filter(name__icontains='decoroom').count() > 0:
            queryset = queryset.filter(Q(customer__name__icontains="decoroom") |
                                       Q(customer__id=420) |
                                       Q(customer__id=257))
            
        offset = self.request.query_params.get('offset', None)
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        
        if offset != None and limit:
            queryset = queryset[int(offset):limit + int(offset)]
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

class AcknowledgementDetail(AcknowledgementMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    paginate_by = 10
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data_for_put(request)
        
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