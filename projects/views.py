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