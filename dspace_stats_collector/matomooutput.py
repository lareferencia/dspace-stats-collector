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
            params['cvar'] = json.dumps({"1": ["oaipmhID", oaipmhID], "2": ["repositoryID",self._repoProperties['matomo.repositoryId']], "3": ["countryID",self._repoProperties['matomo.countryISO']] })

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
            
            logger.debug('MATOMO_FILTER:: Event: {} is_robot {}'.format(event._id, event.is_robot))

            yield event


BULK_TRACKING_BATCH_SIZE_DEFAULT = 50

class MatomoBufferedSender:

    def __init__(self, configContext):
    
        self._configContext = configContext
        self._buffer = [] # init buffer 
        self._totalSent = 0
        self._url = configContext.getMatomoUrl()
        
        try:
            self._bufferSize = configContext.getMatomoOutputSize()
            assert(self._maxBufferSize > 0)
        except:
            self._bufferSize = BULK_TRACKING_BATCH_SIZE_DEFAULT

    def getTotalSent(self):
        return self._totalSent

    def send(self, event):
        request_list = [ e._id for e in self._buffer ]
        print(list(request_list))
        self._buffer.append(event)
        request_list = [ e._id for e in self._buffer ]
        print(list(request_list))
        if self.isBufferFull():
            self.flush()
      
    def isBufferFull(self):
        return len(self._buffer) >= self._bufferSize

    def _sendRequestsToMatomo(self, url, events):

        lastEventTimestamp = events[-1]._src['time'] 

        try:
            request_list = [ e._matomoRequest for e in events ]
            #print(list(request_list))
            #request_list = [ e._matomoRequest for e in events] 
            if len(request_list) > 0: #sends only non empty lists
                http_response = requests.post(url, data = json.dumps( dict( requests = request_list, token_auth = self._configContext.getMatomoTokenAuth()) ))
                #http_response = requests.post(url, data = json.dumps( dict( requests = [ e._matomoRequest for e in events if not e.is_robot  ], token_auth = self._configContext.getMatomoTokenAuth()) ))
                http_response.raise_for_status()
                json_response = json.loads(http_response.text)
            
                if json_response['status'] != "success" or json_response['invalid'] != 0:
                    raise MatomoInternalServerException(http_response.text, json_response)
            else:
                logger.debug("There are no events to send")  #Modificación MEMO#
        
        except requests.exceptions.HTTPError as e:
            print(e)
            raise MatomoInternalServerException(str(e))

        except requests.exceptions.ConnectionError as e:
            print(e)
            raise MatomoOfflineException(str(e))
            
        except requests.exceptions.RequestException as e:
            print(e)
            raise MatomoOfflineException(str(e))

        return lastEventTimestamp


    def flush(self):

        lastEventTimestamp = None
      
        try: 
            # try to send all buffered events        
            lastEventTimestamp = self._sendRequestsToMatomo(self._url, self._buffer)
            self._totalSent += len(self._buffer)

        except MatomoOfflineException as e:
            # if is offline will break the execution
            raise

        except MatomoInternalServerException as e:

            # if some there is some internal problem, the will try to send each event 

            logger.error('Matomo internal error detected processing events in bulk. Retrying in one event per request mode: Error was: {}'.format( str(e) ) )            

            for event in self._buffer:

                try:
                    lastEventTimestamp = e._src['time'] # in this mode, the event timestamp is always assigned as the last timestamp
                    if not event.is_robot:
                        self._sendRequestsToMatomo(self._url, [event]) # send one event
                        self._totalSent += 1
                        #logger.info('totalSent + 1 after error')

                except MatomoOfflineException as e: # if server is down break
                    raise 
                
                except MatomoInternalServerException as e: # if there is some internal error will discard this event and log the result
                    logger.error('Matomo internal error occurred: {} with event. This event will be discarded.\n {}'.format( str(e), event ) )            



        if lastEventTimestamp != None:
            self._configContext.history.save_last_tracked_timestamp(lastEventTimestamp)
        
        self._buffer = [] #Clean buffer


class MatomoOutput:

    def __init__(self, configContext):

        self._configContext = configContext
        self._sender = MatomoBufferedSender(configContext)

    def run(self, events):
        
        processed = 0
        robots_count = 0  

        for event in events:
            processed += 1
            self._sender.send(event)
            if event.is_robot == True: 
                robots_count += 1            
                
        if robots_count == processed:
            logger.debug('Everyone was a robot')

        logger.debug('How many robots: {}'.format(robots_count))    
        self._sender.flush()
        logger.info('MatomoOutput finished processing {} events, sent {} succesfully'.format(processed, self._sender.getTotalSent()))
