import logging

from rest_framework import serializers

from accounting.models import Account
from hr.models import Employee
from media.models import S3Object
from media.serializers import S3ObjectSerializer


logger = logging.getLogger(__name__)

        
class AccountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(required=False, allow_null=True)
    name_en = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    name_th = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    type = serializers.CharField(required=False, allow_null=True)
 
    
    class Meta:
        fields = '__all__'
        model = Account
    
    