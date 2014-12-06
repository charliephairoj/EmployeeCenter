from io import BytesIO
import logging
from decimal import Decimal

from rest_framework import viewsets
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from contacts.models import Supplier
from supplies.models import Supply, Fabric, Log, Product
from supplies.PDF import SupplyPDF
from auth.models import S3Object
from supplies.serializers import SupplySerializer, FabricSerializer, LogSerializer



logger = logging.getLogger(__name__)


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
    
    def pre_save(self, obj, *args, **kwargs):
        """
        Override the 'pre_save' method
        """
        try:
            if obj.pk:
                self._apply_quantity(obj, self.request.DATA['quantity'])
        except KeyError:
            pass
    
    def post_save(self, obj, created=False, *args, **kwargs):
        if "supplier" in self.request.DATA:
            supplier = Supplier.objects.get(pk=self.request.DATA['supplier'])
            try:
                product = Product.objects.get(supply=obj, supplier=supplier)
            except Product.DoesNotExist:
                product = Product(supply=obj, supplier=supplier)
                
            for field in ['cost', 'reference', 'purchasing_units', 'quantity_per_puchasing_units', 
                          'upc']:
                try:
                    setattr(product, field, self.request.DATA[field])
                except KeyError:
                    pass
                    
            product.save()
            
    def _apply_quantity(self, obj, new_quantity):
        """
        Internal method to apply the new quantity to the obj and
        create a log of the quantity change
        """
        new_quantity = Decimal(str(new_quantity))
        
        #Type change to ensure that calculations are only between Decimals
        obj.quantity = Decimal(str(obj.quantity))
        
        if new_quantity < 0:
            raise ValueError('Quantity cannot be negative')
            
        if new_quantity != obj.quantity:
            if new_quantity > obj.quantity:
                action = 'ADD'
                diff = new_quantity - obj.quantity
            elif new_quantity < obj.quantity:
                action = 'SUBTRACT'
                diff = obj.quantity - new_quantity
            
            #Create log to track quantity changes
            log = Log(supply=obj, 
                      action=action,
                      quantity=diff,
                      message=u"{0}ed {1}{2} {3} {4}".format(action.capitalize(),
                                                             diff,
                                                             obj.units,
                                                             "to" if action == "ADD" else "from",
                                                             obj.description))
             
            #Set new quantity
            obj.quantity = new_quantity
            
            #Save log                                               
            log.save()
            
            
        
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['supplier']
        
        for field in fields:
            if field in request.DATA:
                if 'id' in request.DATA[field]:
                    request.DATA[field] = request.DATA[field]['id']
                
        return request
    
    
class SupplyList(SupplyMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        request = self._format_primary_key_data(request)
        response = super(SupplyList, self).post(request, *args, **kwargs)
        
        return response
        
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
        
        #Filter based on supplier
        s_id = self.request.QUERY_PARAMS.get('supplier_id', None)
        if s_id:
            queryset = queryset.filter(products__supplier_id=s_id)
        
        #Filter based on product upc code
        upc = self.request.QUERY_PARAMS.get('upc', None)
        if upc:
            queryset = queryset.filter(product__upc=upc).distinct('product__upc')

        return queryset.distinct()
        
    
    

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
    

class FabricList(SupplyList):
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer
    

class FabricDetail(SupplyDetail):
    queryset = Fabric.objects.all()
    serializer_class = FabricSerializer
            
    
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
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    
    def get_queryset(self):
        
        queryset = self.queryset
        
        supply_id = self.request.QUERY_PARAMS.get('supply', None)

        if supply_id:
            queryset = queryset.filter(supply_id=supply_id)
            
        action = self.request.QUERY_PARAMS.get('action', None)

        if supply_id:
            queryset = queryset.filter(action=action)
            
        return queryset
