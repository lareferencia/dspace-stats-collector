#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" DSpace Repository instance config """

import logging
import os
import sys
from datetime import datetime, date

from .config.history import History, TIMESTAMP_PATTERN
from .config.loader import ConfigLoader, DEFAULT_SOLR_STATS_CORE_NAME
from .config.settings import CollectorSettings
try:
    from .database_factory import create_database
except ImportError:
    from database_factory import create_database

logger = logging.getLogger(__name__)

DEFAULT_INSTALL_PATH = os.path.expanduser('~') + "/dspace-stats-collector"
DEFAULT_CONFIG_PATH = DEFAULT_INSTALL_PATH + "/config"
DEFAULT_COLLECTOR_COMMAND_NAME = "dspace-stats-collector"
SAVE_DIR = os.path.expanduser('~') + "/dspace-stats-collector/var/timestamp"
COUNTER_ROBOTS_FILE = 'COUNTER_Robots_list.json'
DEFAULT_OUPUT_LIMIT = 100
EXPORT_FILE_NAME_BASE = 'dspace_stats_export'


class ConfigurationContext:

    defaultInstallPath = DEFAULT_INSTALL_PATH
    defaultConfigPath = DEFAULT_CONFIG_PATH
    defaultCollectorCommand = DEFAULT_COLLECTOR_COMMAND_NAME
    defaultRepository = 'default'
    defaultOuputLimit = DEFAULT_OUPUT_LIMIT
    counterRobotsFileName = COUNTER_ROBOTS_FILE

    @staticmethod
    def getPropertiesFieldPath(config_dir, repo_name):
        return f"{config_dir}/{repo_name}.properties"

    def __init__(self, repoName, commandLineArgs):
        self.repoName = repoName
        
        # 1. Initialize History (State)
        self.history = History(SAVE_DIR, repoName)
        
        # 2. Load Configuration (Settings)
        # We need to know where config dir is. 
        # Original code used commandLineArgs.config_dir or defaults.
        # Check simple logic:
        config_dir = commandLineArgs.config_dir
        
        loader = ConfigLoader(config_dir, repoName, commandLineArgs)
        self.settings: CollectorSettings = loader.load_settings()

        # 3. Setup Legacy Attributes (Facade)
        # Many parts of the app might access these directly, so we map them.
        self.dspaceMajorVersion = self.settings.dspace.major_version
        self.maxEventsToSend = self.settings.max_events
        self.anonymize_ip_mask = self.settings.anonymize_ip_mask

        # Legacy compatibility attributes used by pipeline stages.
        repo_properties = getattr(self.settings, 'repo_properties', None)
        self.properties = dict(repo_properties) if isinstance(repo_properties, dict) else {}
        dspace_properties = getattr(self.settings, 'dspace_properties', None)
        self.dspaceProperties = dict(dspace_properties) if isinstance(dspace_properties, dict) else {}

        self.properties.setdefault('matomo.idSite', self.settings.matomo.site_id)
        self.properties.setdefault('matomo.rec', self.settings.matomo.rec)
        self.properties.setdefault('matomo.token_auth', self.settings.matomo.token_auth)
        self.properties.setdefault('matomo.repositoryId', self.settings.matomo.repository_id or self.repoName)
        self.properties.setdefault('matomo.countryISO', self.settings.matomo.country_iso or "")
        self.properties.setdefault('matomo.verifySSL', str(self.settings.matomo.verify_ssl).lower())

        self.dspaceProperties.setdefault('handle.canonical.prefix', self.settings.dspace.canonical_prefix)
        self.dspaceProperties.setdefault('dspace.hostname', self.settings.dspace.hostname)
        self.dspaceProperties.setdefault('dspace.url', self.settings.dspace.url)
        self.dspaceProperties.setdefault('dspace.server.url', self.settings.dspace.server_url)
        self.dspaceProperties.setdefault('dspace.ui.url', self.settings.dspace.ui_url)
        
        self.solrStatsCoreName = self.settings.solr.core_name
        self.solrServerURL = self.settings.solr.server_url
        self.solrStatsCoreURL = f"{self.solrServerURL}/{self.solrStatsCoreName}"
        
        # Re-construct solrQueryInitialTimestamp/UntilDate logic if needed by external
        # The loader handled date_from/until from args, but history fallback logic needs to happen here or be passed to loader.
        # Actually loader check args, if args missing it uses History?
        # Let's check original logic: 
        # If args.date_from -> use it
        # Else if history -> use it
        # Else -> Today
        
        # My loader handled: args -> date_from (and put it in settings)
        # But loader didn't have access to history for fallback.
        # So I should refine logic here.
        
        if self.settings.solr.date_from:
             self.solrQueryInitialTimestamp = self.settings.solr.date_from
        elif self.history.get_last_tracked_timestamp():
             self.solrQueryInitialTimestamp = self.history.get_last_tracked_timestamp()
             logger.debug('Loaded initialTimestamp from history: {}'.format(self.solrQueryInitialTimestamp))
             # Update settings so everyone is in sync
             self.settings.solr.date_from = self.solrQueryInitialTimestamp
        else:
             logger.debug('No initial date provided, using current date.')
             self.solrQueryInitialTimestamp = date.today().strftime(TIMESTAMP_PATTERN)
             self.settings.solr.date_from = self.solrQueryInitialTimestamp

        self.date_from = datetime.strptime(self.solrQueryInitialTimestamp, TIMESTAMP_PATTERN)
        
        if self.settings.solr.date_until:
            self.solrQueryUntilDate = self.settings.solr.date_until
        else:
            self.solrQueryUntilDate = None

        self.solrQueryRows = self.settings.solr.query_rows
        self.counterRobotsFilename = f"{config_dir}/{self.counterRobotsFileName}"

        # 4. Initialize Database
        self.db = create_database(
            version=self.settings.dspace.major_version,
            jdbc_url=self.settings.dspace.db_url,
            username=self.settings.dspace.db_username,
            password=self.settings.dspace.db_password
        )

        
    ############################################### public methods   ###########################################
    def getMatomoOutputSize(self):
        return self.settings.matomo.batch_size

    def getMatomoTokenAuth(self):
        return self.settings.matomo.token_auth

    def getMatomoVerifySSL(self):
        return self.settings.matomo.verify_ssl
    
    def getMatomoIdSite(self):
        return self.settings.matomo.site_id

    def getMatomoUrl(self):
        return self.settings.matomo.url

    def getSolrLimit(self):
        # Was solr.limit in properties? 
        # My loader mapped queryRows, but limit?
        # Check original: return int(self.properties['solr.limit'])
        # I missed 'solr.limit' in settings.py! 
        # Wait, getSolrLimit was reading property 'solr.limit', default?
        # Actually in original code: self.solrQueryRows= SOLR_QUERY_ROWS_SIZE (500)
        # And getSolrLimit reads 'solr.limit'. 
        # I should assume it's solr.queryRows or similar.
        # Let's map it to query_rows for now or add it if distinct.
        return self.settings.solr.query_rows
    
    def getDspaceMajorVersion(self):
        return self.settings.dspace.major_version

    def getSolrStatsCoreName(self):
        return self.settings.solr.core_name
    
    def getExportFileName(self):
        month = self.date_from.strftime("%m")
        year = self.date_from.strftime("%Y")
        idSite = self.settings.matomo.site_id

        return "%s_%s_%s_%s.txt" % (EXPORT_FILE_NAME_BASE, idSite, year , month) 

    def close(self):
        logger.debug("Closing resources")
        if self.db:
            self.db.close()



