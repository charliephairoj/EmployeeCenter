#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial
from twilio.jwt.client import ClientCapabilityToken
import boto.ses


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
    logger.debug(request.GET)
    resp = VoiceResponse()

    gather = Gather(action="/api/v1/ivr/test/route_call/", method="POST", num_digits=1, timeout=10)
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-welcome.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-sales.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-customer-service.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-accounting.mp3")
    resp.append(gather)

    return HttpResponse(resp)

def route_call(request):

    logger.debug(request.POST)
    logger.debug(request.POST.get('Digits', ''))

    digits = int(request.POST.get('Digits', '0'))
    call_origin = request.POST.get('From', None)

    call_log = Call.objects.create(twilio_id=request.POST.get('CallSid', None), 
                                   type="incoming", 
                                   incoming_number=call_origin)

    logger.debug(call_log.__dict__)

    if digits == 1:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-sales.mp3"
        numbers = ['+66819189145']
        clients = ["sidarat"]
        caller_id = call_origin or '+6625088681'

        call_log.forwarding_number = '+66819189145'
        call_log.save()

    elif digits == 2:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = ['+66914928558', '+66952471426']
        clients = ["chup", 'apaporn']
        caller_id = '+6625088681'

    elif digits == 3:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66988325610']
        clients = ["mays"]
        caller_id = '+6625088681'

    elif digits == 8:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66990041468']
        clients = ["charliephairoj"]
        caller_id = call_origin or ""

        call_log.forwarding_number = '+66990041468'
        call_log.save()

    else:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = ['+66914928558', '+66952471426']
        clients = ["chup", 'apaporn']
        caller_id = '+6625088681' or '+6625088681'

    resp = VoiceResponse()
    resp.play(message)

    dial = Dial(caller_id=caller_id, 
                action='/api/v1/ivr/status/',
                record='record-from-ringing', 
                recording_status_callback="/api/v1/ivr/recording/")

    for number in numbers:
        dial.number(number,
                    status_callback_event=['answered', 'completed'],
                    status_callback='/api/v1/ivr/status/',)
    
    for client in clients:
        dial.client(client,
                    status_callback_event=['answered', 'completed'],
                    status_callback='/api/v1/ivr/status/',)

    resp.append(dial)

    return HttpResponse(resp)


def call_status_update_callback(request):
    call_data = request.POST
    logger.debug(call_data)

    try:
        call_log = Call.objects.get(twilio_id=call_data.get('CallSid', 0))
    except Exception as e:
        call_log = Call()

    call_log.twilio_id = request.POST.get('CallSid', call_log.twilio_id)
    call_log.type = call_data.get('Direction', call_log.type) 
    call_log.incoming_number = call_data.get('From', call_log.incoming_number)
    call_log.save()

    resp = VoiceResponse()
    resp.hangup()
    return HttpResponse(resp)


def recording_callback(request):
    call_data = request.POST
    logger.debug(call_data)
    call_log = Call.objects.get(twilio_id=call_data.get('CallSid', 0))

    call_log.duration = call_data.get('RecordingDuration', call_log.duration)
    call_log.recording_url = call_data.get('RecordingUrl', call_log.recording_url)

    call_log.save()

    resp = VoiceResponse()
    resp.hangup()

    return HttpResponse(resp)

def email_call_summary(recipient, body):

    conn = boto.ses.connect_to_region('us-east-1')
    conn.send_email('no-replay@dellarobbiathailand.com',
                    'Acknowledgement of Order Placed',
                    body,
                    recipients,
                    format='html')