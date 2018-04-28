import logging

from rest_framework import serializers

from equipment.models import Equipment
from hr.models import Employee
from media.models import S3Object
from media.serializers import S3ObjectFieldSerializer


logger = logging.getLogger(__name__)


class EquipmentListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        """
        Implmement multiple update for equipment
        """
        ret = []
        
        #Update the quantity for each supply
        for data in validated_data:
            equipment = Equipment.objects.get(pk=data['id'])
    
            self.child.update(equipment, data)

            ret.append(equipment)

        return ret
        
        
class EquipmentSerializer(serializers.ModelSerializer):
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    employee = serializers.PrimaryKeyRelatedField(required=False,
                                                  queryset=Employee.objects.all())
    id = serializers.IntegerField(required=False)
    brand = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)
    image = S3ObjectFieldSerializer(allow_null=True, required=False)
    
    class Meta:
        fields = '__all__'
        model = Equipment
        list_serializer_class = EquipmentListSerializer
    
    def create(self, validated_data):
        print validated_data
        image_data = validated_data.pop('image', {})
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        try:
            instance.image = S3Object.objects.get(pk=image_data['id'])
        except KeyError:
            pass
        
        instance.save()
        
        return instance
        
    def update(self, instance, validated_data):
        
        instance = super(EquipmentSerializer, self).update(instance, validated_data)
        
        try:
            if instance.status.lower() == "checked in":
                instance.employee = None
        except AttributeError:
            instance.status = 'checked in'
            instance.employee = None
        
        
        try:
            instance.image = S3Object.objects.get(pk=validated_data['image']['id'])
        except (TypeError, KeyError):
            pass
            
        instance.save()
            
        return instance
        
    def to_representation(self, instance):
        """
        Override 'to_represenation' method
        """
        ret = super(EquipmentSerializer, self).to_representation(instance)
        
        try:
            ret['employee'] = {'id': instance.employee.id,
                               'first_name': instance.employee.first_name,
                               'last_name': instance.employee.last_name, 
                               'nickname': instance.employee.nickname}
        except AttributeError as e:
            pass
            
        try:
            ret['employee']['image'] = {'id': instance.employee.image.id,
                                        'url': instance.employee.image.generate_url()}
        except AttributeError as e:
            pass
            
        try:
            if ret['status'].lower() == 'checked in':
                del ret['employee']
        except AttributeError:
            pass
                           
        return ret
        
        