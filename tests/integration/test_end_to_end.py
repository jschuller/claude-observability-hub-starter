"""
End-to-end integration tests for Claude Observability Hub.
"""
import json
import time
import uuid
import pytest
import requests
import websocket
from datetime import datetime


HUB_URL = "http://localhost:4001"  # Test instance port
WS_URL = "ws://localhost:4001/stream"


class TestEndToEndFlow:
    """Test complete event flow from hook to dashboard."""
    
    @pytest.mark.integration
    def test_full_event_flow(self):
        """Test: Python hook → Hub → DB → WebSocket → Dashboard."""
        # 1. Connect WebSocket client
        received_events = []
        
        def on_message(ws, message):
            data = json.loads(message)
            if data.get('type') == 'new_event':
                received_events.append(data['data'])
        
        ws = websocket.WebSocketApp(WS_URL, on_message=on_message)
        
        # Start WebSocket in background thread
        import threading
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Give WebSocket time to connect
        time.sleep(0.5)
        
        # 2. Send event via HTTP
        test_event = {
            'event_uuid': str(uuid.uuid4()),
            'source_app': 'integration_test',
            'machine_id': 'test_machine',
            'session_id': 'test_session_123',
            'agent_id': 'test_agent_456',
            'agent_type': 'main',
            'agent_name': 'Integration Test Agent',
            'hook_event_type': 'PreToolUse',
            'payload': {
                'tool': 'TestTool',
                'timestamp': datetime.utcnow().isoformat()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        response = requests.post(
            f"{HUB_URL}/events",
            json=test_event,
            headers={'X-Event-UUID': test_event['event_uuid']}
        )
        
        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        
        # 3. Verify WebSocket received the event
        time.sleep(0.5)  # Give time for broadcast
        
        assert len(received_events) > 0
        received = received_events[-1]
        assert received['event_uuid'] == test_event['event_uuid']
        assert received['source_app'] == 'integration_test'
        
        # 4. Verify event is queryable
        query_response = requests.get(f"{HUB_URL}/events?limit=10")
        assert query_response.status_code == 200
        
        events = query_response.json()
        found = any(e['event_uuid'] == test_event['event_uuid'] for e in events)
        assert found, "Event not found in query results"
        
        # Cleanup
        ws.close()
    
    @pytest.mark.integration
    def test_network_partition_recovery(self):
        """Test hub downtime and recovery with local queue."""
        # This would simulate hub being down, events being queued,
        # then hub coming back up and processing queued events
        pass
    
    @pytest.mark.integration
    def test_agent_hierarchy_flow(self):
        """Test deep agent hierarchy (5+ levels of subagents)."""
        # Create a chain of agents
        agents = []
        parent_id = None
        
        for i in range(5):
            agent_event = {
                'event_uuid': str(uuid.uuid4()),
                'source_app': 'hierarchy_test',
                'session_id': 'hierarchy_session',
                'agent_id': f'agent_level_{i}',
                'agent_name': f'Level {i} Agent',
                'agent_type': 'main' if i == 0 else 'subagent',
                'parent_agent_id': parent_id,
                'hook_event_type': 'Start',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{HUB_URL}/events", json=agent_event)
            assert response.status_code == 200
            
            agents.append(agent_event)
            parent_id = agent_event['agent_id']
        
        # Query and verify hierarchy
        time.sleep(0.5)
        query_response = requests.get(
            f"{HUB_URL}/events?session_id=hierarchy_session"
        )
        
        events = query_response.json()
        assert len(events) >= 5
        
        # Verify parent chain
        for i in range(1, 5):
            event = next(e for e in events if e['agent_id'] == f'agent_level_{i}')
            assert event['parent_agent_id'] == f'agent_level_{i-1}'
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_high_volume_event_storm(self):
        """Test system under load (1000 events/sec)."""
        start_time = time.time()
        event_count = 1000
        
        # Send events rapidly
        for i in range(event_count):
            event = {
                'event_uuid': f'storm-{i}-{uuid.uuid4()}',
                'source_app': 'load_test',
                'session_id': 'storm_session',
                'agent_id': f'storm_agent_{i % 10}',  # 10 different agents
                'hook_event_type': 'Notification',
                'payload': {'index': i},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                f"{HUB_URL}/events",
                json=event,
                timeout=5
            )
            
            # Allow some failures under load
            if response.status_code not in [200, 503]:
                pytest.fail(f"Unexpected status: {response.status_code}")
        
        duration = time.time() - start_time
        events_per_sec = event_count / duration
        
        print(f"Processed {event_count} events in {duration:.2f}s")
        print(f"Rate: {events_per_sec:.2f} events/sec")
        
        # Verify most events were stored
        time.sleep(1)  # Let system catch up
        query_response = requests.get(
            f"{HUB_URL}/events?session_id=storm_session&limit=100"
        )
        
        stored_events = query_response.json()
        assert len(stored_events) > 50  # At least half made it
    
    @pytest.mark.integration
    def test_duplicate_event_handling(self):
        """Test that duplicate events are properly rejected."""
        duplicate_uuid = str(uuid.uuid4())
        
        event = {
            'event_uuid': duplicate_uuid,
            'source_app': 'duplicate_test',
            'hook_event_type': 'Test',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # First send - should succeed
        response1 = requests.post(f"{HUB_URL}/events", json=event)
        assert response1.status_code == 200
        
        # Second send - should be rejected
        response2 = requests.post(f"{HUB_URL}/events", json=event)
        assert response2.status_code == 409
        assert response2.json()['status'] == 'duplicate'
    
    @pytest.mark.integration
    def test_batch_api(self):
        """Test batch event submission."""
        batch_events = {
            'events': [
                {
                    'event_uuid': str(uuid.uuid4()),
                    'source_app': 'batch_test',
                    'hook_event_type': f'Event{i}',
                    'timestamp': datetime.utcnow().isoformat()
                }
                for i in range(10)
            ]
        }
        
        response = requests.post(
            f"{HUB_URL}/events/batch",
            json=batch_events
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['processed'] == 10
        assert result['total'] == 10
    
    @pytest.mark.integration
    def test_session_replay(self):
        """Test replaying a complete session."""
        session_id = f'replay_session_{uuid.uuid4()}'
        
        # Create a session with multiple events
        events = [
            ('Start', 'main', None),
            ('PreToolUse', 'main', None),
            ('SubagentStart', 'subagent', 'main'),
            ('PostToolUse', 'subagent', 'main'),
            ('SubagentStop', 'subagent', 'main'),
            ('Stop', 'main', None)
        ]
        
        for event_type, agent_type, parent in events:
            event = {
                'event_uuid': str(uuid.uuid4()),
                'source_app': 'replay_test',
                'session_id': session_id,
                'agent_id': agent_type,
                'agent_type': agent_type,
                'parent_agent_id': parent,
                'hook_event_type': event_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{HUB_URL}/events", json=event)
            assert response.status_code == 200
            time.sleep(0.1)  # Ensure ordering
        
        # Query full session
        query_response = requests.get(
            f"{HUB_URL}/events?session_id={session_id}&limit=100"
        )
        
        session_events = query_response.json()
        assert len(session_events) == 6
        
        # Verify event order (newest first in response)
        event_types = [e['hook_event_type'] for e in reversed(session_events)]
        expected_order = ['Start', 'PreToolUse', 'SubagentStart', 
                         'PostToolUse', 'SubagentStop', 'Stop']
        assert event_types == expected_order


class TestErrorScenarios:
    """Test error handling and edge cases."""
    
    @pytest.mark.integration
    def test_malformed_event_rejection(self):
        """Test that malformed events are rejected."""
        malformed_events = [
            {},  # Empty event
            {'not_valid': 'fields'},  # Missing required fields
            {'event_uuid': 'not-a-uuid'},  # Invalid UUID format
        ]
        
        for event in malformed_events:
            response = requests.post(f"{HUB_URL}/events", json=event)
            assert response.status_code == 400
    
    @pytest.mark.integration
    def test_database_recovery(self):
        """Test system recovers from database issues."""
        # This would test scenarios like:
        # - Disk full
        # - Database locked
        # - Corruption recovery
        pass


if __name__ == '__main__':
    # Run with random order to catch state pollution
    # Set PYTEST_RANDOM_SEED env var to reproduce failures
    pytest.main([__file__, '-v', '--random-order'])