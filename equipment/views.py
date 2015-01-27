import logging

from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status

from equipment.models import Equipment
from equipment.serializers import EquipmentSerializer

logger = logging.getLogger(__name__)


class EquipmentMixin(object):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    
    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['employee']
        
        for field in fields:
            if field in request.data:
                if 'id' in request.data[field]:
                    request.data[field] = request.data[field]['id']
                   
        return request


class EquipmentList(EquipmentMixin, generics.ListCreateAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Implement 'put' for multiple batch update
        """
        
        if isinstance(request.data, list):
            for data in request.data:
                if "employee" in data:
                    try:
                        data['employee'] = data['employee']['id']
                    except KeyError as e:
                        logger.warn(e)
                        
        return self.bulk_update(request, *args, **kwargs)
    
    def bulk_update(self, request, *args, **kwargs):
        #partial = kwargs.pop('partial', False)

        # restrict the update to the filtered queryset
        serializer = EquipmentSerializer(Equipment.objects.filter(id__in=[d['id'] for d in request.data]),
                                         data=request.data,
                                         context={'request': request, 'view': self},
                                         many=True)
        
        if serializer.is_valid(raise_exception=True):
            
            serializer.save()
            
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class EquipmentDetail(EquipmentMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        """
        Override the 'put' method in order
        to populate fields
        """
        request = self._format_primary_key_data(request)
        
        return super(EquipmentDetail, self).put(request, *args, **kwargs)
        