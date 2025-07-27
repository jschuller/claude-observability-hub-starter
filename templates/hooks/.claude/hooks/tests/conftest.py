"""
Shared test fixtures for Claude Observability Hub hooks.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest


@pytest.fixture
def temp_queue_dir():
    """Create a temporary directory for queue files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_hub_url():
    """Mock observability hub URL."""
    return "http://localhost:4000"


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return {
        'source_app': 'test_project',
        'session_id': 'session_123',
        'agent_id': 'agent_456',
        'agent_name': 'test_agent',
        'agent_type': 'main',
        'hook_event_type': 'PreToolUse',
        'payload': {
            'tool': 'Bash',
            'command': 'ls -la'
        }
    }


@pytest.fixture
def sample_subagent_event():
    """Sample subagent event with parent tracking."""
    return {
        'source_app': 'test_project',
        'session_id': 'session_123',
        'agent_id': 'subagent_789',
        'agent_name': 'code_reviewer',
        'agent_type': 'subagent',
        'parent_agent_id': 'agent_456',
        'hook_event_type': 'SubagentStop',
        'payload': {
            'task': 'review changes',
            'status': 'success'
        }
    }


@pytest.fixture
def mock_urlopen():
    """Mock urllib.urlopen for network requests."""
    with patch('urllib.request.urlopen') as mock:
        # Default successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def mock_urlopen_failure():
    """Mock urllib.urlopen to simulate network failure."""
    with patch('urllib.request.urlopen') as mock:
        from urllib.error import URLError
        mock.side_effect = URLError("Connection refused")
        yield mock


@pytest.fixture
def mock_urlopen_duplicate():
    """Mock urllib.urlopen to simulate duplicate event (409)."""
    with patch('urllib.request.urlopen') as mock:
        mock_response = Mock()
        mock_response.status = 409
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock.return_value = mock_response
        yield mock