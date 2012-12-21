from supplies.models import Supply
from utilities.http import processRequest
import json
from django.http import HttpResponseRedirect, HttpResponse
import logging

logger = logging.getLogger('EmployeeCenter');

 
       
#Supplies
def supply(request, supply_id='0'):
    return processRequest(request, Supply, supply_id)
    
#fabric
def fabric(request, fabric_id=0):
    
    from supplies.models import Fabric
    
    return processRequest(request, Fabric, fabric_id)

#Add length to a fabric
def fabric_add(request, fabric_id):
    
    from supplies.models import Fabric
    
    user = request.user
    length = request.POST.get('length')
    remark = request.POST.get('remark')
    
    fabric = Fabric.objects.get(id=fabric_id)
    
    fabric.add(length, remark=remark, employee=user)
    
    response = HttpResponse(json.dumps(fabric.get_data()), mimetype="application/json")
    response.status_code = 200
    return response
    
#Subtracts length from a fabric
def fabric_subtract(request, fabric_id):
    
    from supplies.models import Fabric
    
    user = request.user
    length = request.POST.get('length')
    remark = request.POST.get('remark')
    
    fabric = Fabric.objects.get(id=fabric_id)
    
    fabric.subtract(length, remark=remark, employee=user)
    
    response = HttpResponse(json.dumps(fabric.get_data()), mimetype="application/json")
    response.status_code = 200
    return response
    
#Resets Length from a fabric
def fabric_reset(request, fabric_id):
    
    from supplies.models import Fabric
    logger.debug(request.POST)
    user = request.user
    length = request.POST.get('length')
    remark = request.POST.get('remark')
    
    fabric = Fabric.objects.get(id=fabric_id)
    
    fabric.reset(length, remark=remark, employee=user)
    
    response = HttpResponse(json.dumps(fabric.get_data()), mimetype="application/json")
    response.status_code = 200
    return response

#foam
def foam(request, foam_id=0):
    from supplies.models import Foam
     
    return processRequest(request, Foam, foam_id)
    
#lumber
def lumber(request, lumber_id=0):
    from supplies.models import Lumber
    
    return processRequest(request, Lumber, lumber_id)
    

def sewing_thread(request, sewing_thread_id=0):
    from supplies.models import SewingThread
    return processRequest(request, SewingThread, sewing_thread_id)

def screw(request, screw_id=0):
    from supplies.models import Screw
    return processRequest(request, Screw, screw_id)

def staple(request, staple_id=0):
    from supplies.models import Staple
    return processRequest(request, Staple, staple_id)

def webbing(request, webbing_id=0):
    from supplies.models import Webbing
    return processRequest(request, Webbing, webbing_id)

def wool(request, wool_id=0):
    from supplies.models import Wool
    return processRequest(request, Wool, wool_id)

def zipper(request, zipper_id=0):
    from supplies.models import Zipper
    return processRequest(request, Zipper, zipper_id)
