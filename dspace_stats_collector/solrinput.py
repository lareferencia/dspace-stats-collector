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

class TimestampCursor(object):
    """ Implements the concept of cursor in relational databases """
    def __init__(self, solr, query, timeout=100):
        """ Cursor initialization """
        self.solr = solr
        self.query = query
        self.timeout = timeout
        self.baseQuery = self.query['q']

    def fetch(self, rows=100, limit=None, initialTimestamp=None):
        """ Generator method that grabs all the documents in bulk sets of
        'rows' documents
        :param rows: number of rows for each request
        """

        docs_retrieved = 0
        done = False
        lastTimestamp = None

        while not done:
            if (docs_retrieved == 0) & (initialTimestamp is not None):
                self.query['q'] = self.baseQuery + (' +time:{"%s" TO *]' % initialTimestamp)
            elif docs_retrieved > 0:
                self.query['q'] = self.baseQuery + (' +time:{"%s" TO *]' % lastTimestamp)

            if limit is not None:
                rows = min(rows, limit - docs_retrieved)
            self.query['rows'] = rows

            results = self.solr._select(self.query)
            resp_data = json.loads(results)
            if (docs_retrieved == 0):
                numFound = resp_data['response']['numFound']
                if limit is not None:
                    docsToGo = min(numFound, limit)
                else:
                    docsToGo = numFound
                logger.debug('{} SOLR events to be processed'.format(docsToGo))
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
        self._limit = configContext.solrQueryLimit
        self._initialTimestamp = configContext.solrQueryInitialTimestamp
        self._solrServerURL = configContext.solrStatsCoreURL

    def run(self):
        solr = pysolr.Solr(self._solrServerURL, timeout=100)
        cursor = TimestampCursor(solr, {
            'q': '*',
            'sort': 'time asc',
            'start': 0,
            'wt': 'json',
            'fq': '+statistics_type:"view" +type:(0 OR 2)',
            'fl': 'id,ip,owningItem,referrer,time,type,userAgent'
        })
        for docs in cursor.fetch(rows=self._rows, limit=self._limit, initialTimestamp = self._initialTimestamp):
            for doc in docs:
                event = Event()
                event._src = doc
                if 'userAgent' not in doc.keys():
                    event._src['userAgent'] = ''
                yield event
