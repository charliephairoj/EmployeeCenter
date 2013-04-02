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

from acknowledgements.models import Acknowledgement


@login_required
def acknowledgement(request, ack_id=0):
    #Get Request
    if request.method == "GET":
        if ack_id == 0:
            GET_data = request.GET
            data = []
            acks = Acknowledgement.objects.all().order_by('-id')

            #Additional filters from parameters
            if "start_date" in GET_data and "end_date" in GET_data:
                start_date = dateutil.parser.parse(GET_data['start_date'])
                end_date = dateutil.parser.parse(GET_data['end_date'])
                print start_date
                print end_date
                acks = acks.filter(delivery_date__range=[start_date, end_date])
            elif "start_date" in GET_data:
                start_date = dateutil.parser.parse(GET_data['start_date'])
                acks = acks.filter(delivery_date__gte=start_date)
            elif "end_date" in GET_data:
                end_date = dateutil.parser.parse(GET_data['end_date'])
                acks = acks.filter(delivery_date__lte=end_date)
            elif "date" in GET_data:
                date = dateutil.parser.parse(GET_data['date'])
                acks = acks.filter(delivery_date=date)
            if "last_modified" in GET_data:
                timestamp = dateutil.parser.parse(GET_data["last_modified"])
                acks = acks.filter(last_modified__gte=timestamp)
            for ack in acks:
                data.append(ack.get_data())
        else:
            ack = Acknowledgement.objects.get(id=ack_id)
            data = ack.get_data()
        response = HttpResponse(json.dumps(data), mimetype="application/json")
        return response

    if request.method == "POST":
        if ack_id == 0:
            data = json.loads(request.body)
            ack = Acknowledgement()
            urls = ack.create(data, user=request.user)
            data = urls.update(ack.get_data())
            return HttpResponse(json.dumps(urls),
                                mimetype="application/json")
        else:
            data = json.loads(request.body)
            ack = Acknowledgement.objects.get(id=ack_id)
            urls = ack.update(data, request.user)
            urls.update(ack.get_data())
            return HttpResponse(json.dumps(urls),
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
