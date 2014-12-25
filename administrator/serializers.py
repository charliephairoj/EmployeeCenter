import logging

from rest_framework import serializers
from django.contrib.auth.models import Permission, Group

from administrator.models import User


logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        field = ['email']
