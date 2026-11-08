#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" SOLR pipeline components """

import logging
logger = logging.getLogger()

import datetime

import json
import pysolr

try:
    from .eventpipeline import Event
    from .config.history import TIMESTAMP_PATTERN
except Exception: #ImportError
    from eventpipeline import Event
    from config.history import TIMESTAMP_PATTERN

class SolrTimestampCursor(object):
    
    """ Implements the concept of timestamped cursor """
    def __init__(self, solr, query, maxDaysToLookForEvents=30):
        """ Cursor initialization """
        self.solr = solr
        self.query = query
        self.maxDaysToLookForEvents = maxDaysToLookForEvents

    def fetch(self, rows=500, limit=None, initialTimestamp=None, untilDate=None):
        """Read matching events through a fixed upper bound, including long gaps.

        Empty periods never advance the durable delivery checkpoint. Only the
        Matomo sender acknowledges progress, so failed batches remain retryable.
        maxDaysToLookForEvents is retained in the constructor for compatibility;
        it no longer limits how far this cursor searches.
        """
        if rows <= 0:
            raise ValueError("rows must be positive")

        upper_bound = untilDate or datetime.datetime.now(
            datetime.timezone.utc
        ).strftime(TIMESTAMP_PATTERN)
        from_timestamp = initialTimestamp
        retrieved = 0

        while limit is None or retrieved < limit:
            page_size = rows if limit is None else min(rows, limit - retrieved)
            logger.debug(
                "Fetching %s SOLR docs from %s through %s",
                page_size, from_timestamp, upper_bound,
            )
            docs = self._query_solr(from_timestamp, upper_bound, page_size)
            if not docs:
                logger.debug("No further matching SOLR events through %s", upper_bound)
                return

            retrieved += len(docs)
            from_timestamp = docs[-1]['time']
            yield docs

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
