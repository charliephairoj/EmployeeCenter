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


def voice(request):
    resp = VoiceResponse()
    if "To" in request.form and request.form["To"] != '':
        dial = Dial(caller_id=os.environ['TWILIO_CALLER_ID'])
        # wrap the phone number or client name in the appropriate TwiML verb
        # by checking if the number given has only digits and format symbols
        if phone_pattern.match(request.form["To"]):
            dial.number(request.form["To"])
        else:
            dial.client(request.form["To"])
        resp.append(dial)
    else:
        resp.say("Thanks for calling!")

    return Response(str(resp), mimetype='text/xml')


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
        clients = ["chutima", 'oil']

    elif digits == 3:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66988325610']
        clients = ["may"]
    elif digits == 8:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-accounting.mp3"
        numbers = ['+66990041468']
        clients = ["charliephairoj"]
    else:
        message = "https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-transferring-customer-service.mp3"
        numbers = ['+66914928558', '+66952471426']
        clients = ["chutima", 'oil']

    resp = VoiceResponse()
    resp.play(message)

    dial = Dial(caller_id='+6625088681')
    for number in numbers:
        dial.number(number)
    
    for client in clients:
        dial.client(client)

    resp.append(dial)

    return HttpResponse(resp)
