from rest_framework import serializers

from supplies.serializers import SupplySerializer
from acknowledgements.serializers import ItemSerializer
from projects.models import Project, Room


class ProjectSerializer(serializers.ModelSerializer):
    #supplies = SupplySerializer(read_only=True, many=True)
    
    class Meta:
        model = Project
        field = ('id', 'codename')
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method
        """
        ret = super(ProjectSerializer, self).to_representation(instance)
        
        if 'pk' in self.context:
            ret['items'] = []
            for acknowledgement in instance.acknowledgements.all():
                ret['items'] += [ItemSerializer(item).data for item in acknowledgement.items.all()]
        
        return ret
    
class RoomSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Room
        field = ('id', 'description', 'reference')