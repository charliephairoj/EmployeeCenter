#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Project views
"""
import json
import time
from datetime import datetime, timedelta
import logging

from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from rest_framework import viewsets
from rest_framework import generics
from rest_framework.response import Response
from django.utils.datastructures import MultiValueDictKeyError
from django.contrib.auth.decorators import login_required

from projects.models import Project, Room, Item, Phase, Part, File
from projects.serializers import ProjectSerializer, PhaseSerializer, RoomSerializer, ItemSerializer, PartSerializer
from utilities.http import process_api, save_upload
from auth.models import S3Object
from projects.PDF import ProjectPDF, PhasePDF


logger = logging.getLogger(__name__)


@permission_required('projects.view_project_report')
def report(request, pk):
    
    response = HttpResponse(content_type='application/pdf; charset=utf-8')
    
    pdf = ProjectPDF(project=Project.objects.get(pk=pk), user=request.user)
    pdf.create(response)
    
    return response
    

@permission_required('projects.view_phase_report')
def phase_report(request, pk):
    
    response = HttpResponse(content_type='application/pdf; charset=utf-8')
    
    pdf = PhasePDF(phase=Phase.objects.get(pk=pk), user=request.user)
    pdf.create(response)
    
    return response


def project_public(request):
    if request.method.lower() == "get":
        projects = Project.objects.filter(website=True).order_by('codename')
        projects = projects.prefetch_related('files')
        projects_data = [{'codename': project.codename,
                          'images': [img.file.generate_url(time=31560000) for img in File.objects.filter(web_active=True, 
                                                                                                    project=project).order_by('-primary')]}
                        for project in projects]
        response = HttpResponse(json.dumps(projects_data), 
                                content_type="application/json")
        response.status_code = 200
        return response


@login_required
def project_image(request):
    if request.method == "POST":
        try:
            filename = request.FILES['file'].name
        except MultiValueDictKeyError:
            filename = request.FILES['image'].name

        filename = save_upload(request, filename=filename)

        obj = S3Object.create(filename,
                        "project/image/{0}_{1}".format(time.time(), filename.split('/')[-1]),
                        'media.dellarobbiathailand.com')
                        
        
        response = HttpResponse(json.dumps({'id': obj.id,
                                            'url': obj.generate_url(),
                                            'key': obj.key,
                                            'bucket':obj.bucket}),
                                content_type="application/json")
        response.status_code = 201
        return response
    
    
class ProjectMixin(object):
    queryset = Project.objects.all().order_by('codename')
    serializer_class = ProjectSerializer


class ProjectList(ProjectMixin, generics.ListCreateAPIView):
    
    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = Project.objects.all()
        
        #Filter based on query
        query = self.request.query_params.get('q', None)
        if query:
            queryset = queryset.filter(Q(codename__icontains=query) | 
                                       Q(pk__icontains=query))
                                      
        status_exclusions = self.request.query_params.get('status__exclude', None)
        if status_exclusions:
            queryset = queryset.exclude(status__icontains=status_exclusions)
            
        # Exclude projects that are completed and order than 30 days
        d = datetime.now() - timedelta(days=30)
        try:
            queryset = queryset.exclude(status__icontains="completed", last_modified__lte=d, website=False)
        except Exception as e:
            queryset = queryset.exclude(status__icontains="completed", website=False)
        
        # Enfore ordering by codename    
        queryset = queryset.order_by('-website', '-id')
        
        offset = int(self.request.query_params.get('offset', 0))
        limit = int(self.request.query_params.get('limit', settings.REST_FRAMEWORK['PAGINATE_BY']))
        if offset and limit:
            queryset = queryset[offset - 1:limit + (offset - 1)]
        else:
            queryset = queryset[0:50]

        queryset = queryset.select_related('customer')
        queryset = queryset.prefetch_related('rooms',
                                             'phases',
                                             'rooms__files',
                                             'files',
                                             'customer__addresses',
                                             'acknowledgements',
                                             'acknowledgements__items',
                                             'acknowledgements__items__image',
                                             'purchase_orders')
                                             
        return queryset
    
    
class ProjectDetail(ProjectMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def get(self, request, pk, format=None):
            project = self.get_object()
            serializer = ProjectSerializer(project, context={'pk':pk})
            return Response(serializer.data)

    def get_queryset(self):
        """
        Override 'get_queryset' method in order to customize filter
        """
        queryset = Project.objects.all()

        queryset = queryset.select_related('customer')
        queryset = queryset.prefetch_related('rooms',
                                             'phases',
                                             'rooms__files',
                                             'files',
                                             'customer__addresses',
                                             'acknowledgements',
                                             'acknowledgements__items',
                                             'acknowledgements__items__image',
                                             'purchase_orders')

        return queryset
    

class PhaseViewSet(viewsets.ModelViewSet):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer
    
    
class RoomMixin(object):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['project']

        for field in fields:
            if field in request.data:
                try:
                    request.data[field] = request.data[field]['id']
                except (TypeError, KeyError) as e:
                    logger.warn(e)
        
        return request
        

class RoomList(RoomMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
        
        request = self._format_primary_key_data(request)
        
        return super(RoomList, self).post(request, *args, **kwargs)
    

class RoomDetail(RoomMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
        
        request = self._format_primary_key_data(request)
        
        return super(RoomDetail, self).put(request, *args, **kwargs)
    

class RoomItemMixin(object):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def _format_primary_key_data(self, request):
        """
        Format fields that are primary key related so that they may 
        work with DRF
        """
        fields = ['room']
        for field in fields:
            if field in request.data:
                try:
                    request.data[field] = request.data[field]['id']
                except (TypeError, KeyError) as e:
                    logger.warn(e)
        
        return request
        

class RoomItemList(RoomItemMixin, generics.ListCreateAPIView):
    
    def post(self, request, *args, **kwargs):
                
        request = self._format_primary_key_data(request)
        return super(RoomItemList, self).post(request, *args, **kwargs)
        
        
class RoomItemDetail(RoomItemMixin, generics.RetrieveUpdateDestroyAPIView):
    
    def put(self, request, *args, **kwargs):
                
        request = self._format_primary_key_data(request)
        
        return super(RoomItemDetail, self).put(request, *args, **kwargs)
    

class PartViewSet(viewsets.ModelViewSet):
    queryset = Part.objects.all()
    serializer_class = PartSerializer
    
    
def room_image(request):
    """
    Uploads the file in the request
    """
    if request.method.lower() == 'post':
        
        credentials = request.user.aws_credentials
        key = credentials.access_key_id
        secret = credentials.secret_access_key
        
        filename = save_upload(request)
        obj = S3Object.create(filename,
                        'project/room/image/{0}.jpg'.format(time.time()),
                        'media.dellarobbiathailand.com')

        return HttpResponse(json.dumps({'id': obj.id,
                                        'url': obj.generate_url(key, secret)}),
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
    
    
    