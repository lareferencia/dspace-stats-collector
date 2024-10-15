#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Matomo pipeline components """

import logging
logger = logging.getLogger()

import urllib.parse
import json
import random
from datetime import datetime
from pytz import timezone
import requests
import copy

# define Python user-defined exceptions
class MatomoException(Exception):
    """Base class for other exceptions"""
    pass

class MatomoOfflineException(MatomoException):
    """Base class for other exceptions"""
    pass

class MatomoInternalServerException(MatomoException):
    """Base class for other exceptions"""
    pass


BULK_TRACKING_BATCH_SIZE_DEFAULT = 50

class FileOutput:

    def __init__(self, configContext):
        self._configContext = configContext
        self._file = open( configContext.getExportFileName() , 'w')

    def run(self, events):
        
        processed = 0
        robots_count = 0  
                
        for event in events:
            processed += 1
            self.write(event)
            if event.is_robot == True: 
                robots_count += 1            
                
        if robots_count == processed:
            logger.debug('Everyone was a robot')

        logger.debug('How many robots: {}'.format(robots_count))
        
        self._file.close()
        
        #logger.debug("Starting processing: %s on: %s from date: %s" % (repoName, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), configContext.history.get_last_tracked_timestamp())) 
        logger.info('DSpace Stats Export finished {} events from {} to {}. Breakdown: {} events discarted as robot. Filename: {}'.format(processed, self._configContext.solrQueryInitialTimestamp, self._configContext.solrQueryUntilDate, robots_count, self._configContext.getExportFileName()))
        
    ## write to file
    def write(self, event):
        ## if not robot write to file
        if event.is_robot == False:
            self._file.write(event._matomoRequest + '\n')
