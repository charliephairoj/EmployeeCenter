import logging

from rest_framework import serializers
from django.contrib.auth.models import Permission, Group

from administrator.models import User


logger = logging.getLogger(__name__)


class PermissionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Permission
        

class GroupSerializer(serializers.ModelSerializer):
    #permissions = PermissionSerializer(many=True)
    
    class Meta:
        model = Group
        
             
class UserSerializer(serializers.ModelSerializer):
    #groups = GroupSerializer(many=True)
    
    class Meta:
        model = User
        #depth = 1
        field = ['email']



        
