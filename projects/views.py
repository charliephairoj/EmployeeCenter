"""
Project views
"""
import json
import time

from django.http import HttpResponse
from django.conf import settings
from rest_framework import generics
from rest_framework.response import Response

from projects.models import Project, Room, Item
from projects.serializers import ProjectSerializer, RoomSerializer
from utilities.http import process_api, save_upload
from auth.models import S3Object


class ProjectMixin(object):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class ProjectList(ProjectMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = self.queryset
        
        #Filter based on query
        query = self.request.QUERY_PARAMS.get('q', None)
        if query:
            queryset = queryset.filter(Q(codename__icontains=query) | 
                                       Q(pk__icontains=query))
                                      
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
            
        return queryset
    
    
class ProjectDetail(ProjectMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def get(self, request, pk, format=None):
            project = self.get_object()
            serializer = ProjectSerializer(project, context={'pk':pk})
            return Response(serializer.data)
    
    
class RoomMixin(object):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer


class RoomList(RoomMixin, generics.ListCreateAPIView):
    pass
    

class RoomDetail(RoomMixin, generics.RetrieveUpdateDestroyAPIView):
    pass
    
    
def room_image(request):
    """
    Uploads the file in the request
    """
    if request.method.lower() == 'post':

        filename = save_upload(request)
        obj = S3Object.create(filename,
                        'project/room/image/{0}.jpg'.format(time.time()),
                        'media.dellarobbiathailand.com')

        return HttpResponse(json.dumps({'id': obj.id,
                                        'url': obj.generate_url()}),
                            mimetype='application/json',
                            status=201)
    else:
        return HttpResponse(status=401, mimetype="plain/text")


def item_schematic(request, schematic_id=0):
    """
    Handles uploading item_schematic
    """
    filename = save_upload(request)
    try:
        schematic = S3Object.objects.get(pk=schematic_id)
    except S3Object.DoesNotExist:
        try:
            obj_id = request.POST.get('id')
            schematic = S3Object.objects.get(pk=obj_id)
        except:
            key = 'project/item/schematic/{0}.jpg'.format(time.time())

            schematic = S3Object.create(filename,
                                        key,
                                        'media.dellarobbiathailand.com',
                                         encrypt_key=True)
    return HttpResponse(json.dumps(schematic.dict()),
                        mimetype='application/json',
                        status=201)
    
    
    