#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" SOLR pipeline components """

import logging
logger = logging.getLogger()

import json
import pysolr

try:
    from .eventpipeline import Event
except Exception: #ImportError
    from eventpipeline import Event

class SolrTimestampCursor(object):
    
    """ Implements the concept of timestamped cursor """
    def __init__(self, solr, query):
        """ Cursor initialization """
        self.solr = solr
        self.query = query
        self.baseQuery = self.query['q']

    def fetch(self, rows=100, limit=None, initialTimestamp=None, untilDate=None):
        """ Generator method that grabs all the documents in bulk sets of
        'rows' documents
        :param rows: number of rows for each request
        """

        docs_retrieved = 0
        done = False
        lastTimestamp = initialTimestamp

        while not done:


            if untilDate != None:
                self.query['q'] = self.baseQuery + (' +time:{"%s" TO "%s"]' % (lastTimestamp, untilDate))
            else:
                #self.query['q'] = self.baseQuery + (' +time:{"%s" TO *]' % lastTimestamp)
                self.query['q'] = self.baseQuery + (' +time:{"%s" TO %s+30DAYS]' % (lastTimestamp,lastTimestamp))
            

            if limit is not None:
                rows = min(rows, limit - docs_retrieved)
            self.query['rows'] = rows

            logger.debug('Fetching {} SOLR docs from time: {}'.format(rows, lastTimestamp))

            results = self.solr._select(self.query)
            resp_data = json.loads(results)
            #if (docs_retrieved == 0):
                #numFound = resp_data['response']['numFound']
                #if limit is not None:
                #    docsToGo = min(numFound, limit)
                #else:
                #    docsToGo = numFound

            docs = resp_data['response']['docs']
            numDocs = len(docs)
 
            if numDocs > 0:
                docs_retrieved += numDocs
                lastTimestamp = docs[-1]['time']
                yield docs
            else:
                done = True


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
