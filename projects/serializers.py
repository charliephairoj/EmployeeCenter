import logging

from rest_framework import serializers

from supplies.serializers import SupplySerializer
from projects.models import Project, Phase, Room, Item, File, ItemSupply, Part, ProjectSupply
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


class PhaseFieldSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Phase
        fields = ('id', 'quantity', 'description', 'due_date')
        depth = 0
        

class ProjectSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    supplies = serializers.ListField(child=serializers.DictField(), write_only=True, allow_null=True,
                                     required=False)
    files = serializers.ListField(child=serializers.DictField(), write_only=True, allow_null=True,
                                     required=False)
    codename = serializers.CharField(allow_blank=True)
    #phases = PhaseSerializer(many=True)
    
    class Meta:
        model = Project
        fields = ('id', 'codename', 'rooms', 'quantity', 'phases', 'supplies', 'status', 'website', 'files')
        depth = 1
        
    def to_representation(self, instance):
        """
        Override the 'to_representation' method
        """
        ret = super(ProjectSerializer, self).to_representation(instance)
        """
        if 'pk' in self.context:
            ret['items'] = []
            for acknowledgement in instance.acknowledgements.all():
                ret['items'] += [AckItemSerializer(item).data for item in acknowledgement.items.all()]
        """

        try:
            ret['files'] = [{'id':f.file.id,
                            'web_active': f.web_active,
                            'primary': f.primary,
                            'url':f.generate_url()} for f in instance.files.all()]     
        except AttributeError as e:
            ret['files'] = []
        #ret['supplies'] = [self._serialize_supply(supply, instance) for supply in instance.supplies.all()]
        
        return ret
        
    def create(self, validated_data):
        """
        Create
        """
        supplies = validated_data.pop('supplies', [])
        files = validated_data.pop('files', [])
        
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        self._create_or_update_supplies(supplies, instance)

        #Update attached files
        for f_data in files:
            try: 
                file = File.objects.get(file_id=f_data['id'], project=instance)
            except File.DoesNotExist:
                file = File.objects.create(file=S3Object.objects.get(pk=f_data['id']),
                                    project=instance)

            file.web_active = f_data.get('web_active', file.web_active)
            file.primary = f_data.get('primary', file.primary)
            file.save()
        
        return instance
        
    def update(self, instance, validated_data):
        """
        Update
        """
        supplies = validated_data.pop('supplies', [])
        logger.debug(validated_data)
        #Update attached files
        files = validated_data.pop('files', [])

        id_list = [f['id'] for f in files]

        # Add of create new files
        for f_data in files:
            try: 
                file = File.objects.get(file_id=f_data['id'], project=instance)
            except File.DoesNotExist:
                file = File.objects.create(file=S3Object.objects.get(pk=f_data['id']),
                                           project=instance)

            file.web_active = f_data.get('web_active', file.web_active)
            file.primary = f_data.get('primary', file.primary)
            file.save()

        for f in instance.files.all():
            if f.id not in id_list:
                File.objects.get(file=f, project=instance).delete()
        
        self._create_or_update_supplies(supplies, instance)
        
        return super(ProjectSerializer, self).update(instance, validated_data)
        
    def _create_or_update_supplies(self, supplies, project):
        #Create or update new supplies
        id_list = [supply['id'] for supply in supplies]
        
        for supply_data in supplies:
            try:
                project_supply = ProjectSupply.objects.get(supply=Supply.objects.get(pk=supply_data['id']),
                                                project=project)
            except ProjectSupply.DoesNotExist:
                project_supply = ProjectSupply.objects.create(supply=Supply.objects.get(pk=supply_data['id']),
                                                        project=project)
                id_list.append(project_supply.supply.id)
                
            project_supply.quantity = supply_data.get('quantity', project_supply.quantity)
            project_supply.save()
            
        #Remove delete supplies
        for supply in project.supplies.all():
            if supply.id not in id_list:
                ProjectSupply.objects.get(supply=supply, project=project).delete()
                
    def _serialize_supply(self, supply, project):
        ret = {'id': supply.id,
               'description': supply.description}
               
        ret['quantity'] = ProjectSupply.objects.get(supply=supply, project=project).quantity
        
        logger.debug(self.context)
        
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            ret['image'] = {'url': supply.image.generate_url(key, secret)}
        except AttributeError:
            pass
            
        return ret


class ProjectFieldSerializer(serializers.ModelSerializer):
    codename = serializers.CharField(required=True, allow_null=True, allow_blank=True)

    class Meta:
        model = Project
        fields = ('id', 'codename', 'quantity', 'status')
        depth = 0

                
class RoomSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    reference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    files = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                  allow_null=True)
    
    class Meta:
        model = Room
        fields = ('id', 'description', 'reference', 'files', 'project', 'items', 'floor')
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
        
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            ret['files'] = [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url(key, secret)} for file in instance.files.all()]
        except AttributeError:
            pass

        return ret


class RoomFieldSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Room
        fields = ('id', 'description', 'reference', 'floor')

        
class ItemSerializer(serializers.ModelSerializer):
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    supplies = serializers.ListField(child=serializers.DictField(), write_only=True, allow_null=True,
                                     required=False)
    files = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                  allow_null=True) 
    parts = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                  allow_null=True)
                                  
    class Meta:
        model = Item
        fields = ('id', 'room', 'supplies', 'description', 'reference', 'quantity', 'status', 'files',
                  'parts')
    
    def create(self, validated_data):
        
        supplies = validated_data.pop('supplies', [])
        files = validated_data.pop('files', [])
        parts = validated_data.pop('parts', [])
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        for supply in supplies:
            ItemSupply.objects.create(supply=Supply.objects.get(pk=supply['id']),
                                      item=instance, quantity=supply['quantity'])
                                      
        for file in files:
            File.objects.create(file=S3Object.objects.get(pk=file['id']), item=instance)
            
        for part in parts:
            del part['item']
            Part.objects.create(item=instance, **part)
                                      
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
        parts = validated_data.pop('parts', [])
        
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
        logger.debug(parts)                 
        #Add a Part
        for part_data in parts:
            try:
                part = Part.objects.get(pk=part_data['id'])
                part.quantity = part_data['quantity']
            except (KeyError, Part.DoesNotExist):
                del part_data['item']
                part = Part.objects.create(**part_data)
                        
        return instance
        
    def to_representation(self, instance):
        
        ret = super(ItemSerializer, self).to_representation(instance)
        
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        ret['supplies'] = [{'id': supply.id,
                            'description': supply.description,
                            'quantity': ItemSupply.objects.get(item=instance, supply=supply).quantity,
                            'url': self._get_image_from_supply(supply),
                            'units': supply.units}
                           for supply in instance.supplies.all(key, secret)]
                           
        try:
            ret['files'] = [{'id': file.id,
                             'filename': file.key.split('/')[-1],
                             'type': file.key.split('.')[-1],
                             'url': file.generate_url(key, secret)} for file in instance.files.all()]
        except AttributeError:
            pass
            
        try:
            ret['parts'] = [{'id': part.id,
                             'description': part.description,
                             'quantity': part.quantity} for part in instance.parts.all()]
        except AttributeError:
            pass
                           
        return ret
            
    def _get_image_from_supply(self, supply):
        """
        Returns the image url from the supply if there is an image
        """
        iam_credentials = self.context['request'].user.aws_credentials
        key = iam_credentials.access_key_id
        secret = iam_credentials.secret_access_key
        
        try:
            return supply.image.generate_url(key, secret)
        except AttributeError:
            return None
            

class PartSerializer(serializers.ModelSerializer):
    #item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    
    class Meta:
        model = Part
        fields = ('id', 'description', 'item', 'quantity')
        depth = 0
    
        
        
        
        
        
        
        
        
        
        
        
        
                                