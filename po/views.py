# Create your views here.

import json
import logging
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.db import connection
from django.db.models import Q
from django.conf import settings
from rest_framework import generics
from rest_framework.renderers import JSONRenderer
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required

from po.serializers import PurchaseOrderSerializer
from po.models import PurchaseOrder
from supplies.models import Supply, Product
from projects.models import Project, Room, Phase
from utilities.http import save_upload
from media.models import S3Object
from media.serializers import S3ObjectSerializer


logger = logging.getLogger(__name__)


@login_required
def item_image(request, po_id=None):

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

        if po_id:
            key = u"purchase_order/{0}/item/image/{1}".format(po_id, filename.split('/')[-1])
        else: 
            key = u"purchase_order/item/image/{0}".format(filename.split('/')[-1])

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
def po_file(request, po_id=None):

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

        if po_id:
            key = u"purchase_order/{0}/files/{1}".format(po_id, filename.split('/')[-1])
        else: 
            key = u"purchase_order/files/{0}".format(filename.split('/')[-1])
        
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
    

@csrf_exempt
def purchase_order_approval(request):

    if request.method.lower() == 'get':
        query_params = request.GET

        po_id = query_params.get('id')
        approval_pass = query_params.get('pass')
        
        try:
            po = PurchaseOrder.objects.get(pk=po_id)
        except PurchaseOrder.DoesNotExist as e:
            response = HttpResponse(json.dumps({'message':'unauthorized'}),
                            content_type="application/json")
            response.status_code = 404
            return response
        
        if po.approve(approval_pass):
            po.email_requester()
            message = "PO # {0} approved.".format(po.id)
            response = HttpResponse(json.dumps({'message': message}),
                            content_type="application/json")
            response.status_code = 201
        else:
            response = HttpResponse(json.dumps({'message':'unauthorized'}),
                            content_type="application/json")
            response.status_code = 404
    else: 
        response = HttpResponse(json.dumps({'message':'unauthorized'}),
                            content_type="application/json")
        response.status_code = 404
    
    return response

def purchase_order_stats(request):
    cursor = connection.cursor()
    query = """
    SELECT (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'processed') AS processed_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'processed') AS processed_sum,
    (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'received') AS received_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'received') AS received_sum,
    (SELECT COUNT(id)
    FROM po_purchaseorder where lower(status) = 'paid') AS paid_count,
    (SELECT SUM(total)
    FROM po_purchaseorder where lower(status) = 'paid') AS paid_sum,
    COUNT(id) AS total_count,
    SUM(total) AS total_sum
    FROM po_purchaseorder
    WHERE lower(status) != 'cancelled';
    """
    
    cursor.execute(query)
    row = cursor.fetchone()

    data = {'processed': {'count': row[0], 'amount': str(row[1])},
            'received': {'count': row[2], 'amount': str(row[3])},
            'paid': {'count': row[4], 'amount': str(row[5])},
            'total': {'count': row[6], 'amount': str(row[7])}}
    
    response = HttpResponse(json.dumps(data),
                            content_type="application/json")
    response.status_code = 200
    return response
    

class PurchaseOrderMixin(object):
    queryset = PurchaseOrder.objects.all().order_by('-id')
    serializer_class = PurchaseOrderSerializer

    def handle_exception(self, exc):
        """
        Custom Exception Handler

        Exceptions are logged as error via logging,
        which will send an email to the system administrator
        """
        logger.error(exc)
        
        return super(PurchaseOrderMixin, self).handle_exception(exc)
        
        
class PurchaseOrderList(PurchaseOrderMixin, generics.ListCreateAPIView):
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.exclude(status='cancelled')
        od = datetime.now() - timedelta(30)
        queryset = queryset.exclude(status="Processed", order_date__lte=od)
        rd = datetime.now() - timedelta(30)
        queryset = queryset.exclude(status="CLOSED", order_date__lte=rd)
        
        # Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(supplier__name__icontains=query) |
                                       Q(pk__icontains=query) |
                                       Q(items__description__icontains=query))
            queryset = queryset.distinct('id')
                                       
        # Filter by project
        project_id = self.request.query_params.get('project_id', None)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        # Last modified
        last_modified = self.request.query_params.get('last_modified', None)
        if last_modified:
            queryset = queryset.filter(last_modified__gte=last_modified)
                                      
        offset = int(self.request.query_params.get('offset', 0))
        settings_paginate_by = settings.REST_FRAMEWORK['PAGINATE_BY']
        limit = self.request.query_params.get('limit', settings_paginate_by)
        limit = int(limit)
        
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]
            

        queryset = queryset.select_related('supplier',
                                           'project',
                                           'room',
                                           'phase', 
                                           'pdf', 
                                           'auto_print_pdf',
                                           'deposit_document',
                                           'balance_document',
                                           'acknowledgement')
        queryset = queryset.prefetch_related('items',
                                             'logs',
                                             'items__supply',
                                             'items__supply__image',
                                             #'items__supply__product',
                                             'project__rooms',
                                             'project__phases',
                                             'project__rooms__files',
                                             'supplier__addresses')
        return queryset
        
    def get_paginate_by(self):
        """
        
        """
        settings_paginate_by = settings.REST_FRAMEWORK['PAGINATE_BY']
        limit = self.request.query_params.get('limit', settings_paginate_by)
        limit = int(limit)
        
        return self.queryset.count() if limit == 0 else limit


class PurchaseOrderDetail(PurchaseOrderMixin,
                          generics.RetrieveUpdateDestroyAPIView):

    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset.all()
                
        queryset = queryset.select_related('supplier',
                                           'project',
                                           'room',
                                           'phase', 
                                           'pdf', 
                                           'auto_print_pdf',
                                           'deposit_document',
                                           'balance_document',
                                           'acknowledgement')
        queryset = queryset.prefetch_related('items',
                                             'files',
                                             'logs',
                                             'logs__user',
                                             'items__supply',
                                             'items__supply__image',
                                             #'items__supply__product',
                                             'project__rooms',
                                             'project__phases',
                                             'project__rooms__files',
                                             'supplier__addresses')
        
        return queryset
