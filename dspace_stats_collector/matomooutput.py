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

BULK_TRACKING_BATCH_SIZE_DEFAULT = 50

class MatomoFilter:

    def __init__(self, configContext):

        dspaceProperties = configContext.dspaceProperties

        if 'handle.canonical.prefix' in dspaceProperties.keys():
            self._handleCanonicalPrefix = dspaceProperties['handle.canonical.prefix']
        else:
            self._handleCanonicalPrefix = 'http://hdl.handle.net/'
        self._dspaceHostname = dspaceProperties['dspace.hostname']
        self._dspaceUrl = dspaceProperties['dspace.url']

        self._repoProperties = configContext.properties

    def run(self, events):
        for event in events:
            params = dict()

            # https://developer.matomo.org/api-reference/tracking-api
            params['idsite'] = self._repoProperties['matomo.idSite']
            params['rec'] = self._repoProperties['matomo.rec']
            params['action_name'] = event._db['record_title']
            params['_id'] = event._sess['id']
            params['rand'] = random.randint(1e5,1e6)
            params['apiv'] = 1

            if 'referrer' in event._src.keys():  # Not always available
                params['urlref'] = event._src['referrer']

            params['ua'] = event._src['userAgent']

            oaipmhID = "oai:{}:{}".format(self._dspaceHostname, event._db['handle'])
            params['cvar'] = json.dumps({"1": ["oaipmhID", oaipmhID], "2": ["repositoryID",self._repoProperties['matomo.repositoryId']] })

            if event._db['is_download']:
                params['download'] = "{dspaceUrl}/bitstream/{handle}/{sequence_id}/{filename}".format(
                    dspaceUrl = self._dspaceUrl,
                    handle = event._db['handle'],
                    sequence_id = event._db['sequence_id'],
                    filename = urllib.parse.quote(event._db['filename'])
                )
                params['url'] = params['download']
            else: # Not a download
                params['url'] = self._handleCanonicalPrefix + event._db['handle']
                # event.download does not get generated

            params['token_auth'] = self._repoProperties['matomo.token_auth']
            params['cip'] = event._src['ip']

            srctime = event._src['time']
            try:  # parse with or without milliseconds
                srctime = datetime.strptime(srctime, "%Y-%m-%dT%H:%M:%S.%fZ")
            except:
                srctime = datetime.strptime(srctime, "%Y-%m-%dT%H:%M:%SZ")

            try:  # if env locale is ok
                utctime = srctime.astimezone(timezone('UTC'))
            except:  # otherwise (naive datetime without timezone yet), report solr time as utc without converting
                local_tz = timezone('UTC')
                utctime = local_tz.localize(srctime)

            params['cdt'] = datetime.strftime(utctime, "%Y-%m-%d %H:%M:%S")
            logger.debug('SOLR time {} got converted to UTC: {}'.format(event._src['time'], params['cdt']))


            event._matomoParams = params
            event._matomoRequest = '?' + urllib.parse.urlencode(params)
            yield event


class MatomoBulkOutput:
#TODO: This matomo outputs will be used in combination with a general buffered output to be developed
    def __init__(self, configContext):
        self._configContext = configContext
        self._configContextProperties = configContext.properties
                 
    def run(self, events):
        data_dict = dict(
            requests=[event._matomoRequest for event in events],
            token_auth=self._configContextProperties['matomo.token_auth']
        )
        num_events = len(data_dict['requests'])
        url = self._configContextProperties['matomo.trackerUrl']

        try:
            http_response = requests.post(url, data = json.dumps(data_dict))
            http_response.raise_for_status()
            json_response = json.loads(http_response.text)
            if json_response['status'] != "success" or json_response['invalid'] != 0:
                raise ValueError(http_response.text)
        except requests.exceptions.HTTPError as err:
            logger.exception('HTTP error occurred: {}'.format(err))
            raise
        except:
            logger.exception('Error while posting events to tracker. URL: {}. Data: {}'.format(url, data_dict))
            raise

        logger.debug('{} events sent to matomo tracker'.format(num_events))
        logger.debug('MatomoOutput finished processing {} events'.format(num_events))


class MatomoOutput:

    def __init__(self, configContext):
        self._configContext = configContext
        self._configContextProperties = configContext.properties
        self._requestsBuffer = []
        self._lastTimestamp = None
        try:
            self._bulkTrackingBatchSize = int(self._configContextProperties['matomo.batchSize'])
            assert(self._bulkTrackingBatchSize > 0)
        except:
            self._bulkTrackingBatchSize = BULK_TRACKING_BATCH_SIZE_DEFAULT

    def _appendToBuffer(self, event):
        self._requestsBuffer.append(event._matomoRequest)
        self._lastTimestamp = event._src['time']

    def _flushBuffer(self):
        data_dict = dict(
            requests=self._requestsBuffer,
            token_auth=self._configContextProperties['matomo.token_auth']
        )
        num_events = len(self._requestsBuffer)
        url = self._configContextProperties['matomo.trackerUrl']

        # print(json.dumps(data_dict, indent=4, sort_keys=True))
        try:
            http_response = requests.post(url, data = json.dumps(data_dict))
            http_response.raise_for_status()
            json_response = json.loads(http_response.text)
            if json_response['status'] != "success" or json_response['invalid'] != 0:
                raise ValueError(http_response.text)
        except requests.exceptions.HTTPError as err:
            logger.exception('HTTP error occurred: {}'.format(err))
            raise
        except:
            logger.exception('Error while posting events to tracker. URL: {}. Data: {}'.format(url, data_dict))
            raise

        logger.debug('{} events sent to tracker'.format(num_events))
        logger.debug('Local time for last event tracked: {}'.format(self._lastTimestamp))
        self._configContext.save_last_tracked_timestamp(self._lastTimestamp)
        self._requestsBuffer = []
        self._lastTimestamp = None

    def run(self, events):
        n = 0
        for event in events:
            n += 1
            self._appendToBuffer(event)
            if (n % self._bulkTrackingBatchSize) == 0:
                self._flushBuffer()
        if (n % self._bulkTrackingBatchSize) != 0:
            self._flushBuffer()
        logger.debug('MatomoOutput finished processing {} events'.format(n))
