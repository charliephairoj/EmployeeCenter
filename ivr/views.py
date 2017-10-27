#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import render
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial
from twilio.jwt.client import ClientCapabilityToken
import boto.ses

from administrator.models import Log
from ivr.models import Call


logger = logging.getLogger(__name__)


@csrf_exempt
def voice(request):
    """Returns TwiML instructions to Twilio's POST requests"""
    resp = VoiceResponse()
    dial = Dial(caller_id='+6625088681')

    # If the browser sent a phoneNumber param, we know this request
    # is a support agent trying to call a customer's phone
    if 'phoneNumber' in request.POST:
        dial.number(request.POST['phoneNumber'])
    else:
        # Otherwise we assume this request is a customer trying
        # to contact support from the home page
        dial.client('support_agent')
    
    resp.append(dial)
    return HttpResponse(resp)


@csrf_exempt
def get_token(request):
    """Returns a Twilio Client token"""
    # Create a TwilioCapability token with our Twilio API credentials
    capability = ClientCapabilityToken(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN)

    # If the user is on the support dashboard page, we allow them to accept
    # incoming calls to "support_agent"
    # (in a real app we would also require the user to be authenticated)
    capability.allow_client_incoming(request.user.username)
    # Allow our users to make outgoing calls with Twilio Client
    capability.allow_client_outgoing(settings.TWIML_APPLICATION_SID)
    # Generate the capability token
    token = capability.to_jwt()

    return JsonResponse({'token': token})


@csrf_exempt
def test(request):
    resp = VoiceResponse()

    gather = Gather(action="/api/v1/ivr/test/route_call/", method="POST", num_digits=1, timeout=10)
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-welcome.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-sales.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-customer-service.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-accounting.mp3")
    resp.append(gather)

    return HttpResponse(resp)

def route_call(request):


    digits = int(request.POST.get('Digits', '0'))
    call_origin = request.POST.get('From', None)

    call_log = Call.objects.create(twilio_id=request.POST.get('CallSid', None), 
                                   type="incoming", 
                                   incoming_number=call_origin)
    if digits == 1:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-sales.mp3"
        numbers = [(73, '+66819189145')]
        clients = [(73, "sidarat")]
        caller_id = call_origin or '+6625088681'

        call_log.forwarding_number = '+66819189145'
        call_log.save()

    elif digits == 2:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = [(16, '+66914928558'), (42, '+66952471426'), (42, '+66634646465')]
        clients = [(16, "chup"), (42, 'apaporn')]
        caller_id = '+6625088681'

    elif digits == 3:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = [(63, '+66988325610')]
        clients = [(63, "mays")]
        caller_id = '+6625088681'

    elif digits == 8:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = [(1, '+66990041468')]
        clients = [(1, "charliephairoj")]
        caller_id = "+6625088681"

        call_log.forwarding_number = '+66990041468'
        call_log.save()

    else:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = [(16, '+66914928558'), (42, '+66952471426')]
        clients = [(16, "chup"), (42, 'apaporn')]
        caller_id = '+6625088681' or '+6625088681'

    resp = VoiceResponse()
    resp.play(message)

    dial = Dial(caller_id=caller_id, 
                #action='/api/v1/ivr/status/',
                record='record-from-ringing', 
                recording_status_callback="/api/v1/ivr/recording/")

    for number in numbers:
        dial.number(number[1],
                    status_callback_event='answered',
                    status_callback=_get_status_callback_url(number[0]),
                    status_callback_method="GET")
    
    for client in clients:
        dial.client(client[1],
                    status_callback_event='answered',
                    status_callback=_get_status_callback_url(client[0]),
                    status_callback_method="GET")

    resp.append(dial)

    return HttpResponse(resp)


def call_status_update_callback(request):
    call_data = request.GET

    try:
        user = User.objects.get(pk=call_data['employee_id'])
    except Exception as e:
        logger.debug(e)
        user = User.objects.get(pk=1)

    try:
        call_log = Call.objects.get(twilio_id=call_data.get('ParentCallSid', 0))
    except Exception as e:
        logger.debug(e)
        logger.debug("New Call Created")
        call_log = Call()

    call_log.twilio_id = request.POST.get(u'ParentCallSid', call_log.twilio_id)
    call_log.type = call_log.type or call_data.get('Direction', call_log.type) 
    call_log.incoming_number = call_log.incoming_number or call_data.get('From', call_log.incoming_number)
    call_log.employee = user
    call_log.save()

    resp = VoiceResponse()
    resp.hangup()
    return HttpResponse(resp)


def recording_callback(request):
    call_data = request.POST
    call_log = Call.objects.get(twilio_id=call_data.get('CallSid', 0))

    call_log.duration = call_data.get('RecordingDuration', call_log.duration)
    call_log.recording_url = call_data.get('RecordingUrl', call_log.recording_url)

    call_log.save()

    resp = VoiceResponse()
    resp.hangup()

    try:
        email_call_summary(call_log.employee.email, call_log)
    except Exception as e:
        try: 
            employee = call_log.employee or User.objects.get(pk=1)
        except AttributeError:
            employee = User.objects.get(pk=1)
        Log.objects.create(type="Call Summary Error", 
                           message=e,
                           user=employee)
        email_call_summary('charliep@alineagroup.co', call_log, 'error call summary')


    return HttpResponse(resp)

def email_call_summary(recipient, call, subject='Call Summary'):

    body = render_to_string('call_summary.html', {'call': call})
    conn = boto.ses.connect_to_region('us-east-1')
    conn.send_email('no-replay@dellarobbiathailand.com',
                    subject,
                    body,
                    recipient,
                    format='html')

def _get_status_callback_url(employee_id=None):
    status_callback_url = 'https://employee.alineagroup.co/api/v1/ivr/status/'

    if employee_id:
        status_callback_url += "?employee={0}".format(employee_id)
    
    
    return status_callback_url