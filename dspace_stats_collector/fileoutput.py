#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Matomo pipeline components """

import logging
logger = logging.getLogger()


import gzip

class FileOutput:

    def __init__(self, configContext):
        self._configContext = configContext
        self._file = gzip.open(configContext.getExportFileName() + '.gz', 'wt')

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
        
        logger.info('DSpace Stats Export finished {} events from {} to {}. Breakdown: {} events discarted as robot. Filename: {}'.format(processed, self._configContext.solrQueryInitialTimestamp, self._configContext.solrQueryUntilDate, robots_count, self._configContext.getExportFileName()))
        
    ## write to file
    def write(self, event):
        ## if not robot write to file
        if event.is_robot == False:
            self._file.write(event._matomoRequest + '\n')
