import logging

from rest_framework import serializers
from django.contrib.auth.models import Permission, Group

from administrator.models import User


logger = logging.getLogger(__name__)


class PermissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    
    class Meta:
        model = Permission
        fields = ('id', 'codename', 'name')
        
    def to_representation(self, instance):
        
        ret = super(PermissionSerializer, self).to_representation(instance)
        
        ret['content_type'] = instance.content_type.app_label
        
        return ret
    
        
class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, required=False)
    name = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = Group
        fields = ['id', 'permissions', 'name']
        
    def create(self, validated_data):
        perms = validated_data.pop('permissions', [])
        
        instance = self.Meta.model.objects.create(**validated_data)
        
        return instance
        
    def update(self, instance, validated_data):
        client_permissions = validated_data.pop('permissions', [])
        logger.debug(client_permissions)
        server_permissions = instance.permissions.all()
        id_list = [perm['id'] for perm in client_permissions]
        logger.debug(id_list)
        
        #Add New permissions
        for client_perm in client_permissions:
            instance.permissions.add(Permission.objects.get(pk=client_perm['id']))
            id_list.append(client_perm['id'])
            
        #Remove 
        for perm in server_permissions:
            if perm.id not in id_list:
                instance.permissions.remove(perm)
                
        return instance
        
             
class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'groups', 'id', 'last_login']
        depth = 1
    
    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password')
        
        instance = self.Meta.model.objects.create(**validated_data)
        instance.set_password(password)
        instance.save()
        
        assert instance.check_password(password)
        assert instance.has_usable_password()
        
        for group_data in groups:
            instance.groups.add(Group.objects.get(pk=group_data['id']))
            
        return instance
        
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
        
        


        
