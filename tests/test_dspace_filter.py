#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for DSpaceDBFilter."""

import pytest
from unittest.mock import MagicMock
from dspace_stats_collector.dspacefilter import DSpaceDBFilter
from dspace_stats_collector.eventpipeline import Event

class TestDSpaceDBFilter:

    def test_run_buffers_and_enriches_events(self, mock_config_context, sample_event):
        """Test that the filter buffers events and processes them in batches."""
        # Setup mock DB with a method to simulate caching/querying
        mock_db = MagicMock()
        mock_config_context.db = mock_db
        
        # Setup return values for queryDownload
        enriched_data = {
            'id': '12345', 
            'record_title': 'Enriched Title',
            'handle': '123/456',
            'is_download': True
        }
        mock_db.queryDownload.return_value = enriched_data
        
        # Initialize filter with small batch size for testing
        dspace_filter = DSpaceDBFilter(mock_config_context)
        dspace_filter._batch_size = 2 # Force small batch
        
        # Create 3 events
        e1 = Event(); e1._src = {'id': '1', 'type': 0}
        e2 = Event(); e2._src = {'id': '2', 'type': 0}
        e3 = Event(); e3._src = {'id': '3', 'type': 0}
        
        events = [e1, e2, e3]
        
        # Run filter
        processed = list(dspace_filter.run(events))
        
        assert len(processed) == 3
        
        # Verify enrichment
        for e in processed:
            assert e._db == enriched_data
            
        # Verify calls - Should be called for each event (since we haven't implemented true batching yet, just simulated buffering)
        assert mock_db.queryDownload.call_count == 3
        
    def test_skips_events_missing_in_db(self, mock_config_context):
        """Test that events not found in DB are dropped."""
        mock_db = MagicMock()
        mock_config_context.db = mock_db
        
        # Returns None for unknown ID
        mock_db.queryDownload.return_value = None
        
        dspace_filter = DSpaceDBFilter(mock_config_context)
        
        e1 = Event(); e1._src = {'id': 'unknown', 'type': 0}
        
        processed = list(dspace_filter.run([e1]))
        
        assert len(processed) == 0 # Dropped

    def test_handles_db_errors_gracefully(self, mock_config_context):
        """Test that DB exceptions don't crash the pipeline."""
        mock_db = MagicMock()
        mock_config_context.db = mock_db
        
        mock_db.queryDownload.side_effect = Exception("DB Connection Failed")
        
        dspace_filter = DSpaceDBFilter(mock_config_context)
        
        e1 = Event(); e1._src = {'id': 'bad_id', 'type': 0}
        
        processed = list(dspace_filter.run([e1]))
        
        assert len(processed) == 0 # Dropped due to error, app should continue
