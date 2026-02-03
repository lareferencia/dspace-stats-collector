#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for MatomoFilter."""

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from dspace_stats_collector.matomooutput import MatomoFilter
from dspace_stats_collector.eventpipeline import Event

class TestMatomoFilter:

    def test_run_transforms_download_event(self, mock_config_context, sample_event):
        """Test transformation of a download event (type 0/is_download=True)."""
        matomo_filter = MatomoFilter(mock_config_context)
        
        # Verify sample event is a download
        assert sample_event._db['is_download'] is True
        
        # Run filter
        events = [sample_event]
        processed_events = list(matomo_filter.run(events))
        
        assert len(processed_events) == 1
        event = processed_events[0]
        
        # Check params
        params = event._matomoParams
        assert params['idsite'] == '1'
        assert params['action_name'] == 'Test Record Title'
        assert params['_id'] == 'session_123'
        assert params['ua'] == 'Mozilla/5.0 Test Agent'
        
        # Check Download URL format
        expected_url = "http://dspace.example.com/bitstream/12345/6789/1/test_file.pdf"
        assert params['download'] == expected_url
        assert params['url'] == expected_url
        
        # Check Custom Variables (cvar)
        assert '"oaipmhID", "oai:dspace.example.com:12345/6789"' in params['cvar']

    def test_run_transforms_item_view_event(self, mock_config_context, sample_event):
        """Test transformation of an item view event (type 2/is_download=False)."""
        matomo_filter = MatomoFilter(mock_config_context)
        
        # Modify sample event to be an item view
        sample_event._db['is_download'] = False
        sample_event._db['filename'] = None
        sample_event._db['sequence_id'] = None
        
        # Run filter
        events = [sample_event]
        processed_events = list(matomo_filter.run(events))
        
        event = processed_events[0]
        params = event._matomoParams
        
        # Check Item View URL format
        assert 'download' not in params
        assert params['url'] == "http://hdl.handle.net/12345/6789"

    def test_timestamp_parsing_with_millis(self, mock_config_context, sample_event):
        """Test parsing timestamp with milliseconds."""
        matomo_filter = MatomoFilter(mock_config_context)
        sample_event._src['time'] = "2026-01-13T15:30:45.123Z"
        
        processed_events = list(matomo_filter.run([sample_event]))
        params = processed_events[0]._matomoParams
        
        # Matomo format: YYYY-MM-DD HH:MM:SS
        assert params['cdt'] == "2026-01-13 15:30:45"

    def test_timestamp_parsing_without_millis(self, mock_config_context, sample_event):
        """Test parsing timestamp without milliseconds."""
        matomo_filter = MatomoFilter(mock_config_context)
        sample_event._src['time'] = "2026-01-13T15:30:45Z"
        
        processed_events = list(matomo_filter.run([sample_event]))
        params = processed_events[0]._matomoParams
        
        assert params['cdt'] == "2026-01-13 15:30:45"

    def test_dspace7_url_construction(self, mock_config_context, sample_event):
        """Test URL construction for DSpace 7."""
        # Setup DSpace 7 config
        mock_config_context.getDspaceMajorVersion.return_value = '7'
        mock_config_context.dspaceProperties['dspace.server.url'] = 'https://api.dspace.org'
        mock_config_context.dspaceProperties['dspace.ui.url'] = 'https://dspace.org'
        
        matomo_filter = MatomoFilter(mock_config_context)
        
        processed_events = list(matomo_filter.run([sample_event]))
        params = processed_events[0]._matomoParams
        
        # Check DSpace 7 specific URL construction
        # Expecting uses dspace.ui.url
        expected_url = "https://dspace.org/bitstream/12345/6789/1/test_file.pdf"
        assert params['download'] == expected_url
        
        # Check OAI ID uses server url (hostname)
        # In the code: oai:{dspaceHostname}:{handle}
        # For DSpace 7 code sets dspaceHostname = dspace.server.url
        assert '"oaipmhID", "oai:https://api.dspace.org:12345/6789"' in params['cvar']

    def test_run_with_typed_settings_context(self, sample_event):
        """MatomoFilter works when only typed settings are available."""
        settings = SimpleNamespace(
            dspace=SimpleNamespace(
                canonical_prefix='http://hdl.handle.net/',
                hostname='dspace.example.com',
                url='http://dspace.example.com',
                server_url='http://dspace.example.com/server',
                ui_url='http://dspace.example.com/ui',
            ),
            matomo=SimpleNamespace(
                site_id='1',
                rec='1',
                repository_id='repo123',
                country_iso='US',
                token_auth='auth_token_123',
            ),
        )
        context = SimpleNamespace(
            settings=settings,
            getDspaceMajorVersion=lambda: '6',
        )

        matomo_filter = MatomoFilter(context)
        processed = list(matomo_filter.run([sample_event]))

        assert len(processed) == 1
        params = processed[0]._matomoParams
        assert params['idsite'] == '1'
        assert params['token_auth'] == 'auth_token_123'
