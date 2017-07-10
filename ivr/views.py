#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import logging

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial


logger = logging.getLogger(__name__)

 
@csrf_exempt
def test(request):
    logger.debug(request)
    resp = VoiceResponse()
    gather = Gather(action="/api/v1/ivr/test/route_call/", method="POST", num_digits=1, timeout=5)
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-welcome.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-sales.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-customer-service.mp3")
    gather.play(url="https://s3-ap-southeast-1.amazonaws.com/media.dellarobbiathailand.com/ivr/audio-accounting.mp3")
    resp.append(gather)

    logger.debug(resp)

    return HttpResponse(resp)

def route_call(request):
    logger.debug(request)
    logger.debug(request.POST.get('Digits', ''))

    digits = int(request.POST.get('Digits', '0'))

    if digits == 1:
        message = "Routing to sales"
        number = '+66819189145'
    elif digits == 2:
        message = "Routing to customer service"
        number = '+19498294996'
    elif digits == 3:
        message = "Routing to accounting"
        number = '+66990041468'
    else:
        message = "Routing to customer service"
        number = '+19498294996'
    resp = VoiceResponse()
    resp.say(message)
    resp.dial(number)
    logger.debug(number)
    return HttpResponse(resp)
