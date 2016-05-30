from io import BytesIO
import logging
from decimal import Decimal
import json
import time

from rest_framework import viewsets
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Log, Product
from supplies.PDF import SupplyPDF
from utilities.http import save_upload
from auth.models import S3Object
from supplies.serializers import SupplySerializer, FabricSerializer, LogSerializer
from media.stickers import StickerPage, Sticker, FabricSticker


logger = logging.getLogger(__name__)


@login_required
def sticker(request, pk=None):
    response = HttpResponse(content_type='application/pdf; charset=utf-8')
    supply = Supply.objects.get(pk=pk)
    pdf = Sticker(code="DRS-{0}".format(supply.id), description=supply.description)
    pdf.create(response)

    return response


@login_required
def fabric_sticker(request, pk=None):
    response = HttpResponse(content_type='application/pdf; charset=utf-8')
    fabric = Fabric.objects.get(pk=pk)
    pdf = FabricSticker(fabric=fabric)
    pdf.create(response)

    return response


def supply_image(request):
    if request.method == "POST":
        credentials = request.user.aws_credentials
        key = credentials.access_key_id
        secret = credentials.secret_access_key

        filename = save_upload(request)
        obj = S3Object.create(filename,
                        "supply/image/{0}.jpg".format(time.time()),
                        'media.dellarobbiathailand.com',
                        key, secret)
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url(key, secret)}),
                                content_type="application/json")
        response.status_code = 201
        return response


@login_required
def shopping_list(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="supply-shopping-list.pdf"'
    buffer = BytesIO()

    pdf = SupplyPDF(filename=buffer)
    pdf.create()

    data = buffer.getvalue()
    buffer.close()
    response.write(data)
    return response


class SupplyMixin(object):
    queryset = Supply.objects.all().order_by('description')
    serializer_class = SupplySerializer

    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may
        work with DRF
        """
        fields = ['supplier', 'image', 'suppliers', 'sticker', 'employee']

        if type(request.data) == list:
            for index, data in enumerate(request.data):
                request.data[index] = self._format_individual_data(request.data[index])
        elif type(request.data) == dict:
            self._format_individual_data(request.data)

        return request

    def _format_individual_data(self, data):

        fields = ['supplier', 'image', 'suppliers', 'sticker', 'employee']

        for field in fields:
            if field in data:
                try:
                    if 'id' in data[field]:
                        data[field] = data[field]['id']
                except TypeError:
                    pass

                #format for supplier in suppliers list
                if field == 'suppliers':
                    for index, supplier in enumerate(data[field]):
                        try:
                            data[field][index]['supplier'] = supplier['supplier']['id']
                        except (KeyError, TypeError):
                            try:
                                data[field][index]['supplier'] = supplier['id']
                            except KeyError:
                                pass

        return data


class SupplyList(SupplyMixin, generics.ListCreateAPIView):

    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(SupplyList, self).post(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        return self.bulk_update(request, *args, **kwargs)

    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(products__supplier__name__icontains=query) |
                                       Q(description__icontains=query) |
                                       Q(products__reference__icontains=query))

        #Filter based on supplier
        s_id = self.request.query_params.get('supplier_id', None)
        if s_id:
            queryset = queryset.filter(products__supplier_id=s_id)

        #Filter based on product upc code
        upc = self.request.query_params.get('upc', None)
        if upc:
            queryset = queryset.filter(products__upc=upc)

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
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

    def bulk_update(self, request, *args, **kwargs):
        #partial = kwargs.pop('partial', False)

        # restrict the update to the filtered queryset
        serializer = SupplySerializer(Supply.objects.filter(id__in=[d['id'] for d in request.data]),
                                      data=request.data,
                                      context={'request': request, 'view': self},
                                      many=True)

        if serializer.is_valid(raise_exception=True):

            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SupplyDetail(SupplyMixin, generics.RetrieveUpdateDestroyAPIView):
    def put(self, request, *args, **kwargs):

        request = self._format_primary_key_data(request)
        response = super(SupplyDetail, self).put(request, *args, **kwargs)

        return response


class SupplyTypeList(viewsets.ModelViewSet):
    def type(self, request, *args, **kwargs):
        data = [s for s in Supply.objects.values_list('type', flat=True).distinct()]
        return Response(data=data, status=status.HTTP_200_OK)


supply_type_list = SupplyTypeList.as_view({
    'get': 'type'
})


class FabricMixin(object):
    queryset = Fabric.objects.all().order_by('description')
    serializer_class = FabricSerializer


class FabricList(FabricMixin, SupplyList):

    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all().order_by('status', 'pattern', 'color')

        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(products__supplier__name__icontains=query) |
                                       Q(description__icontains=query) |
                                       Q(products__reference__icontains=query) |
                                       Q(pattern__icontains=query) |
                                       Q(color__icontains=query))

        #Filter based on supplier
        s_id = self.request.query_params.get('supplier_id', None)
        if s_id:
            queryset = queryset.filter(products__supplier_id=s_id)

        #Filter based on product upc code
        upc = self.request.query_params.get('upc', None)
        if upc:
            queryset = queryset.filter(products__upc=upc)

        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', self.request.query_params.get('page_size', settings.REST_FRAMEWORK['PAGINATE_BY'])))

        if offset == 0 and limit == 0:
            queryset = queryset
        elif offset and limit:
            queryset = queryset[offset:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]

        return queryset


class FabricDetail(FabricMixin, SupplyDetail):
    pass


class FabricViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit models
    """
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer


class LogViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit upholstery
    """
    queryset = Log.objects.all().order_by('-id')
    serializer_class = LogSerializer

    def get_queryset(self):

        queryset = self.queryset.all()

        supply_id = self.request.query_params.get('supply', None)
        supply_id = self.request.query_params.get('supply_id', None) or supply_id

        if supply_id:
            queryset = queryset.filter(supply_id=supply_id)

        action = self.request.query_params.get('action', None)

        if action:
            queryset = queryset.filter(action=action)

        return queryset

    def update(self, request, *args, **kwargs):

        logger.debug(request)


class LogList(generics.ListAPIView):

    queryset = Log.objects.all().order_by('-id')
    serializer_class = LogSerializer

    def get_queryset(self):

        queryset = self.queryset.all()

        supply_id = self.request.query_params.get('supply', None)
        supply_id = self.request.query_params.get('supply_id', None) or supply_id

        if supply_id:
            queryset = queryset.filter(supply_id=supply_id)

        action = self.request.query_params.get('action', None)

        if action:
            queryset = queryset.filter(action=action)

        return queryset


class LogDetail(generics.RetrieveUpdateAPIView):

    queryset = Log.objects.all().order_by('-id')
    serializer_class = LogSerializer

    def put(self, request, *args, **kwargs):
        del request.data['supply']
        response = super(LogDetail, self).put(request, *args, **kwargs)

        return response
