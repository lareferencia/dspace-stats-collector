#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Event class - verifying the shared state bug fix."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dspace_stats_collector.eventpipeline import Event


class TestEventIsolation:
    """Test that Event instances have isolated state."""
    
    def test_events_do_not_share_data_dict(self):
        """
        Critical test: Verify that each Event instance has its own _data_dict.
        
        This was a bug where _data_dict was a class variable, causing
        all Event instances to share the same dictionary.
        """
        e1 = Event()
        e2 = Event()
        
        e1.foo = "bar"
        
        # e2 should NOT have the 'foo' attribute set by e1
        assert e1.foo == "bar"
        assert e2.foo is None, "Events are sharing state! This is the bug we fixed."
    
    def test_multiple_events_isolated(self):
        """Test multiple events with different data."""
        events = [Event() for _ in range(5)]
        
        for i, event in enumerate(events):
            event.value = i
            event.name = f"event_{i}"
        
        for i, event in enumerate(events):
            assert event.value == i
            assert event.name == f"event_{i}"
    
    def test_event_src_isolation(self):
        """Test that _src attribute is isolated between events."""
        e1 = Event()
        e2 = Event()
        
        e1._src = {'id': '123', 'time': '2026-01-01'}
        e2._src = {'id': '456', 'time': '2026-01-02'}
        
        assert e1._src['id'] == '123'
        assert e2._src['id'] == '456'


class TestEventAttributes:
    """Test Event attribute access."""
    
    def test_get_missing_attribute_returns_none(self):
        """Accessing non-existent attribute should return None."""
        event = Event()
        assert event.nonexistent is None
    
    def test_set_and_get_attribute(self):
        """Basic attribute set/get."""
        event = Event()
        event.my_attr = "my_value"
        assert event.my_attr == "my_value"
    
    def test_to_json(self):
        """Test JSON serialization."""
        event = Event()
        event.title = "Test Title"
        event.value = 42
        
        json_str = event.toJSON()
        assert "Test Title" in json_str
        assert "42" in json_str
    
    def test_str_representation(self):
        """Test string representation."""
        event = Event()
        event.key = "value"
        
        str_repr = str(event)
        assert "key" in str_repr
        assert "value" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
