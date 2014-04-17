"""
API file for all media models
"""
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization

from auth.models import S3Object


class S3ObjectResource(ModelResource):
    class Meta:
        queryset = S3Object.objects.all()
        resource_name = 's3object'
        authorization = Authorization()
        
    def dehydrate(self, bundle):
        """
        Implement the dehydrate method
        
        We add a uri to the actual file that is stored
        on the S3 system
        """
        bundle.data['url'] = bundle.obj.generate_url()
        
        return bundle