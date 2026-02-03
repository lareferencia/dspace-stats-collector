#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration loader."""

import logging
import os
import sys
import json
import requests
from datetime import date
from pyjavaprops.javaproperties import JavaProperties
from .settings import CollectorSettings, MatomoSettings, SolrSettings, DSpaceSettings

logger = logging.getLogger(__name__)

DEFAULT_SOLR_SERVER = "http://localhost:8080/solr"
DEFAULT_SOLR_STATS_CORE_NAME = "statistics"
DEFAULT_ANONYMIZE_IP_MASK = '255.255.255.255'


class ConfigLoader:
    """Loads configuration from properties files."""

    def __init__(self, config_dir: str, repo_name: str, args):
        self.config_dir = config_dir
        self.repo_name = repo_name
        self.args = args

    def load_settings(self) -> CollectorSettings:
        # 1. Load collector properties (repo.properties)
        props_file = f"{self.config_dir}/{self.repo_name}.properties"
        props = self._read_properties(props_file)

        # 2. Determine DSpace version and Dir
        dspace_dir = props.get('dspace.dir')
        dspace_version = props.get('dspace.majorVersion')

        # 3. Load DSpace properties (dspace.cfg / local.cfg)
        dspace_props = self._read_dspace_properties(dspace_dir, dspace_version)

        # 4. Construct Sub-Settings
        matomo_settings = MatomoSettings(
            url=props['matomo.trackerUrl'],
            token_auth=props['matomo.token_auth'],
            site_id=props['matomo.idSite'],
            repository_id=props.get('matomo.repositoryId'),
            batch_size=int(props.get('matomo.batchSize', 50)),
            rec=props.get('matomo.rec', "1"),
            country_iso=props.get('matomo.countryISO'),
            verify_ssl=self._parse_bool(props.get('matomo.verifySSL', True))
        )

        # Solr Logic
        solr_core_name = props.get('solr.core', DEFAULT_SOLR_STATS_CORE_NAME)
        if hasattr(self.args, 'archived_core') and self.args.archived_core:
            solr_core_name += f"-{self.args.archived_core}"

        solr_url = self._find_solr_server(props, dspace_props, solr_core_name)
        
        # Date handling
        date_from = None
        if hasattr(self.args, 'date_from') and self.args.date_from:
             date_from = self.args.date_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        date_until = None
        if hasattr(self.args, 'date_until') and self.args.date_until:
             date_until = self.args.date_until.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        solr_settings = SolrSettings(
            server_url=solr_url,
            core_name=solr_core_name,
            query_rows=int(props.get('solr.queryRows', 500)),
            date_from=date_from,
            date_until=date_until
        )

        dspace_settings = DSpaceSettings(
            install_dir=dspace_dir,
            major_version=dspace_version,
            db_url=dspace_props.get('db.url'),
            db_username=dspace_props.get('db.username'),
            db_password=dspace_props.get('db.password'),
            canonical_prefix=dspace_props.get('handle.canonical.prefix', 'http://hdl.handle.net/'),
            hostname=dspace_props.get('dspace.hostname'),
            url=dspace_props.get('dspace.url'),
            server_url=dspace_props.get('dspace.server.url'),
            ui_url=dspace_props.get('dspace.ui.url'),
        )

        max_events = int(props.get('max.eventsToSend', 100))
        if hasattr(self.args, 'no_limit') and self.args.no_limit:
            max_events = sys.maxsize

        return CollectorSettings(
            matomo=matomo_settings,
            solr=solr_settings,
            dspace=dspace_settings,
            max_events=max_events,
            anonymize_ip_mask=props.get('anonymize.ip_mask', DEFAULT_ANONYMIZE_IP_MASK),
            repo_properties=dict(props),
            dspace_properties=dict(dspace_props),
        )

    def _parse_bool(self, value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _read_properties(self, filename: str) -> dict:
        javaprops = JavaProperties()
        try:
            with open(filename) as f:
                javaprops.load(f)
            return javaprops.get_property_dict()
        except FileNotFoundError:
            logger.error(f"Properties file not found: {filename}")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"Error reading {filename}: {e}")
            sys.exit(1)

    def _read_dspace_properties(self, dspace_dir: str, version: str) -> dict:
        javaprops = JavaProperties()
        props = {}

        # Define potential config paths based on logic in original configcontext
        paths = []
        if version.startswith('6') or version.startswith('7'):
            paths.append(f"{dspace_dir}/config/dspace.cfg")
            paths.append(f"{dspace_dir}/config/local.cfg")
        elif version == '5c':
             paths.append(f"{dspace_dir}/build.properties")
        else:
             paths.append(f"{dspace_dir}/config/dspace.cfg")

        for path in paths:
            try:
                with open(path) as f:
                    javaprops.load(f)
                props.update(javaprops.get_property_dict())
                logger.debug(f"Loaded DSpace properties from {path}")
            except FileNotFoundError:
                if "local.cfg" in path:
                    logger.debug(f"Optional file {path} not found")
                else:
                    logger.error(f"Required file {path} not found")
                    # Original code raised here for required files
                    sys.exit(1)
        
        return props

    def _find_solr_server(self, props, dspace_props, core_name) -> str:
        # Search logic similar to original
        search_paths = [
            ('dspace config', dspace_props.get('solr.server')),
            ('collector config', props.get('solr.server')),
            ('default value', DEFAULT_SOLR_SERVER)
        ]

        found_url = None
        for source, path in search_paths:
            if not path:
                continue
            
            # Check ping
            ping_url = f"{path}/{core_name}/admin/ping?wt=json"
            try:
                resp = requests.get(ping_url, timeout=5)
                if resp.status_code == 200:
                    found_url = path
                    logger.debug(f"Found Solr server at {path} ({source})")
                    break
            except Exception:
                 logger.debug(f"Could not connect to Solr at {ping_url}")
        
        if not found_url:
            raise RuntimeError(f"Solr server not found. Checked: {search_paths}")

        return found_url
