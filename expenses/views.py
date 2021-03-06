#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import json
import time
import dateutil
import unicodecsv as csv
from pytz import timezone
from datetime import datetime, timedelta

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.http import HttpResponse
from django.db import transaction, connection
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.decorators import login_required

from invoices.models import Invoice, Item
from invoices.serializers import InvoiceSerializer, ItemSerializer
from contacts.serializers import CustomerSerializer
from contacts.models import Customer
from projects.models import Project, Room
from utilities.http import save_upload
from media.models import S3Object
from media.serializers import S3ObjectSerializer


logger = logging.getLogger(__name__)


def invoice_stats(request):
    cursor = connection.cursor()
    query = """
    SELECT (SELECT COUNT(id) 
            FROM invoices_invoice where lower(status) = 'acknowledged'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'acknowledged'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'in production'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'in production'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'ready to ship'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'ready to ship'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'shipped'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'shipped'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'invoiced'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'invoiced'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'paid'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'paid'),
           (SELECT COUNT(id) 
                       FROM invoices_invoice where lower(status) = 'deposit received'),
           (SELECT SUM(total) 
                       FROM invoices_invoice where lower(status) = 'deposit received'),
           COUNT(id),
           SUM(total)
    FROM invoices_invoice AS a
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
    

@login_required
def invoice_item_image(request, ack_id=None):

    if request.method.lower() == "post":
        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''
        
        filename = save_upload(request)

        if ack_id:
            key = u"invoice/{0}/item/image/{1}".format(ack_id, filename.split('/')[-1])
        else: 
            key = u"invoice/item/image/{0}".format(filename.split('/')[-1])

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

    # If any method other than POST
    else:
        response = HttpResponse('{"message": "Not Allowed"}', content_type='application/json; charset=utf-8')
        response.status_code = 405 
        return response


@login_required
def invoice_file(request, ack_id=None):

    if request.method.lower() == "post":

        try:
            credentials = request.user.aws_credentials
            key = credentials.access_key_id
            secret = credentials.secret_access_key
        except AttributeError as e:
            logger.error(e)
            key = ''
            secret = ''

        filename = save_upload(request)

        if ack_id:
            key = u"invoice/{0}/files/{1}".format(ack_id, filename.split('/')[-1])
        else: 
            key = u"invoice/files/{0}".format(filename.split('/')[-1])
        
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

    # If any method other than POST
    else:
        response = HttpResponse('{"message": "Not Allowed"}', content_type='application/json; charset=utf-8')
        response.status_code = 405 
        return response
    

def invoice_download(request):
    
    # Get the start and ending date to filter
    start_date = dateutil.parser.parse(request.GET.get('start'))
    end_date = dateutil.parser.parse(request.GET.get('end'))
    logger.warn(start_date)
    logger.warn(end_date)
    
    # Get the Invoices
    invoices = Invoice.objects.filter(time_created__gte=start_date, 
                                          time_created__lte=end_date)
    
    # Create the respones and write headers 
    filename = 'Invoices_{0}_{1}'.format(start_date.strftime('%Y-%m-%d'),
                                                 end_date.strftime('%Y-%m-%d'))       
    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(filename)
    
    # Write BOM to make UTF-8     
    response.write("\xEF\xBB\xBF")

    # Write to file
    writer = csv.writer(response, encoding='cp874')
    writer.writerow(['id', 'date', 'customer', 'vat', 'total'])
    
    for invoice in invoices:
        writer.writerow([invoice.id,
                         invoice.time_created,
                         u'{0}'.format(invoice.customer.name),
                         '{0}'.format(invoice.vat),
                         '{0}'.format(invoice.total)])
                         
    return response
    
    
class InvoiceMixin(object):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
      
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """

        if request.data['due_date'] in [0, '0']:
            d = datetime.now()
            bkk_tz = timezone('Asia/Bangkok')
            d = bkk_tz.localize(d) + timedelta(days=30)
            request.data['due_date'] = d.isoformat()

        fields = ['items']
        
        for field in fields:
            if field in request.data:
                        
                if 'id' in request.data[field]:
                    request.data[field] = request.data[field]['id']
               
                    
                if field == 'items':
                    for index, item in enumerate(request.data['items']):
                        try:
                            request.data['items'][index]['product'] = {'id': item['id']}
                            del request.data['items'][index]['id']
                        except KeyError as e:
                            request.data['items'][index]['product'] = {'id': 10436}
                   
        return request
        
    def _format_primary_key_data_for_put(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['items']
        
        for field in fields:
            if field in request.data:
                try:
                    if 'id' in request.data[field]:
                        request.data[field] = request.data[field]['id']
                except TypeError:
                    pass

        return request

        
class InvoiceList(InvoiceMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        return super(InvoiceList, self).post(request, *args, **kwargs)
         
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all().order_by('-id')
        
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
        elif offset is None and limit:
            queryset = queryset[0:limit]
        else:
            queryset = queryset[0:50]
        
        
        queryset = queryset.select_related('customer', 
                                            'project', 
                                            'room',
                                            'phase',
                                            'employee',
                                            'pdf',)
        queryset = queryset.prefetch_related('logs', 
                                             'logs__user',
                                             'customer__addresses',
                                             'customer__files',
                                             'items',
                                             'items__image',
                                             'items__product',
                                             'files')
        
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if limit == 0:
            return self.queryset.count()
        else:
            return limit   
         

class InvoiceDetail(InvoiceMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    paginate_by = 10
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data_for_put(request)
               
        return super(InvoiceDetail, self).put(request, *args, **kwargs)

    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
                
        queryset = queryset.select_related('customer', 
                                            'project', 
                                            'room',
                                            'phase',
                                            'employee',
                                            'pdf',)
        queryset = queryset.prefetch_related('logs', 
                                             'logs__user',
                                             'customer__addresses',
                                             'items',
                                             'items__image',
                                             'items__product',
                                             'files')
        
        return queryset

    
class InvoiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows invoices to be view or editted
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    
    def create(self, request):
        data = request.data
        customer = self._get_customer(request.data['customer']['id'])
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
           
            serializer.save()
        else:
            logger.debug(serializer.errors)
        logger.debug(serializer.data)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
    def _get_customer(self, customer_id):
        return Customer.objects.get(pk=customer_id)
        

class InvoiceItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows invoice items to be viewed or editted
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer