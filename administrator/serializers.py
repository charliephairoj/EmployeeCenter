import logging

from rest_framework import serializers
from django.contrib.auth.models import Permission, Group

from administrator.models import User


logger = logging.getLogger(__name__)


class PermissionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Permission
    
        
class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, required=False, read_only=True)
    name = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = Group
        fields = ['id', 'permissions', 'name']
        
             
class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'groups', 'id']
    
    def update(self, instance, validated_data):
        
        client_groups = validated_data.pop('groups', [])
        server_groups = instance.groups.all()
        id_list = [group['id'] for group in client_groups]
        
        #Add new groups
        for client_group in client_groups:
            instance.groups.add(Group.objects.get(pk=client_group['id']))
            
        #Delete groups
        for group in server_groups:
            if group.id not in id_list:
                instance.groups.remove(group)
        
        return instance
        
        


        
