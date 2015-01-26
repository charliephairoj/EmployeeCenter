import logging

from rest_framework import generics

from equipment.models import Equipment
from equipment.serializers import EquipmentSerializer

logger = logging.getLogger(__name__)


class EquipmentMixin(object):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    

class EquipmentList(EquipmentMixin, generics.ListCreateAPIView):
    pass
    
    
class EquipmentDetail(EquipmentMixin, generics.RetrieveUpdateDestroyAPIView):
    pass