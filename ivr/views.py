#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial
from twilio.jwt.client import ClientCapabilityToken


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
    logger.debug(request)
    logger.debug(request.POST.get('Digits', ''))

    digits = int(request.POST.get('Digits', '0'))

    if digits == 1:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-sales.mp3"
        numbers = ['+66819189145']
        clients = ["sidarat"]

    elif digits == 2:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = ['+66914928558', '+66952471426']
        clients = ["chup", 'apaporn']

    elif digits == 3:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66988325610']
        clients = ["mays"]
    elif digits == 8:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66990041468']
        clients = ["charliephairoj"]
    else:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = ['+66914928558', '+66952471426']
        clients = ["chup", 'apaporn']

    resp = VoiceResponse()
    resp.play(message)

    dial = Dial(caller_id='+6625088681')
    for number in numbers:
        dial.number(number)
    
    for client in clients:
        dial.client(client)

    resp.append(dial)

    return HttpResponse(resp)
