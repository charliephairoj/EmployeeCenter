from io import BytesIO
import logging

from rest_framework import viewsets
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required

from supplies.models import Supply, Fabric, Log
from supplies.PDF import SupplyPDF
from auth.models import S3Object
from supplies.serializers import SupplySerializer, FabricSerializer, LogSerializer



logger = logging.getLogger('EmployeeCenter')


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
    




class SupplyViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view and edit supplies
    """
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer
    

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
    
