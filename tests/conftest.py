import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure we can import from source
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dspace_stats_collector.eventpipeline import Event

@pytest.fixture
def mock_config_context():
    """Mock ConfigurationContext."""
    config = MagicMock()
    
    # Mock properties
    config.dspaceProperties = {
        'handle.canonical.prefix': 'http://hdl.handle.net/',
        'dspace.hostname': 'dspace.example.com',
        'dspace.url': 'http://dspace.example.com',
        'dspace.server.url': 'http://dspace.example.com/server',
        'dspace.ui.url': 'http://dspace.example.com/ui',
    }
    
    config.properties = {
        'matomo.idSite': '1',
        'matomo.rec': '1',
        'matomo.repositoryId': 'repo123',
        'matomo.countryISO': 'US',
        'matomo.token_auth': 'auth_token_123',
    }
    
    config.getDspaceMajorVersion.return_value = '6'
    config.getMatomoUrl.return_value = 'http://matomo.example.com/matomo.php'
    config.getMatomoTokenAuth.return_value = 'auth_token_123'
    config.getMatomoOutputSize.return_value = 50
    
    return config

@pytest.fixture
def sample_event():
    """Create a sample generic event."""
    event = Event()
    event._src = {
        'id': '12345',
        'time': '2026-01-13T12:00:00.000Z',
        'ip': '192.168.1.100',
        'userAgent': 'Mozilla/5.0 Test Agent',
        'type': 0, # Download
    }
    event._sess = {'id': 'session_123'}
    event.is_robot = False
    
    # Mock _db data usually populated by DSpaceDBFilter
    event._db = {
        'id': '12345',
        'record_title': 'Test Record Title',
        'handle': '12345/6789',
        'is_download': True,
        'owning_item': 'owner_123',
        'sequence_id': 1,
        'filename': 'test_file.pdf'
    }
    
    return event
