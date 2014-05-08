"""
Project views
"""
import json
import time

from django.http import HttpResponse

from projects.models import Project, Room, Item
from utilities.http import process_api, save_upload
from auth.models import S3Object


def project(request, project_id=0):
    return process_api(request, Project, project_id)


def room(request, room_id=0):
    return process_api(request, Room, room_id)


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


def item(request, item_id=0):
    return process_api(request, Item, item_id)


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
    
    
    