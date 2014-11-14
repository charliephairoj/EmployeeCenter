import logging

from rest_framework import viewsets, status
from rest_framework import generics
from rest_framework.response import Response
from django.db import transaction

from acknowledgements.models import Acknowledgement, Item, Pillow
from acknowledgements.serializers import AcknowledgementSerializer, ItemSerializer
from contacts.serializers import CustomerSerializer
from contacts.models import Customer
from projects.models import Project


logger = logging.getLogger(__name__)


class AcknowledgementMixin(object):
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    
        
class AcknowledgementList(AcknowledgementMixin,generics.ListCreateAPIView):
    
    def post(self, request):
        
        #Create project if necessary
        if "project" in request.DATA:
            if "codename" in request.DATA['project']:
                project = Project(codename=request.DATA['project']['codename'])
                project.save()
                request.DATA['project'] = project.id
                
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

        return super(AcknowledgementList, self).post(request)
        
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
        logger.debug(obj.items.all())
        obj.calculate_totals()
        
        #obj.create_and_upload_pdfs()
    

class AcknowledgementDetail(AcknowledgementMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Acknowledgement.objects.all()
    serializer_class = AcknowledgementSerializer
    paginate_by = 10
    
    
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