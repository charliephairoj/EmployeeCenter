import logging

from rest_framework import serializers

from supplies.serializers import SupplySerializer
from acknowledgements.serializers import ItemSerializer as AckItemSerializer
from projects.models import Project, Phase, Room, Item, File, ItemSupply
from media.models import S3Object
from supplies.models import Supply


logger = logging.getLogger(__name__)


class FileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = File
        
        
class PhaseSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Phase
        fields = ('id', 'project', 'quantity', 'description', 'due_date')
        depth = 0
        

class ProjectSerializer(serializers.ModelSerializer):
    #supplies = SupplySerializer(read_only=True, many=True)
    #phases = PhaseSerializer(many=True)
    
    class Meta:
        model = Project
        fields = ('id', 'codename', 'rooms', 'quantity', 'phases')
        depth = 1
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method
        """
        ret = super(ProjectSerializer, self).to_representation(instance)
        
        if 'pk' in self.context:
            ret['items'] = []
            for acknowledgement in instance.acknowledgements.all():
                ret['items'] += [AckItemSerializer(item).data for item in acknowledgement.items.all()]
        
        return ret
        
    
class RoomSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    reference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    files = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                  allow_null=True)
    
    class Meta:
        model = Room
        fields = ('id', 'description', 'reference', 'files', 'project', 'items')
        depth = 2
        
    def create(self, validated_data):
        """
        Implementing the create method
        
        We extract the files attribute from validated_data. Added added files
        to list of associated files with the room
        """
        files = validated_data.pop('files', [])
        instance = self.Meta.model.objects.create(**validated_data)
        
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']), room=instance)
            
        return instance
    
    def update(self, instance, validated_data):
        """
        Implementing the update method
        
        We extract the files attribute from validated_data. Added added files
        to list of associated files with the room
        """
        #Update attached files
        files = validated_data.pop('files', [])
        for file in files:
            try: 
                file = File.objects.get(file_id=file['id'], room=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                    room=instance)
                                            
        return instance
        
    def to_representation(self, instance):
        """
        Override the 'to_represenatation' method.
        
        We call the parent method in order to get the standard output.
        Then we add the associated files with the room
        """
        ret = super(RoomSerializer, self).to_representation(instance)
        
        ret['items'] = [ItemSerializer(item).data for item in instance.items.all()]
        
        logger.debug('ok')
        
        try:
            ret['files'] = [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url()} for file in instance.files.all()]
        except AttributeError:
            pass

        return ret
        
        
class ItemSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    supplies = serializers.ListField(child=serializers.DictField(), write_only=True, allow_null=True,
                                     required=False)
    files = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                  allow_null=True)
    
    class Meta:
        model = Item
        fields = ('id', 'room', 'supplies', 'description', 'reference', 'quantity', 'status', 'files')
        
    def create(self, validated_data):
        
        supplies = validated_data.pop('supplies', [])
        files = validated_data.pop('files', []);
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        for supply in supplies:
            ItemSupply.objects.create(supply=Supply.objects.get(pk=supply['id']),
                                      item=instance, quantity=supply['quantity'])
                                      
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']), item=instance)
                                      
        return instance
        
    def update(self, instance, validated_data):
        """
        Implement 'update' method to update the Room Item resource
        
        We loop through the supply data to determine which supplies need to be associated or update.
        Then we loop through the supplies associated with the item, and compare to list of ids
        that the user provided. From this we determine which supply to disassociate
        """
        supplies = validated_data.pop('supplies', [])
        files = validated_data.pop('files', [])
        
        #List of ids not to delete
        id_list = [supply['id'] for supply in supplies]
        
        #Create or update new supplies
        for supply_data in supplies:
            try:
                item_supply = ItemSupply.objects.get(supply=Supply.objects.get(pk=supply_data['id']),
                                                item=instance)
            except ItemSupply.DoesNotExist:
                item_supply = ItemSupply.objects.create(supply=Supply.objects.get(pk=supply_data['id']),
                                                        item=instance)
                id_list.append(item_supply.supply.id)
                
            item_supply.quantity = supply_data.get('quantity', item_supply.quantity)
            item_supply.save()
            
        #Remove delete supplies
        for supply in instance.supplies.all():
            if supply.id not in id_list:
                ItemSupply.objects.get(supply=supply, item=instance).delete()
        
        #Add Files
        for file in files:
            try: 
                file = File.objects.get(file_id=file['id'], item=instance)
            except File.DoesNotExist:
                File.objects.create(file=S3Object.objects.get(pk=file['id']),
                                    item=instance)
        
        return instance
        
    def to_representation(self, instance):
        
        ret = super(ItemSerializer, self).to_representation(instance)
        
        ret['supplies'] = [{'id': supply.id,
                            'description': supply.description,
                            'quantity': ItemSupply.objects.get(item=instance, supply=supply).quantity,
                            'url': self._get_image_from_supply(supply),
                            'units': supply.units}
                           for supply in instance.supplies.all()]
                           
        try:
            ret['files'] = [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url()} for file in instance.files.all()]
        except AttributeError:
            pass
                           
        return ret
            
    def _get_image_from_supply(self, supply):
        """
        Returns the image url from the supply if there is an image
        """
        try:
            return supply.image.generate_url()
        except AttributeError:
            return None
            
            
    
        
        
        
        
        
        
        
        
        
        
        
        
                                