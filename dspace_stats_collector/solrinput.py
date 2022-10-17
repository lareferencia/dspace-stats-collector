#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" SOLR pipeline components """

import logging
import re
logger = logging.getLogger()

import json
import pysolr

try:
    from .eventpipeline import Event
except Exception: #ImportError
    from eventpipeline import Event

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
        fromTimestamp = initialTimestamp
    
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
                fromTimestamp = docs[-1]['time']
                retryToLookAhead = 0
                yield docs
            else:
                # we store the original fromTimestamp
                oldFromTimestamp = fromTimestamp
                # if we did not found any documents, then we need to increase the number of days to look ahead
                retryToLookAhead += 1
                # we move the fromTimestamp adding n+1 days where n are the days we have looked ahead so far (was incremented by 1 in the last line) 
                fromTimestamp = oldFromTimestamp + ('+%sDAYS' % retryToLookAhead)
                # note that toTimeStamp will be fromTimestamp + retryToLookAhead + 1 ( keeping the one day window)
        
                # if the retryToLookAhead is reached the maxDaysToLoolForEvent, then we are done
                # or if untilDate was originally set, then we are done ignoring the look ahead process
                done = (retryToLookAhead >= self.maxDaysToLookForEvents) or (untilDate is not None) 

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
        solr = pysolr.Solr(self._solrServerURL, timeout=100)
        cursor = SolrTimestampCursor(solr, {
            'q': '*',
            'sort': 'time asc',
            'start': 0,
            'wt': 'json',
            'fq': '+statistics_type:"view" +type:(0 OR 2)',
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
