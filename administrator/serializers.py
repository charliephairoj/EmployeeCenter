import logging

from rest_framework import serializers
from django.contrib.auth.models import Permission, Group
from django.db import models
import boto
from django.conf import settings

from django.utils import timezone as tz

from administrator.models import User, AWSUser, Log, Label, Company


logger = logging.getLogger(__name__)


"""
Defaults 

Used for Serializer Field defaults
"""
class CompanyDefault(object):
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self.user = request.user

        if settings.DEBUG:
            self.user = User.objects.get(pk=1)

        self.company = self.user.company

    def __call__(self):
        return self.company


"""
Serializers
"""
class UserFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'id', 'last_login', 'is_active', 'web_ui_version')
        depth = 0


class BaseLogSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(default=serializers.CreateOnlyDefault(tz.now))
    type = serializers.CharField(default=serializers.CreateOnlyDefault('GENERAL'))
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    company = serializers.HiddenField(default=serializers.CreateOnlyDefault(CompanyDefault()))

    class Meta:
        model = Log
        depth = 1
        fields = ('id', 'message', 'timestamp', 'user', 'type', 'company')


class LabelSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Label
        fields = '__all__'


class LogSerializer(serializers.ModelSerializer):

    employee = UserFieldSerializer(source="user")
    
    class Meta:
        model = Log
        fields = ('id', 'message', 'timestamp', 'employee', 'type')


class LogListFieldSerializer(serializers.ListSerializer):
    """Serializer to filter the type of logs
      The value argument to to_representation() method is 
      the model instance"""
    def xto_representation(self, data):
        data = data.exclude(type__icontains="error").order_by('-timestamp').select_related('user')
        return super(LogListFieldSerializer, self).to_representation(data)


class LogFieldSerializer(serializers.ModelSerializer):

    employee = UserFieldSerializer(source="user")
    
    class Meta:
        model = Log
        list_serializer_class = LogListFieldSerializer
        fields = ('id', 'message', 'timestamp', 'employee', 'type')
        

class PermissionListSerializer(serializers.ListSerializer):

    def xto_internal_value(self, data):
        print "\n\nPerm List\n\n"
        logger.debug(data)
        return super(PermissionListSerializer, self).to_internal_value(data)

    def xto_representation(self, data):
        print "\n\nPerm List\n\n"
        logger.debug(isinstance(data, models.Manager))
        logger.debug(type(data))
        logger.debug(data)
        logger.debug(isinstance(data, models.Manager))
        data = data.prefetch_related('content_type')
        logger.debug(isinstance(data, models.Manager))
        ret = super(PermissionListSerializer, self).to_representation(data)
        #return data
        logger.debug(data)
        return ret

class PermissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    module = serializers.CharField(read_only=True, source="content_type.app_label")

    class Meta:
        model = Permission
        fields = ('id', 'codename', 'name', 'module')
        list_serializer_class = PermissionListSerializer


    def xto_internal_value(self, data):
        ret = super(PermissionSerializer, self).to_internal_value(data)        

        return ret
        
    def xto_representation(self, instance):
        
        ret = super(PermissionSerializer, self).to_representation(instance)
        
        ret['content_type'] = instance.content_type.app_label
        
        return ret
    
        
class GroupSerializer(serializers.ModelSerializer):
    perm_queryset = Permission.objects.all().prefetch_related('content_type')
    permissions = PermissionSerializer(data=perm_queryset, many=True, required=False)
    name = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)
    users = UserFieldSerializer(many=True, read_only=True, source="user_set")
    
    class Meta:
        model = Group
        fields = ('id', 'permissions', 'name', 'users')
        
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


class GroupFieldSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Group
        fields = ('id', 'name')


class CompanySerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Company
        fields = ('id', 'name')

             
class UserSerializer(serializers.ModelSerializer):
    groups = GroupFieldSerializer(many=True, required=False)
    #password = serializers.CharField(write_only=True, required=False)
    company = CompanySerializer(read_only=True)
    
    class Meta:
        model = User
        write_only_fields = ['password',]
        fields = ('email', 'username', 'first_name', 'last_name', 'groups', 
                  'id', 'last_login', 'is_active', 'web_ui_version', 'company')
        read_only_fields = ('company',)
        depth = 1
    
    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password')
        
        company = self.context['request'].user.company
        instance = self.Meta.model.objects.create(company=company, 
                                                  **validated_data)
        instance.set_password(password)
        instance.save()

        assert instance.check_password(password)
        assert instance.has_usable_password()

        # Create access and secret keys
        instance.access_key = instance.create_key()
        instance.secret_key = instance.create_key(instance.access_key)
        instance.save()
        
        assert instance.access_key
        assert instance.secret_key
        
        #Create the credentials for aws
        self._create_aws_credentials(instance)
        
        for group_data in groups:
            instance.groups.add(Group.objects.get(pk=group_data['id']))
            
        return instance
        
    def update(self, instance, validated_data):
        
        client_groups = validated_data.pop('groups', [])
        server_groups = instance.groups.all()
        id_list = [group['id'] for group in client_groups]
        user = self.context['request'].user
        
        #Add new groups
        for client_group in client_groups:
            instance.groups.add(Group.objects.get(pk=client_group['id']))
            
        #Delete groups
        for group in server_groups:
            if group.id not in id_list:
                instance.groups.remove(group)

        # Update and Log attributes that have changed
        update_fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'web_ui_version']
        for field in update_fields:
            data = validated_data.get(field, getattr(instance, field))
            current_data = getattr(instance, field)
            if data != current_data:
                message = "Changed {0} from {1} to {2}.".format(field, 
                                                                current_data, 
                                                                data)
                Log.objects.create(message=message, 
                                   type="ADMINISTRATION", 
                                   user=user)
                setattr(instance, field, data)

        instance.save()
        
        return instance

    def _create_aws_credentials(self, user):
        aws_user = AWSUser(user=user).save()
        
        iam = boto.connect_iam()
        
        response = iam.create_user(user.email)
        user.aws_credentials.iam_id = response.user.user_id
        
        # Add to S3 group
        response = iam.add_user_to_group('S3-Users', user.email)

        # Create AccessKey/SecretKey pair for User
        response = iam.create_access_key(user.email)
        user.aws_credentials.access_key_id = response.access_key_id
        user.aws_credentials.secret_access_key = response.secret_access_key
        
        user.aws_credentials.save()




        
