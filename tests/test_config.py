#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Configuration Refactoring."""

import pytest
import os
from unittest.mock import MagicMock, patch
from dspace_stats_collector.config.history import History
from dspace_stats_collector.config.loader import ConfigLoader
from dspace_stats_collector.config.settings import CollectorSettings
from dspace_stats_collector.configcontext import ConfigurationContext

class TestHistory:
    
    def test_save_and_load_timestamp(self, tmp_path):
        history = History(str(tmp_path), "test_repo")
        ts = "2026-01-13T12:00:00.000Z"
        
        history.save_last_tracked_timestamp(ts)
        
        # Reload
        history2 = History(str(tmp_path), "test_repo")
        loaded_ts = history2.get_last_tracked_timestamp()
        
        # Expect normalized format with microseconds
        assert loaded_ts == "2026-01-13T12:00:00.000000Z"

    def test_handles_missing_file_gracefully(self, tmp_path):
        history = History(str(tmp_path), "non_existent")
        assert history.get_last_tracked_timestamp() is None


class TestConfigLoader:
    
    @patch('dspace_stats_collector.config.loader.JavaProperties')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_load_settings(self, mock_exists, mock_open, mock_javaprops):
        # Setup Mocks
        mock_javaprops_instance = mock_javaprops.return_value
        
        # Mock Repo Properties
        repo_props = {
            'dspace.dir': '/opt/dspace',
            'dspace.majorVersion': '7',
            'matomo.trackerUrl': 'http://matomo.org',
            'matomo.token_auth': 'ABC',
            'matomo.idSite': '1',
            'matomo.batchSize': '50',
            'solr.core': 'statistics',
            'max.eventsToSend': '100'
        }
        
        # Mock DSpace Properties
        dspace_props = {
            'db.url': 'jdbc:postgresql://localhost:5432/dspace',
            'db.username': 'dspace',
            'db.password': 'dspace',
            'dspace.hostname': 'dspace.org',
            'dspace.url': 'https://dspace.org',
            'dspace.server.url': 'https://api.dspace.org',
            'dspace.ui.url': 'https://dspace.org',
             'solr.server': 'http://localhost:8983/solr'
        }
        
        # Sequential returns for get_property_dict
        # 1. Repo props
        # 2. DSpace props (from dspace.cfg)
        # 3. DSpace props (from local.cfg - optional)
        mock_javaprops_instance.get_property_dict.side_effect = [repo_props, dspace_props, {}]
        
        # Mock Requests for Solr Ping
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            # Helper to ignore reading from file
            # Since we mock load(), open() context is just a dummy
            
            loader = ConfigLoader('/config', 'repo', MagicMock())
            settings = loader.load_settings()
            
            assert isinstance(settings, CollectorSettings)
            assert settings.dspace.install_dir == '/opt/dspace'
            assert settings.matomo.url == 'http://matomo.org'
            assert settings.solr.server_url == 'http://localhost:8983/solr'
            assert settings.dspace.major_version == '7'

class TestConfigurationContextFacade:
    
    @patch('dspace_stats_collector.configcontext.ConfigLoader')
    @patch('dspace_stats_collector.configcontext.History')
    @patch('dspace_stats_collector.configcontext.create_database')
    def test_delegation(self, mock_create_db, mock_history, mock_loader_cls):
        # Mock Loader returning settings
        mock_loader = mock_loader_cls.return_value
        
        # Configure Settings Mock with explicit nested Mocks
        mock_settings = MagicMock()
        
        mock_dspace = MagicMock()
        mock_dspace.major_version = '7'
        
        mock_matomo = MagicMock()
        mock_matomo.url = 'http://matomo.org'
        
        mock_solr = MagicMock()
        mock_solr.core_name = 'stats'
        mock_solr.server_url = 'http://solr.org' # Add this to prevent Mock
        mock_solr.date_from = None
        mock_solr.date_until = None
        
        mock_settings.dspace = mock_dspace
        mock_settings.matomo = mock_matomo
        mock_settings.solr = mock_solr

        mock_loader.load_settings.return_value = mock_settings
        
        # Configure History Mock to avoid returning MagicMock (which is truthy/non-string)
        mock_history_instance = mock_history.return_value
        mock_history_instance.get_last_tracked_timestamp.return_value = None
        
        mock_args = MagicMock()
        mock_args.config_dir = '/tmp'
        mock_args.date_from = None
        mock_args.date_until = None
        
        ctx = ConfigurationContext('repo', mock_args)
        
        # Check Facade methods access Settings
        assert ctx.getMatomoUrl() == 'http://matomo.org'
        assert ctx.getDspaceMajorVersion() == '7'
        assert ctx.getSolrStatsCoreName() == 'stats'
        
        # Check initialization
        mock_loader.load_settings.assert_called_once()
        mock_history.assert_called_once()
