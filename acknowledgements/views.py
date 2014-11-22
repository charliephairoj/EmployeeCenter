import logging
import time

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.db import transaction

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
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    
    def _condense_pillows(self, request):
        """
        Condense the pillows by combining pillows of the same type and fabric
        """
        #Condense pillow data
        for item in request.DATA['items']:
            #Sort pillows
            if "pillows" in item:
                pillows = {}
                for pillow in item['pillows']:
                    try:
                        fabric_id = pillow['fabric']
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
            if field in request.DATA:
                if 'id' in request.DATA[field]:
                    request.DATA[field] = request.DATA[field]['id']
                    
                if field == 'items':
                    for index, item in enumerate(request.DATA['items']):
                        try:
                            request.DATA['items'][index]['fabric'] = item['fabric']['id']
                        except (KeyError, TypeError):
                            pass
                            
                elif field == 'project':
                    try:
                        if "codename" in request.DATA['project'] and "id" not in request.DATA['project']:
                            project = Project(codename=request.DATA['project']['codename'])
                            project.save()
                            request.DATA['project'] = project.id
                    except TypeError:
                        pass
                   
        return request

        
class AcknowledgementList(AcknowledgementMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        """
        Override the 'post' method in order 
        to popular fields
        """
        request = self._format_primary_key_data(request)
        
        request = self._condense_pillows(request)
        
        return super(AcknowledgementList, self).post(request, *args, **kwargs)
                    
    def pre_save(self, obj):
        """
        Override the presave in order to assign the customer to the
        acknowledgement
        """
        
        #Assign the discount
        try:
            if (obj.customer.discount > 0 and 'discount' not in self.request.DATA) or int(self.request.DATA['discount']) == 0: 
                obj.discount = obj.customer.discount
        except KeyError as e:
            obj.discount = obj.customer.discount
            
        #Assign employee
        obj.employee = self.request.user
        
        #Calculate the acknowledgement totals
        obj.calculate_totals()
        
        return super(AcknowledgementMixin, self).pre_save(obj)
        
    def post_save(self, obj, *args, **kwargs):
        """
        Override post save in order to create the pdf
        """
        obj.calculate_totals()
        
        obj.create_and_upload_pdfs()
    

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
        data = request.DATA
        customer = self._get_customer(request.DATA['customer']['id'])
        serializer = self.get_serializer(data=request.DATA)
        
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