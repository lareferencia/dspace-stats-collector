#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Dspace Repository instance config """

import logging
logger = logging.getLogger()

from pyjavaprops.javaproperties import JavaProperties
from dspacedb import DSpaceDB
import json
import requests
import os


SAVE_DIR = os.path.expanduser('~') + '/.dspace_stats_collector'
SOLR_STATS_CORE_NAME = "statistics"
TIMESTAMP_PATTERN = "%Y-%m-%dT00:00:00.000Z"
HISTORY_LAST_TIMESTAMP_FIELDNAME = 'lastTrackedEventTimestamp'
SOLR_QUERY_ROWS_SIZE = 10

class ConfigurationContext:

    def __init__(self, repoName, commandLineArgs):
        
        self.repoName = repoName
        self.propertiesFilename = "%s/%s.properties" % (commandLineArgs.config_dir, repoName)

        self.properties = self._read_properties()
        self.dspaceProperties = self._read_dspace_properties()

        # history
        self.historyFilePath = SAVE_DIR
        self.history = self._load_history()

        # Solr Context
        self.solrStatsCoreName = SOLR_STATS_CORE_NAME
        self.solrServerURL = self._find_solr_server()
        self.solrStatsCoreURL = self.solrServerURL + "/" + self.solrStatsCoreName

        # Solr Query parameters -     
        if commandLineArgs.date_from:
            self.solrQueryInitialTimestamp = commandLineArgs.date_from.strftime(TIMESTAMP_PATTERN)
        elif 'lastTrackedEventTimestamp' in self.history.keys():
            self.solrQueryInitialTimestamp = self.history[HISTORY_LAST_TIMESTAMP_FIELDNAME]
            logger.debug('Loaded initialTimestamp from history: {}'.format(self.solrQueryInitialTimestamp))
        else:
            self.solrQueryInitialTimestamp = None

        self.solrQueryRows= SOLR_QUERY_ROWS_SIZE
        self.solrQueryLimit= commandLineArgs.limit
        
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

    def _load_history(self):
        javaprops = JavaProperties()
        property_dict = dict(lastTrackedEventTimestamp=None)
        historyFileName = "{}/.{}".format(self.historyFilePath, self.repoName)

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
        historyFileName = "{}/.{}".format(self.historyFilePath, self.repoName)

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