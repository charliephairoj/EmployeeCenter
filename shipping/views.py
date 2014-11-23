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

from shipping.models import Shipping
from shipping.serializers import ShippingSerializer
from acknowledgements.models import Acknowledgement


logger = logging.getLogger(__name__)


class ShippingMixin(object):
    queryset = Shipping.objects.all()
    serializer_class = ShippingSerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['acknowledgement']
        
        for field in fields:
            if field in request.DATA:
                if 'id' in request.DATA[field]:
                    logger.debug(request.DATA[field])
                    request.DATA[field] = request.DATA[field]['id']
                
        for index, item in enumerate(request.DATA['items']):
            logger.debug(item)
            logger.debug(request.DATA['items'][index])
            request.DATA['items'][index]['item'] = item['id']
            del request.DATA['items'][index]['id']
                        
        request.DATA['customer'] = Acknowledgement.objects.get(pk=request.DATA['acknowledgement']).customer.id
        return request
    
    
class ShippingList(ShippingMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        logger.debug(request.__dict__)
        logger.debug(request.DATA)
        request = self._format_primary_key_data(request)
        
        return super(ShippingList, self).post(request, *args, **kwargs)
    
        
    def pre_save(self, obj):
        obj.employee = self.request.user
        
        return obj
        
    def post_save(self, obj, *args, **kwargs):
        obj.create_and_upload_pdf()
        
        return obj
        
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(products__supplier__name__icontains=query) | 
                                       Q(description__icontains=query) |
                                       Q(products__reference__icontains=query))
                                      
        return queryset
        
        
class ShippingDetail(generics.RetrieveUpdateDestroyAPIView):
    pass
    
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