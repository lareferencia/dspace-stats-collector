#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" SOLR pipeline components """

from email.utils import parsedate
import logging
import re
logger = logging.getLogger()

import datetime

import json
import pysolr

try:
    from .eventpipeline import Event
except Exception: #ImportError
    from eventpipeline import Event

TIMESTAMP_PATTERN = "%Y-%m-%dT%H:%M:%S.%fZ"

class SolrTimestampCursor(object):
    
    """ Implements the concept of timestamped cursor """
    def __init__(self, solr, query, maxDaysToLookForEvents=30):
        """ Cursor initialization """
        self.solr = solr
        self.query = query
        self.maxDaysToLookForEvents = maxDaysToLookForEvents

    def fetch(self, rows=500, limit=None, initialTimestamp=None, untilDate=None):
        """ Generator method that grabs all the documents in bulk sets of
        'rows' documents
        :param rows: number of rows for each request
        """

        docs_retrieved = 0
        done = False

        # this will hold the working from timestamp 
        fromTimestamp = initialTimestamp

        # this will hold the last timestamp we have successfully retrieved and processed
        lastGoodFromTimestamp = initialTimestamp
    
        # this counts the number of days we have looked ahead if the initial query does not return any results
        retryToLookAhead = 0
        # this counts the number of days we will look ahead from fromTimestamp
        daysToLookAhead = 1

        while not done:

             # limit the number of rows to the number of documents left to retrieve
            if limit is not None:
                rows = min(rows, limit - docs_retrieved)

            # if the untilDate is None, then we set toTimestamp to the initialTimestamp plus the number of days to look ahead (default 1)
            if untilDate is None:
                # we look ahead for the number of days specified in daysToLookAhead counting from fromTimestamp
                toTimeStamp = fromTimestamp + ('+%sDAYS' % daysToLookAhead) 
            else: # otherwise, we need to set up the toTimeStamp to the untilDate
                logger.debug('Until date is fixed looking events until %s' % untilDate)
                toTimeStamp = untilDate

            # query solr    
            logger.debug('Fetching {} SOLR docs from timestamp: {} to timestamp {}'.format(rows, fromTimestamp, toTimeStamp))
            docs = self._query_solr(fromTimestamp, toTimeStamp, rows)
            numDocs = len(docs)
 
            # if we have retrieved any documents, then we need to update the docs_retrieved count, also update fromTimestamp to the timestamp of the last document
            # and we need to reset the retryToLookAhead counter, then we yield the documents
            if numDocs > 0:
                docs_retrieved += numDocs
                lastGoodFromTimestamp = docs[-1]['time'] # update the lastGoodFromTimestamp to the timestamp of the last document
                fromTimestamp = lastGoodFromTimestamp # update the fromTimestamp to the lastGoodFromTimestamp
                retryToLookAhead = 0
                yield docs
            else: # if we did not found any documents
                # we restore the last good fromTimestamp, because if we moved forward in time without succes we need restore the last good timestamp in order to avoid cumulative day offsets
                fromTimestamp = lastGoodFromTimestamp
                # , then we need to increase the number of days to look ahead
                retryToLookAhead += 1
                # we move the fromTimestamp adding n+1 days where n are the days we have looked ahead so far (was incremented by 1 in the last line) 
                fromTimestamp = fromTimestamp + ('+%sDAYS' % retryToLookAhead)
                # note that toTimeStamp will be fromTimestamp + retryToLookAhead + 1 ( keeping the one day window)

                # if the retryToLookAhead is reached the maxDaysToLoolForEvent, then we are done
                # or if untilDate was originally set, then we are done ignoring the look ahead process
                done = (retryToLookAhead > self.maxDaysToLookForEvents) or (untilDate is not None) or (docs_retrieved >= limit)

            
                # finally we consider an special case, if the lastGoodFromTimestamp + retyToLookAhead is greater than present moment then we are done
                try:
                    # example 2022-10-17T08:36:03.879Z
                    parsedate = datetime.datetime.strptime(str(lastGoodFromTimestamp), TIMESTAMP_PATTERN)
                    parsedate = parsedate + datetime.timedelta(days=retryToLookAhead)   
                    
                    if parsedate > datetime.datetime.now(): 
                        logger.debug('SOLR Query look ahead process has reached the present moment, no events found!!! we are done')
                        done = True
                        
                except ValueError as e: # if the date is not valid, then we ignore this error and continue
                    logger.error('Error parsing datestamp %s during solr query process - Something is wrong with lastTimestamp store' % lastGoodFromTimestamp)



        
       
    def _query_solr(self, fromTimestamp, toTimeStamp, rows):
        
        # copy the query and add the time range
        query = self.query.copy()
        query['q'] = self.query.get('q','*') + (' +time:{"%s" TO "%s"]' % (fromTimestamp, toTimeStamp))
        query['rows'] = rows
        
        # query solr
        results = self.solr._select(query)
        
        # convert the results to json object
        resp_data = json.loads(results)
        
        # return the documents
        return resp_data['response']['docs']

class SolrStatisticsInput:

    def __init__(self, configContext):
         
        self._rows = configContext.solrQueryRows
        self._limit = configContext.maxEventsToSend
        self._initialTimestamp = configContext.solrQueryInitialTimestamp
        self._untilDate = configContext.solrQueryUntilDate
        self._solrServerURL = configContext.solrStatsCoreURL

    def run(self):
        solr = pysolr.Solr(self._solrServerURL, timeout=600)
        cursor = SolrTimestampCursor(solr, {
            'q': '*',
            'sort': 'time asc',
            'start': 0,
            'wt': 'json',
            'fq': '+statistics_type:"view" +type:(0 OR 2) +isBot:false',
            'fl': 'id,ip,owningItem,referrer,time,type,userAgent'
        })
        

        n = 0
        for docs in cursor.fetch(rows=self._rows, limit=self._limit, initialTimestamp = self._initialTimestamp, untilDate = self._untilDate):

            logger.debug('{} SOLR docs retrieved. Converting docs to events'.format(len(docs)))

            for doc in docs:
                event = Event()
                event._id = n
                event._src = doc
                n = n + 1 

                if 'userAgent' not in doc.keys():
                    event._src['userAgent'] = None

                logger.debug('SOLR_INPUT:: Event: {}'.format(event._id))

                yield event
