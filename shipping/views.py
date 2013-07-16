# Create your views here.
import json
import os
import time
import dateutil.parser

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from shipping.models import Shipping
from acknowledgements.models import Acknowledgement


@login_required
def shipping(request, shipping_id=0):
    #Get Request
    if request.method == "GET":
        
        if shipping_id ==  0:
            GET_data = request.GET
            data = []
            shippings = Shipping.objects.all().order_by('-id')
            if "last_modified" in GET_data:
                timestamp = dateutil.parser.parse(GET_data["last_modified"])
                shippings = shippings.filter(last_modified__gte=timestamp)
            for shipping in shippings:
                data.append(shipping.get_data())
            response = HttpResponse(json.dumps(data), mimetype="application/json")
            return response

        else:

            shipping = Shipping.objects.get(id=shipping_id)

            response = HttpResponse(json.dumps(shipping.get_data()), mimetype="application/json")
            return response

    if request.method == "POST":
        data = json.loads(request.body)
        shipping = Shipping()
        urls = shipping.create(data, user=request.user)
        data = urls.update(shipping.get_data())
        return HttpResponse(json.dumps(urls), mimetype="application/json")


@login_required
def pdf(request, shipping_id):
    shipping = Shipping.objects.get(id=shipping_id)
    print shipping.shipping_key
    data = {'url': shipping.get_url(shipping.shipping_key)}
    return HttpResponse(json.dumps(data),
                            mimetype="application/json")


#Get url
@login_required
def acknowledgement_url(request, ack_id=0):
    if ack_id != 0 and request.method == "GET":
        ack = Acknowledgement.object.get(id=ack_id)


@login_required
def acknowledgement_item_image(request):
    if request.method == "POST":
        image = request.FILES['image']
        filename = settings.MEDIA_ROOT + str(time.time()) + '.jpg'
        with open(filename, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        #start connection
        conn = S3Connection(settings.AWS_ACCESS_KEY_ID,
                            settings.AWS_SECRET_ACCESS_KEY)
        #get the bucket
        bucket = conn.get_bucket('media.dellarobbiathailand.com', True)
        #Create a key and assign it
        k = Key(bucket)
        #Set file name
        k.key = "acknowledgement/item/image/%f.jpg" % (time.time())
        #upload file
        k.set_contents_from_filename(filename)
        #remove file from the system
        os.remove(filename)
        #set the Acl
        k.set_canned_acl('private')
        #set Url, key and bucket
        data = {
                'url': k.generate_url(300, force_http=True),
                'key': k.key,
                'bucket': 'media.dellarobbiathailand.com'
        }
        #self.save()
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        response.status_code = 201
        return response
