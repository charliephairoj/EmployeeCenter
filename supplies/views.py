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

#uploads a fabric
def fabric_image(request, fabric_id=0):
    
    from django.conf import settings
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key
    import os
    
    if request.method == "POST":
        
        if fabric_id != 0:
            
            image = request.FILES['image']
            filename = settings.MEDIA_ROOT+fabric_id+'.jpg'
            
            with open(filename, 'wb+' ) as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            #start connection
            conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
            #get the bucket
            bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
            #Create a key and assign it 
            k = Key(bucket)
                
            #Set file name
            k.key = "supplies/fabric/%s.jpg" % fabric_id
            #upload file
            
            k.set_contents_from_filename(filename)
            
            #remove file from the system
            os.remove(filename)
            #set the Acl
            k.set_canned_acl('public-read')
         
            #set Url, key and bucket
            data = {
                    'url':k.generate_url(788400000),
                    'key':k.key,
                    'bucket':'media.dellarobbiathailand.com'
            }
            
        #self.save()
            response = HttpResponse(json.dumps(data), mimetype="application/json")
            response.status_code = 201
            return response
        
#Reserve fabric
def fabric_reserve(request, fabric_id):
    
    from supplies.models import Fabric
    
    user = request.user
    length = request.POST.get('length')
    remark = request.POST.get('remark')
    
    fabric = Fabric.objects.get(id=fabric_id)
    fabric.reserve(length, remark=remark, employee=user)
    
    response = HttpResponse(json.dumps(fabric.get_data()), mimetype="application/json")
    response.status_code = 200
    return response

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

#Fabric Log 
def fabric_log(request, fabric_id=0):
    from supplies.models import FabricLog
    
    if request.method == "GET":
        
        logs = FabricLog.objects.filter(fabric_id=fabric_id)
        data = []
        for log in logs:
            
            data_item = {
                         'action':log.action,
                         'length':str(log.length),
                         'total':str(log.current_length),
                         'remarks':log.remarks,
                         'employee':"%s %s" %(log.employee.first_name, log.employee.last_name),
                         'timestamp':log.timestamp.strftime('%B %d, %Y %H:%M:%S')
                         }
            data.append(data_item)
        
        response = HttpResponse(json.dumps(data), mimetype="application/json")
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
