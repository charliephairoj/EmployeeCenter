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
        project = None
        room = None
        fields = ['acknowledgement', 'project', 'room', 'customer']
        
        for field in fields:
            if field in request.data:
                logger.debug(field)
                logger.debug(request.data[field])
                
                # Create a project if it does not exist
                if field == 'project':
                    try:
                        project = Project.objects.get(pk=request.data[field]['id'])
                    except KeyError as e:
                        project = Project(codename=request.data[field]['codename'])
                        project.save()
                        request.data[field]['id'] = project.id
                    
                # Create a room if it does not exist
                elif field == 'room':
                    try: 
                        room = Room.objects.get(pk=request.data[field]['id'])
                    except (KeyError, AttributeError) as e:
                        room = Room(description=request.data[field]['description'],
                                    project=project)
                        room.save()
                        request.data[field]['id'] = room.id

                elif field == 'customer':
                    try:
                        customer = Customer.objects.get(pk=request.data[field]['id'])
                    except (KeyError, AttributeError) as e:
                        customer_serializer = CustomerSerializer(data=request.data[field])
                        
                        if customer_serializer.is_valid(raise_exception=True):
                            customer_serializer.save()

                            request.data[field]['id'] = customer_serializer.data['id']


                if 'id' in request.data[field]:
                    request.data[field] = request.data[field]['id']
                    
        logger.debug(request.data)
        
        
        for index, item in enumerate(request.data['items']):
            try:
                request.data['items'][index]['item'] = item['id']
                del request.data['items'][index]['id']
            except KeyError as e:
                logger.warn(e)
        
        try:                
            request.data['customer'] = Acknowledgement.objects.get(pk=request.data['acknowledgement']).customer.id
        except Exception:
            pass

        return request

    def _format_primary_key_data_for_put(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        project = None
        room = None
        fields = ['acknowledgement', 'project', 'phase', 'customer', 'items']
        
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
    
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        
        return super(ShippingList, self).post(request, *args, **kwargs)
        
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
        queryset = queryset.prefetch_related('items',)
            
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
    
    def put(self, request, *args, **kwargs):
        
        request = self._format_primary_key_data_for_put(request)

        return super(ShippingDetail, self).put(request, *args, **kwargs)
    
    
"""
@login_required
def shipping(request, shipping_id=0):
    #Get Request
    if request.method == "GET":
        
        if shipping_id ==  0:
            GET_data = request.GET
            data = []
            shippings = Shipping.objects.all().order_by('-id')
            if "last_modified" in GET_data:
                timestamp = dateutil.parser.parse(GET_data["last_modified"])
                shippings = shippings.filter(last_modified__gte=timestamp)
            for shipping in shippings:
                data.append(shipping.get_data())
            response = HttpResponse(json.dumps(data), mimetype="application/json")
            return response

        else:

            shipping = Shipping.objects.get(id=shipping_id)

            response = HttpResponse(json.dumps(shipping.get_data()), mimetype="application/json")
            return response

    if request.method == "POST":
        data = json.loads(request.body)
        shipping = Shipping()
        urls = shipping.create(data, user=request.user)
        data = urls.update(shipping.get_data())
        return HttpResponse(json.dumps(urls), mimetype="application/json")


@login_required
def pdf(request, shipping_id):
    shipping = Shipping.objects.get(id=shipping_id)
    data = {'url': shipping.pdf.generate_url()}
    return HttpResponse(json.dumps(data),
                            mimetype="application/json")


#Get url
@login_required
def acknowledgement_url(request, ack_id=0):
    if ack_id != 0 and request.method == "GET":
        ack = Acknowledgement.object.get(id=ack_id)


@login_required
def acknowledgement_item_image(request):
    if request.method == "POST":
        image = request.FILES['image']
        filename = settings.MEDIA_ROOT + str(time.time()) + '.jpg'
        with open(filename, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        #start connection
        conn = S3Connection()
        #get the bucket
        bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = "acknowledgement/item/image/%f.jpg" % (time.time())
        #upload file
        k.set_contents_from_filename(filename)
        #remove file from the system
        os.remove(filename)
        #set the Acl
        k.set_canned_acl('private')
        #set Url, key and bucket
        data = {
                'url': k.generate_url(300, force_http=True),
                'key': k.key,
                'bucket': 'media.dellarobbiathailand.com'
        }
        #self.save()
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
"""