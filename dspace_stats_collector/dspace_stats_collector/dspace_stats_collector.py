#!/usr/bin/env python
#
# -*- coding: utf-8 -*-

"""Main module."""
import json
import sys
import argparse
import logging
import hashlib
import requests
import re
import sqlalchemy
import pysolr
import urllib.parse
import random
import os
import pandas as pd
from pyjavaprops.javaproperties import JavaProperties
from dateutil import parser as dateutil_parser
from datetime import datetime
from pytz import timezone

logger = logging.getLogger()

DESCRIPTION = """
Collects Usage Stats from DSpace repositories.
"""
BULK_TRACKING_BATCH_SIZE_DEFAULT = 50
SAVE_DIR = os.path.expanduser('~') + '/.dspace_stats_collector'


class Event:

    _data_dict = {}

    def __init__(self):
        None

    def __getattr__(self, attribute):
        return self._data_dict[attribute]

    def __setattr__(self, name, value):
        self._data_dict[name] = value

    def __str__(self):
        return self._data_dict.__str__()

    def toJSON(self):
        return json.dumps(self._data_dict, indent=4, sort_keys=True)

class EventPipeline:

    _input_stage = None
    _filters_stage = []
    _output_stage = None

    def __init__(self, input, filters, output):
        self._input_stage = input
        self._filters_stage = filters
        self._output_stage = output

    def run(self):
        events = self._input_stage.run()

        for filter in self._filters_stage:
            events = filter.run(events)

        self._output_stage.run(events)


class DummyInput:

    def __init__(self):
        None

    def run(self):
        for x in range(1,5):
            event = Event()
            event.id = "00" + str(x)
            yield event


class FileInput:

    def __init__(self, filename):
        self._filename = filename

    def run(self):
        try:
            with open(self._filename, 'r') as content_file:
                query_result = content_file.read()
            r = json.loads(query_result)
            for doc in r['response']['docs']:
                event = Event()
                event._src = doc
                yield event
        except (FileNotFoundError, json.decoder.JSONDecodeError, KeyError):
            logger.exception("Error while trying to read events from {}".format(self._filename))
            raise


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

    def __init__(self, solrServer, rows=10, limit=None, initialTimestamp=None):
        self._rows = rows
        self._limit = limit
        self._initialTimestamp = initialTimestamp
        self._solrServer = solrServer + '/statistics'

    def run(self):
        solr = pysolr.Solr(self._solrServer, timeout=100)
        cursor = TimestampCursor(solr, {
            'q': '*',
            'sort': 'time asc',
            'start': 0,
            'wt': 'json',
            'fq': '+statistics_type:"view" +isBot:false +type:(0 OR 2)',
            'fl': 'id,ip,owningItem,referrer,time,type,userAgent'
        })
        for docs in cursor.fetch(rows=self._rows, limit=self._limit, initialTimestamp = self._initialTimestamp):
            for doc in docs:
                event = Event()
                event._src = doc
                if 'userAgent' not in doc.keys():
                    event._src['userAgent'] = ''
                yield event


class DummyFilter:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            event.url = "http://dummy.org/" + str(event.id)
            yield event


class RepoPropertiesFilter:

    def __init__(self, repoProperties):
        self._repoProperties = repoProperties

    def run(self, events):
        for event in events:
            event._repo = self._repoProperties
            yield event


class DSpaceDBFilter:

    def __init__(self, db):
        self._db = db

    def run(self, events):
        for event in events:
            resourceId = event._src['id']
            if event._src['type'] == 0: # Download
                isDownload = True
                owningItem = event._src['owningItem']
                event._db = self._db.queryDownload(resourceId, owningItem)
            elif event._src['type'] == 2: # Item
                isDownload = False
                owningItem = None
                event._db = self._db.queryItem(resourceId)
            else:
                logger.error("Unexpected resource type {} for resource: {}".format(event._src['type'], event._src))
                raise ValueError
            if event._db is None:
                continue # Drop event if could not recover data from db
            yield event


class SimpleHashSessionFilter:

    def __init__(self):
        None

    def run(self, events):
        for event in events:
            srcString = "{:%Y-%m-%d}#{}#{}".format(
                            dateutil_parser.parse(event._src['time']),
                            event._src['ip'],
                            event._src['userAgent']
                        )
            sessDict = {
                        'id': hashlib.md5(srcString.encode()).hexdigest(),
                        'srcString': srcString
                       }
            event._sess = sessDict
            yield event


class MatomoFilter:

    def __init__(self, dspaceProperties):
        if 'handle.canonical.prefix' in dspaceProperties.keys():
            self._handleCanonicalPrefix = dspaceProperties['handle.canonical.prefix']
        else:
            self._handleCanonicalPrefix = 'http://hdl.handle.net/'
        self._dspaceHostname = dspaceProperties['dspace.hostname']
        self._dspaceUrl = dspaceProperties['dspace.url']

    def run(self, events):
        for event in events:
            params = dict()

            # https://developer.matomo.org/api-reference/tracking-api
            params['idsite'] = event._repo['matomo.idSite']
            params['rec'] = event._repo['matomo.rec']

            params['action_name'] = event._db['record_title']
            params['_id'] = event._sess['id']
            params['rand'] = random.randint(1e5,1e6)
            params['apiv'] = 1

            if 'referrer' in event._src.keys():  # Not always available
                params['urlref'] = event._src['referrer']

            params['ua'] = event._src['userAgent']

            oaipmhID = "oai:{}:{}".format(self._dspaceHostname, event._db['handle'])
            params['cvar'] = json.dumps({"1": ["oaipmhID", oaipmhID]})

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

            params['token_auth'] = event._repo['matomo.token_auth']
            params['cip'] = event._src['ip']

            try:
                utctime = datetime.strptime(event._src['time'], "%Y-%m-%dT%H:%M:%S.%fZ").astimezone(timezone('UTC'))
            except:
                utctime = datetime.strptime(event._src['time'], "%Y-%m-%dT%H:%M:%SZ").astimezone(timezone('UTC'))
            params['cdt'] = datetime.strftime(utctime, "%Y-%m-%d %H:%M:%S")

            event._matomoParams = params
            event._matomoRequest = '?' + urllib.parse.urlencode(params)
            yield event


class DummyOutput:

    def __init__(self):
        None

    def run(self, events):
        n = 0
        for event in events:
            n += 1
            print(event.toJSON())
        logger.debug('DummyOutput finished processing {} events'.format(n))


class MatomoOutput:

    def __init__(self, repo):
        self._repo = repo
        self._repoProperties = repo.properties
        self._requestsBuffer = []
        self._lastTimestamp = None
        try:
            self._bulkTrackingBatchSize = int(self._repoProperties['matomo.batchSize'])
            assert(self._bulkTrackingBatchSize > 0)
        except:
            self._bulkTrackingBatchSize = BULK_TRACKING_BATCH_SIZE_DEFAULT

    def _appendToBuffer(self, event):
        self._requestsBuffer.append(event._matomoRequest)
        self._lastTimestamp = event._src['time']

    def _flushBuffer(self):
        data_dict = dict(
            requests=self._requestsBuffer,
            token_auth=self._repoProperties['matomo.token_auth']
        )
        num_events = len(self._requestsBuffer)
        url = self._repoProperties['matomo.trackerUrl']

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
        self._repo.save_to_history('lastTrackedEventTimestamp', self._lastTimestamp)
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


class EventPipelineBuilder:

    def __init__(self, args):
        self._args = args

    def build(self, repo):
        if self._args.date_from:
            initialTimestamp = self._args.date_from.strftime("%Y-%m-%dT00:00:00.000Z")
        elif 'lastTrackedEventTimestamp' in repo.history.keys():
            initialTimestamp = repo.history['lastTrackedEventTimestamp']
            logger.debug('Loaded initialTimestamp from history: {}'.format(initialTimestamp))
        else:
            initialTimestamp = None

        return EventPipeline(
#            FileInput("../tests/sample_input.json"),
            SolrStatisticsInput(repo.solrServer, limit=self._args.limit,
                initialTimestamp = initialTimestamp),
            [
                RepoPropertiesFilter(repo.properties),
                DSpaceDBFilter(repo.db),
                SimpleHashSessionFilter(),
                MatomoFilter(repo.dspaceProperties)
            ],
            MatomoOutput(repo))


class Repository:

    def __init__(self, repoName, propertiesFilename):
        self.repoName = repoName
        self.propertiesFilename = propertiesFilename
        self.properties = self._read_properties()
        self.dspaceProperties = self._read_dspace_properties()
        self.history = self._load_history()

        self.solrServer = self._find_solr_server()

        self.db = DSpaceDB(
                        self.dspaceProperties['db.url'],
                        self.dspaceProperties['db.username'],
                        self.dspaceProperties['db.password'],
                        self.dspaceProperties['db.schema'],
                        self.properties['dspace.majorVersion']
                    )

    def _read_properties(self):
        javaprops = JavaProperties()

        try:
            javaprops.load(open(self.propertiesFilename))
            property_dict = javaprops.get_property_dict()
        except (FileNotFoundError, UnboundLocalError):
            logger.exception("Error while trying to read properties file %s" % self.propertiesFilename)
            raise

        logger.debug("Read succesfully property file %s" % self.propertiesFilename)
        return property_dict

    def _read_dspace_properties(self):
        javaprops = JavaProperties()

        try:
            propertiesFilename = "%s/config/dspace.cfg" % (self.properties["dspace.dir"])
            javaprops.load(open(propertiesFilename))
            property_dict = javaprops.get_property_dict()
            logger.debug("Read succesfully property file %s" % propertiesFilename)
        except (FileNotFoundError, UnboundLocalError):
            logger.exception("Error while trying to read properties file %s" % propertiesFilename)
            raise

        try:
            propertiesFilename = "%s/config/local.cfg" % (self.properties["dspace.dir"])
            javaprops.load(open(propertiesFilename))
            property_dict = javaprops.get_property_dict()
            logger.debug("Read succesfully property file %s" % propertiesFilename)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not read property file %s" % propertiesFilename)
            pass

        return property_dict

    def _find_solr_server(self):

        # Find server
        solrServer = None
        response = None
        search_path = [
            self.properties['solr.server'] if 'solr.server' in self.properties.keys() else None,
            self.dspaceProperties['solr.server'] if 'solr.server' in self.dspaceProperties.keys() else None
            ]
        for path in search_path:
            if path is None:
                continue
            url = path + "/statistics/admin/ping?wt=json"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    solrServer = path
                    break
            except:
                pass

        if solrServer is not None:
            logger.debug("Solr Server found at %s" % solrServer)
        else:
            logger.exception("Solr Server not found in search path: %s" % search_path)
            raise

        # Test Connection
        try:
            status = json.loads(response.text)["status"]
            logger.debug("Solr Statistics Core Status: %s" % status)
        except (KeyError, json.decoder.JSONDecodeError):
            logger.exception("Could not read Solr Statistics Core Status from %s" % solrServer)
            raise

        if status != "OK":
            logger.error("Solr Statistics Core Not Ready")
            raise RuntimeError
        return solrServer

    def _load_history(self):
        javaprops = JavaProperties()
        property_dict = dict(lastTrackedEventTimestamp=None)
        historyFileName = "{}/.{}".format(SAVE_DIR, self.repoName)

        try:
            with open(historyFileName) as f:
                javaprops.load(f)
            property_dict = javaprops.get_property_dict()
            logger.debug("Read succesfully history file %s" % historyFileName)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not read history file %s" % historyFileName)
            pass

        return property_dict


    def save_to_history(self, key, value):
        javaprops = JavaProperties()
        historyFileName = "{}/.{}".format(SAVE_DIR, self.repoName)

        try:
            with open(historyFileName) as f:
                javaprops.load(f)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not read history file %s" % historyFileName)
            pass

        javaprops.set_property(key, value)

        try:
            basedir = os.path.dirname(historyFileName)
            if not os.path.exists(basedir):
                os.makedirs(basedir)
            with open(historyFileName, mode='w') as f:
                javaprops.store(f)
            self.history = javaprops.get_property_dict()
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not save to history file %s" % historyFileName)
            raise

        return


class DSpaceDB:

    def __init__(self, jdbcUrl, username, password, schema, dSpaceMajorVersion):
        self.schema = schema

        # Parse jdbc url
        # Postgres template: jdbc:postgresql://localhost:5432/dspace
        # Oracle template: jdbc:oracle:thin:@//localhost:1521/xe
        m = re.match("^jdbc:(postgresql|oracle):[^\/]*\/\/([^:]+):(\d+)/(.*)$", jdbcUrl)
        if m is None:
            logger.error("Could not parse db.url string: %s" % jdbcUrl)
            raise ValueError

        (engine, hostname, port, database) = m.group(1, 2, 3, 4)

        if engine != "postgresql":
            logger.error("DB Engine not yet supported: %s" % engine)
            raise NotImplementedError

        self.connString = '{engine}://{username}:{password}@{hostname}:{port}/{database}'
        self.connString = self.connString.format(
                engine=engine,
                username=username,
                password=password,
                hostname=hostname,
                port=port,
                database=database,
                )
        logger.debug('DB Connection String: ' + self.connString)
        try:
            self.conn = sqlalchemy.create_engine(self.connString).connect()
            logger.debug('DB Connection established successfully.')
        except sqlalchemy.exc.OperationalError:
            logger.exception("Could not connect to DB.")
            raise

        self._dfResources = pd.DataFrame(columns=['id', 'record_title', 'handle', 'is_download', 'owning_item', 'sequence_id', 'filename']).set_index('id')

        if dSpaceMajorVersion == '5':
            self._queryDownloadSQL = """
            SELECT mv.resource_id AS id,
                   mv2.text_value AS record_title,
                   h.handle AS handle,
                   true AS is_download,
                   i.item_id AS owning_item,
                   b.sequence_id AS sequence_id,
                   mv.text_value AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN bitstream AS b ON mv.resource_id = b.bitstream_id
            RIGHT JOIN bundle2bitstream AS bb ON b.bitstream_id = bb.bitstream_id
            RIGHT JOIN item2bundle AS i ON i.bundle_id = bb.bundle_id
            RIGHT JOIN handle AS h ON h.resource_id = i.item_id
            RIGHT JOIN metadatavalue AS mv2 ON mv2.resource_id = i.item_id
            WHERE mv.metadata_field_id = {dcTitleId}
              AND mv.resource_type_id = 0
              AND b.sequence_id IS NOT NULL
              AND b.deleted = FALSE
              AND mv2.metadata_field_id = {dcTitleId}
              AND mv2.resource_type_id=2
              AND mv.resource_id = {bitstreamId};
            """
            self._queryItemSQL = """
                SELECT mv.resource_id AS id,
                       mv.text_value AS record_title,
                       h.handle AS handle,
                       false AS is_download,
                       NULL AS owning_item,
                       NULL AS sequence_id,
                       NULL AS filename
                FROM metadatavalue AS mv
                RIGHT JOIN handle AS h ON h.resource_id = mv.resource_id
                WHERE metadata_field_id = {dcTitleId}
                  AND mv.resource_type_id=2
                  AND h.resource_type_id=2
                  AND mv.resource_id = {itemId};
            """
        elif dSpaceMajorVersion == '6':
            self._queryDownloadSQL = """
            SELECT mv.dspace_object_id::text AS id,
                   mv2.text_value AS record_title,
                   h.handle AS handle,
                   true AS is_download,
                   i.item_id::text AS owning_item,
                   b.sequence_id AS sequence_id,
                   mv.text_value AS filename
            FROM metadatavalue AS mv
            RIGHT JOIN bitstream AS b ON mv.dspace_object_id = b.uuid
            RIGHT JOIN bundle2bitstream AS bb ON b.uuid = bb.bitstream_id
            RIGHT JOIN item2bundle AS i ON i.bundle_id = bb.bundle_id
            RIGHT JOIN handle AS h ON h.resource_id = i.item_id
            RIGHT JOIN metadatavalue AS mv2 ON mv2.dspace_object_id = i.item_id
            WHERE mv.metadata_field_id = {dcTitleId}
              AND b.sequence_id IS NOT NULL
              AND b.deleted = FALSE
              AND mv2.metadata_field_id = {dcTitleId}
              AND mv.dspace_object_id::text = '{bitstreamId}';
            """
            self._queryItemSQL = """
                SELECT mv.dspace_object_id::text AS id,
                       mv.text_value AS record_title,
                       h.handle AS handle,
                       false AS is_download,
                       NULL AS owning_item,
                       NULL AS sequence_id,
                       NULL AS filename
                FROM metadatavalue AS mv
                RIGHT JOIN handle AS h ON h.resource_id = mv.dspace_object_id
                WHERE metadata_field_id = {dcTitleId}
                  AND h.resource_type_id=2
                  AND mv.dspace_object_id::text = '{itemId}';
            """
        else:
            logger.error('Only implemented values for dspace.majorVersion are 5 and 6. Received {}'.format(dSpaceMajorVersion))
            raise NotImplementedError

        self._dcTitleId = self.getDcTitleId()


    def getDcTitleId(self):
        resource_id_field = 'resource_id'
        SQL = """
        SELECT metadata_field_id AS "dcTitleId"
             FROM metadatafieldregistry mfr,
                  metadataschemaregistry msr
             WHERE mfr.metadata_schema_id = msr.metadata_schema_id
               AND short_id = 'dc'
               AND element = 'title'
               AND qualifier IS NULL;
        """
        dfRecord = pd.read_sql(SQL, self.conn)
        if len(dfRecord) != 1:
            logger.error('Could not recover DC Title metadata field id from db')
            raise RuntimeError
        dcTitleId = dfRecord.dcTitleId[0]
        return dcTitleId


    def queryDownload(self, bitstreamId, owningItem):
        if bitstreamId not in self._dfResources.index.values:
            SQL = self._queryDownloadSQL.format(
                    dcTitleId = self._dcTitleId,
                    bitstreamId = bitstreamId
            )
            dfRecord = pd.read_sql(SQL, self.conn).set_index('id')
            if len(dfRecord) != 1:
                logger.debug('Could not recover data for bitstream {} from db'.format(bitstreamId))
                return None
#            if dfRecord.loc[bitstreamId, 'owning_item'] != owningItem and not(type(owningItem) == list and dfRecord.loc[bitstreamId, 'owning_item'] == owningItem[0]): # DSpace 6 logs owningItem as a 1-element array in SOLR
#                logger.debug('Owning Item mismatch for bitstream {} from db ({}, {})'.format(bitstreamId, dfRecord.loc[bitstreamId, 'owning_item'], owningItem[0]))
#                return None
            logger.debug('Successfully recovered data for bitstream {} from db'.format(bitstreamId))
            self._dfResources = self._dfResources.append(dfRecord)

        return self._dfResources.loc[bitstreamId].to_dict()

    def queryItem(self, itemId):
        if itemId not in self._dfResources.index.values:
            SQL = self._queryItemSQL.format(
                    dcTitleId = self._dcTitleId,
                    itemId = itemId
            )
            dfRecord = pd.read_sql(SQL, self.conn).set_index('id')
            if len(dfRecord) != 1:
                logger.debug('Could not recover data for item {} from db'.format(itemId))
                return None
            logger.debug('Successfully recovered data for item {} from db'.format(itemId))
            self._dfResources = self._dfResources.append(dfRecord)
        return self._dfResources.loc[itemId].to_dict()


def main(args, loglevel):

    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)
    logger.debug("Verbose: %s" % args.verbose)
    logger.debug("Repositories: %s" % args.repositories)
    logger.debug("Configuration Directory: %s" % args.config_dir)
    logger.debug("Limit: %s" % args.limit)
    if args.date_from:
        logger.debug("Date from: %s" % args.date_from.strftime("%Y-%m-%d"))

    for repoName in args.repositories:
        logger.debug("START: %s" % repoName)
        propertiesFilename = "%s/%s.properties" % (args.config_dir, repoName)
        repo = Repository(repoName, propertiesFilename)
        eventPipeline = EventPipelineBuilder(args).build(repo)
        eventPipeline.run()
        logger.debug("END: %s" % repoName)

def parse_args():


    def valid_date_type(arg_date_str):
        """custom argparse *date* type for user dates values given from the command line"""
        # https://gist.github.com/monkut/e60eea811ef085a6540f
        try:
            return datetime.strptime(arg_date_str, "%Y-%m-%d")
        except ValueError:
            msg = "Given Date ({0}) not valid! Expected format, YYYY-MM-DD!".format(arg_date_str)
            raise argparse.ArgumentTypeError(msg)

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("repositories",
                        metavar="REPOSITORYNAME",
                        nargs="+",
                        help="name of repositories to collect usage stats from. Should match the name of the corresponding .properties files in config dir")
    parser.add_argument("-f", "--date_from",
                        type=valid_date_type,
                        metavar="YYYY-MM-DD",
                        default=None,
                        help="collect events only from this date")
    parser.add_argument("-l",
                        "--limit",
                        metavar="LIMIT",
                        type=int,
                        help="max number of events to output")
    parser.add_argument("-c",
                        "--config_dir",
                        metavar="DIR",
                        default="{}/config".format(os.path.dirname(os.path.realpath(__file__))),
                        help="path to configuration directory")
    parser.add_argument("-v",
                        "--verbose",
                        help="increase output verbosity",
                        default=False,
                        action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING

    main(args, loglevel)

