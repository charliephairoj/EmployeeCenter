"""
Project views
"""
from projects.models import Project, Room, Item
from utilities.http import process_api


def project(request, project_id=0):
    return process_api(request, Project, project_id)


def room(request, room_id=0):
    print room_id
    return process_api(request, Room, room_id)


def item(request, item_id=0):
    return process_api(request, Item, item_id)