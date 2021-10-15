#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace Repository instance config """

import logging
logger = logging.getLogger()

from pyjavaprops.javaproperties import JavaProperties
import json
import requests
import os
import sys
from datetime import datetime
from datetime import date

try:
    from .dspacedb import DSpaceDB
except Exception: #ImportError
    from dspacedb import DSpaceDB

SAVE_DIR = os.path.expanduser('~') + "/dspace-stats-collector/var/timestamp"
DEFAULT_INSTALL_PATH = os.path.expanduser('~') + "/dspace-stats-collector"
DEFAULT_COLLECTOR_COMMAND_NAME="dspace-stats-collector"
DEFAULT_CONFIG_PATH = DEFAULT_INSTALL_PATH + "/config"

SOLR_STATS_CORE_NAME = "statistics"
TIMESTAMP_PATTERN = "%Y-%m-%dT00:00:00.000Z"
SOLR_QUERY_ROWS_SIZE = 10
DEFAULT_OUPUT_LIMIT = 100
COUNTER_ROBOTS_FILE = 'COUNTER_Robots_list.json'
LAST_TRACKED_TIMESTAMP_HISTORY_FIELD = 'lastTrackedEventTimestamp'
DEFAULT_ANONYMIZE_IP_MASK = '255.255.255.255'

class History:

    
    #self.history = self._load_history()

    def __init__(self, base_path, reponame):
        self.javaprops = JavaProperties()
        self.base_path = base_path
        self.reponame = reponame
        self.property_dict = {LAST_TRACKED_TIMESTAMP_HISTORY_FIELD:None}
        self.filename = "{}/{}".format(base_path, reponame + ".dat")

        try:
            with open(self.filename) as f:
                self.javaprops.load(f)
            self.property_dict = self.javaprops.get_property_dict()
            logger.debug("Read succesfully history file %s" % self.filename)
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("History file %s does not exist. Creating one..." % self.filename)

    def save_last_tracked_timestamp(self, timestamp):
        try:
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path)
            self.javaprops.set_property(LAST_TRACKED_TIMESTAMP_HISTORY_FIELD, timestamp)    
            with open(self.filename, mode='w') as f:
                self.javaprops.store(f)
            self.property_dict = self.javaprops.get_property_dict()    
        except (FileNotFoundError, UnboundLocalError):
            logger.debug("Could not save to history file %s" % self.filename)
            raise

    def get_last_tracked_timestamp(self):
        return self.property_dict.get(LAST_TRACKED_TIMESTAMP_HISTORY_FIELD, None)


class ConfigurationContext:

    defaultInstallPath = DEFAULT_INSTALL_PATH
    defaultConfigPath = DEFAULT_CONFIG_PATH
    defaultCollectorCommand = DEFAULT_COLLECTOR_COMMAND_NAME
    defaultRepository = 'default'
    defaultOuputLimit = DEFAULT_OUPUT_LIMIT
    counterRobotsFileName = COUNTER_ROBOTS_FILE

    def __init__(self, repoName, commandLineArgs):
        
        self.repoName = repoName
        self.propertiesFilename = ConfigurationContext.getPropertiesFieldPath(commandLineArgs.config_dir, repoName)

        self.properties = self._read_properties()
        self.dspaceProperties = self._read_dspace_properties()

        #History
        self.history = History(SAVE_DIR, repoName)

        # Solr Context
        if commandLineArgs.archived_core != None:
            self.solrStatsCoreName = SOLR_STATS_CORE_NAME + "-" + commandLineArgs.archived_core
        else:
            self.solrStatsCoreName = SOLR_STATS_CORE_NAME

        self.solrServerURL = self._find_solr_server()
        self.solrStatsCoreURL = self.solrServerURL + "/" + self.solrStatsCoreName

        # COUNTER Robots
        self.counterRobotsFilename = ("%s/" + ConfigurationContext.counterRobotsFileName) % (commandLineArgs.config_dir)

        # Solr Query parameters -     
        if commandLineArgs.date_from:
            self.solrQueryInitialTimestamp = commandLineArgs.date_from.strftime(TIMESTAMP_PATTERN)
        elif self.history.get_last_tracked_timestamp() != None:
            self.solrQueryInitialTimestamp = self.history.get_last_tracked_timestamp()
            logger.debug('Loaded initialTimestamp from history: {}'.format(self.solrQueryInitialTimestamp))
        else:
            logger.debug('No initial date provided, using current date.')
            self.solrQueryInitialTimestamp = date.today().strftime(TIMESTAMP_PATTERN)
        
        if commandLineArgs.date_until:
            self.solrQueryUntilDate = commandLineArgs.date_until.strftime(TIMESTAMP_PATTERN)
        else:
            self.solrQueryUntilDate = None

        self.solrQueryRows= SOLR_QUERY_ROWS_SIZE
        
        self.maxEventsToSend = int(self.properties['max.eventsToSend'])
        logger.debug("Limit: %s" % self.maxEventsToSend)
        
        self.dspaceMajorVersion = self.properties['dspace.majorVersion']

        self.anonymize_ip_mask = self.properties.get('anonymize.ip_mask', DEFAULT_ANONYMIZE_IP_MASK)

        self.db = DSpaceDB(
                        self.dspaceProperties['db.url'],
                        self.dspaceProperties['db.username'],
                        self.dspaceProperties['db.password'],
                        self.dspaceProperties.get('db.schema','public'),
                        self.dspaceMajorVersion
                    )

    @staticmethod
    def getPropertiesFieldPath(config_dir, repoName):
        return "%s/%s.properties" % (config_dir, repoName)

    def close(self):
        logger.debug("Closing resources")
        self.db.close()

    ############################################### public methods   ###########################################
    def getMatomoOutputSize(self):
        return int(self.properties['matomo.batchSize'])

    def getMatomoTokenAuth(self):
        return self.properties['matomo.token_auth']

    def getMatomoUrl(self):
        return self.properties['matomo.trackerUrl']

    def getSolrLimit(self):
        return int(self.properties['solr.limit'])
    
    def getDspaceMajorVersion(self):
        return int(self.properties['dspace.majorVersion'])

    ################################################ private methods ##########################################
    def _read_properties(self):
        javaprops = JavaProperties()

        try:
            javaprops.load(open(self.propertiesFilename))
            property_dict = javaprops.get_property_dict()
        except (FileNotFoundError, UnboundLocalError):
            logger.error("Error while trying to read properties file %s" % self.propertiesFilename)
            sys.exit()
            #raise

        logger.debug("Read succesfully property file %s" % self.propertiesFilename)
        return property_dict

    def _read_dspace_properties(self):
        javaprops = JavaProperties()

        if self.getDspaceMajorVersion() == 6:
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

        else:
            try:
                propertiesFilename = "%s/config/dspace.cfg" % (self.properties["dspace.dir"])
                javaprops.load(open(propertiesFilename))
                property_dict = javaprops.get_property_dict()
                logger.debug("Read succesfully property file %s" % propertiesFilename)
            except (FileNotFoundError, UnboundLocalError):
                logger.exception("Error while trying to read properties file %s" % propertiesFilename)
                raise

        return property_dict

    def _find_solr_server(self):

        # Find server
        solrServerURL = None
        response = None
        search_path = [
            self.properties['solr.server'] if 'solr.server' in self.properties.keys() else None,
            self.dspaceProperties['solr.server'] if 'solr.server' in self.dspaceProperties.keys() else None
            ]
        for path in search_path:
            if path is None:
                continue
            url = path + "/" + self.solrStatsCoreName + "/admin/ping?wt=json"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    solrServerURL = path
                    break
            except:
                pass

        if solrServerURL is not None:
            logger.debug("Solr Server found at %s" % solrServerURL)
        else:
            logger.exception("Solr Server not found in search path: %s" % search_path)
            raise

        # Test Connection
        try:
            status = json.loads(response.text)["status"]
            logger.debug("Solr Statistics Core Status: %s" % status)
        except (KeyError, json.decoder.JSONDecodeError):
            logger.exception("Could not read Solr Statistics Core Status from %s" % solrServerURL)
            raise

        if status != "OK":
            logger.error("Solr Statistics Core Not Ready")
            raise RuntimeError
        else: # issue a core commit command, wait until completion
            url = solrServerURL + "/" + self.solrStatsCoreName + "/update?commit=true"
            try:
                logger.debug("Solr :: Committing changes in %s core" % self.solrStatsCoreName)
                response = requests.get(url)
            except:
                logger.error("Commit to Solr server failed")

        return solrServerURL
    

    
