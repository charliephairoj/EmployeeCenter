#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from time import sleep

logger = logging.getLogger(__name__)


class EmptyQueueError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class Queue:

    def __init__(self):
        self.queue = list()

    @property
    def size(self):
        return len(self.queue)

    #Adding elements to queue
    def enqueue(self, q_obj):
        self.queue.insert(0, q_obj)
            

    #Removing the last element from the queue, timeout in milliseconds
    def dequeue(self, timeout=0):
        if self.size > 0:

            if timeout >= 0:
                sleep(timeout / 1000)
                
            return self.queue.pop()

        raise EmptyQueueError('The queue is empty!')