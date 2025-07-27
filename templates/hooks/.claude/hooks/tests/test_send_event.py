"""
Tests for the Claude Observability Hub event sender.
"""
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock, mock_open
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from send_event import send_event_sync, main


class TestSendEventSync:
    """Test the synchronous event sending function."""
    
    @pytest.mark.unit
    def test_event_sent_successfully(self, sample_event, mock_urlopen):
        """Test successful event transmission to hub."""
        result = send_event_sync(sample_event)
        
        assert result is True
        mock_urlopen.assert_called_once()
        
        # Verify request details
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        
        assert request.get_full_url() == "http://localhost:4000/events"
        assert request.get_header('Content-type') == 'application/json'
        assert request.get_header('X-event-uuid') is not None
        
        # Verify event data
        sent_data = json.loads(request.data)
        assert sent_data['source_app'] == 'test_project'
        assert sent_data['event_uuid'] is not None
        assert sent_data['timestamp'] is not None
        assert sent_data['machine_id'] is not None
    
    @pytest.mark.unit
    def test_event_queued_when_hub_down(self, sample_event, mock_urlopen_failure, temp_queue_dir):
        """Test event queuing when hub is unreachable."""
        with patch.dict(os.environ, {'HOME': str(temp_queue_dir)}):
            result = send_event_sync(sample_event)
            
            assert result is True
            
            # Check queue file was created
            queue_file = temp_queue_dir / '.claude' / 'event_queue.jsonl'
            assert queue_file.exists()
            
            # Verify queued event
            with open(queue_file) as f:
                queued = json.loads(f.readline())
                assert queued['event']['source_app'] == 'test_project'
                assert 'queued_at' in queued
    
    @pytest.mark.unit
    def test_duplicate_event_handled_gracefully(self, sample_event, mock_urlopen_duplicate):
        """Test handling of duplicate event UUID (409 response)."""
        result = send_event_sync(sample_event)
        
        assert result is True  # Duplicates are considered successful
        mock_urlopen_duplicate.assert_called_once()
    
    @pytest.mark.unit
    def test_event_uuid_deduplication(self, sample_event, mock_urlopen):
        """Test that same event gets same UUID for deduplication."""
        # Pre-set UUID to ensure consistency
        sample_event['event_uuid'] = 'test-uuid-123'
        
        send_event_sync(sample_event)
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        sent_data = json.loads(request.data)
        
        assert sent_data['event_uuid'] == 'test-uuid-123'
        assert request.get_header('X-event-uuid') == 'test-uuid-123'
    
    @pytest.mark.unit
    def test_parent_agent_tracking_preserved(self, sample_subagent_event, mock_urlopen):
        """Test subagent events preserve parent agent ID."""
        result = send_event_sync(sample_subagent_event)
        
        assert result is True
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        sent_data = json.loads(request.data)
        
        assert sent_data['agent_type'] == 'subagent'
        assert sent_data['parent_agent_id'] == 'agent_456'
        assert sent_data['agent_name'] == 'code_reviewer'
    
    @pytest.mark.unit
    def test_custom_hub_url_from_env(self, sample_event, mock_urlopen):
        """Test using custom hub URL from environment variable."""
        with patch.dict(os.environ, {'CLAUDE_OBSERVABILITY_HUB': 'http://hub.example.com:5000'}):
            # Need to reimport to pick up env change
            from send_event import send_event_sync
            send_event_sync(sample_event)
            
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.get_full_url() == "http://hub.example.com:5000/events"
    
    @pytest.mark.unit
    def test_timeout_handling(self, sample_event, temp_queue_dir):
        """Test handling of request timeout."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Request timed out")
            
            with patch.dict(os.environ, {'HOME': str(temp_queue_dir)}):
                result = send_event_sync(sample_event)
                
                assert result is True  # Should queue on timeout
                
                # Verify event was queued
                queue_file = temp_queue_dir / '.claude' / 'event_queue.jsonl'
                assert queue_file.exists()


class TestMainCLI:
    """Test the CLI interface."""
    
    @pytest.mark.unit
    def test_cli_basic_event(self, mock_urlopen):
        """Test sending event via CLI with basic arguments."""
        test_args = [
            'send_event.py',
            '--source-app', 'test_app',
            '--event-type', 'PreToolUse',
            '--agent-name', 'test_agent'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_urlopen.assert_called_once()
    
    @pytest.mark.unit
    def test_cli_with_payload(self, mock_urlopen):
        """Test CLI with JSON payload."""
        test_args = [
            'send_event.py',
            '--source-app', 'test_app',
            '--event-type', 'PostToolUse',
            '--payload', '{"tool": "Bash", "status": "success"}'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            sent_data = json.loads(request.data)
            
            assert sent_data['payload']['tool'] == 'Bash'
            assert sent_data['payload']['status'] == 'success'
    
    @pytest.mark.unit
    def test_cli_subagent_event(self, mock_urlopen):
        """Test CLI with subagent parameters."""
        test_args = [
            'send_event.py',
            '--source-app', 'test_app',
            '--event-type', 'SubagentStop',
            '--agent-type', 'subagent',
            '--parent-agent-id', 'parent_123',
            '--agent-name', 'code_analyzer'
        ]
        
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            sent_data = json.loads(request.data)
            
            assert sent_data['agent_type'] == 'subagent'
            assert sent_data['parent_agent_id'] == 'parent_123'
    
    @pytest.mark.unit
    def test_cli_with_stdin_data(self, mock_urlopen):
        """Test CLI reading additional data from stdin."""
        test_args = [
            'send_event.py',
            '--source-app', 'test_app',
            '--event-type', 'Notification',
            '--payload', '{"base": "data"}'
        ]
        
        stdin_data = '{"extra": "from_stdin"}'
        
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdin.isatty', return_value=False):
                with patch('json.load', return_value=json.loads(stdin_data)):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
        
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        sent_data = json.loads(request.data)
        
        assert sent_data['payload']['base'] == 'data'
        assert sent_data['payload']['extra'] == 'from_stdin'
    
    @pytest.mark.unit
    def test_cli_failure_exit_code(self, mock_urlopen_failure):
        """Test CLI returns non-zero exit code on failure."""
        test_args = [
            'send_event.py',
            '--source-app', 'test_app',
            '--event-type', 'Error'
        ]
        
        # Mock both urlopen failure AND file write failure
        with patch.object(sys, 'argv', test_args):
            with patch('builtins.open', side_effect=PermissionError("Cannot write")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1


class TestQueueMechanics:
    """Test the local queue fallback mechanism."""
    
    @pytest.mark.unit
    def test_queue_file_format(self, sample_event, mock_urlopen_failure, temp_queue_dir):
        """Test queued events are in correct JSONL format."""
        with patch.dict(os.environ, {'HOME': str(temp_queue_dir)}):
            # Queue multiple events
            send_event_sync(sample_event)
            send_event_sync(sample_event)
            
            queue_file = temp_queue_dir / '.claude' / 'event_queue.jsonl'
            
            # Verify JSONL format
            with open(queue_file) as f:
                lines = f.readlines()
                assert len(lines) == 2
                
                for line in lines:
                    queued = json.loads(line)
                    assert 'event' in queued
                    assert 'queued_at' in queued
                    assert isinstance(queued['queued_at'], str)
    
    @pytest.mark.unit
    def test_queue_directory_creation(self, sample_event, mock_urlopen_failure, temp_queue_dir):
        """Test queue directory is created if it doesn't exist."""
        home_dir = temp_queue_dir / 'new_home'
        
        with patch.dict(os.environ, {'HOME': str(home_dir)}):
            result = send_event_sync(sample_event)
            
            assert result is True
            assert (home_dir / '.claude' / 'event_queue.jsonl').exists()


@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual network or services."""
    
    @pytest.mark.skip(reason="Requires running observability hub")
    def test_real_hub_connection(self, sample_event):
        """Test against actual running hub (manual test)."""
        result = send_event_sync(sample_event)
        assert result is True
    
    def test_batch_event_scenarios(self, mock_urlopen, mock_urlopen_failure):
        """Test mixed success/failure batch scenarios."""
        events = [
            {'source_app': 'app1', 'hook_event_type': 'Start'},
            {'source_app': 'app2', 'hook_event_type': 'Stop'},
        ]
        
        # First succeeds, second fails
        mock_urlopen.side_effect = [mock_urlopen.return_value, mock_urlopen_failure.side_effect]
        
        results = []
        for event in events:
            results.append(send_event_sync(event))
        
        assert results[0] is True
        assert results[1] is True  # Failed but queued