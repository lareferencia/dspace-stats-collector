#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Elasticsearch pipepline components """

import logging
logger = logging.getLogger()

from elasticsearch import Elasticsearch

class ElasticsearchOutput:

    def __init__(self, configContext):

        try:
            ##self.elasticServer = Elasticsearch('https://elastic:wXYFb2YVX6Yd2A0lvM5fDKxx@92245714c70c48d6a707b40423677fe0.us-east-1.aws.found.io:9243')
            self.elasticServer = Elasticsearch(configContext.properties['elastic.url'])
        except Exception as err:
            logger.exception("Connection to elastic failed")
        
        self.indexName = configContext.properties['elastic.index']

    def _send(self, event):
        
        try:
            result = self.elasticServer.index(index=self.indexName, doc_type='event', body=event.toJSON() )
            #logger.debug( "ElasticsearchOutpue Event: {} Result: {}".format(event, result['result']) )
        except:
            logger.exception("Send event to elastic failed")


    def run(self, events):
        n = 0
        for event in events:
            n += 1
            self._send(event)

        logger.debug('Elasticsearc Output finished processing {} events'.format(n))