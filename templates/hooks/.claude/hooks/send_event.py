#!/usr/bin/env python3
"""
Minimal async event sender for Claude Observability Hub.
Zero dependencies beyond Python stdlib.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import argparse

# Configuration
HUB_URL = os.getenv('CLAUDE_OBSERVABILITY_HUB', 'http://localhost:4000')
FALLBACK_QUEUE = Path.home() / '.claude' / 'event_queue.jsonl'
FALLBACK_QUEUE.parent.mkdir(exist_ok=True, parents=True)

def send_event_sync(event_data):
    """Synchronous event sending with fallback."""
    try:
        # Add metadata
        event_data['event_uuid'] = event_data.get('event_uuid', str(uuid.uuid4()))
        event_data['timestamp'] = event_data.get('timestamp', datetime.utcnow().isoformat())
        event_data['machine_id'] = event_data.get('machine_id', os.uname().nodename)
        
        # Send to hub
        req = Request(
            f"{HUB_URL}/events",
            data=json.dumps(event_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-Event-UUID': event_data['event_uuid']
            }
        )
        
        with urlopen(req, timeout=0.5) as response:
            if response.status == 409:  # Duplicate
                return True
            return response.status < 300
            
    except (URLError, TimeoutError):
        # Queue for later
        with open(FALLBACK_QUEUE, 'a') as f:
            f.write(json.dumps({
                'event': event_data,
                'queued_at': datetime.utcnow().isoformat()
            }) + '\n')
        return True
    except Exception as e:
        print(f"Event send error: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Send event to observability hub')
    parser.add_argument('--source-app', required=True, help='Source application name')
    parser.add_argument('--event-type', required=True, help='Hook event type')
    parser.add_argument('--session-id', default=None, help='Session ID')
    parser.add_argument('--agent-id', default=None, help='Agent ID')
    parser.add_argument('--agent-name', default=None, help='Agent name')
    parser.add_argument('--agent-type', default='main', help='Agent type (main/subagent)')
    parser.add_argument('--parent-agent-id', default=None, help='Parent agent ID')
    parser.add_argument('--payload', default='{}', help='Event payload as JSON')
    
    args = parser.parse_args()
    
    # Build event
    event = {
        'source_app': args.source_app,
        'session_id': args.session_id or f"session_{os.getpid()}",
        'agent_id': args.agent_id or f"agent_{os.getpid()}",
        'agent_name': args.agent_name,
        'agent_type': args.agent_type,
        'parent_agent_id': args.parent_agent_id,
        'hook_event_type': args.event_type,
        'payload': json.loads(args.payload)
    }
    
    # Read additional data from stdin if available
    if not sys.stdin.isatty():
        try:
            stdin_data = json.load(sys.stdin)
            event['payload'].update(stdin_data)
        except:
            pass
    
    # Send event
    success = send_event_sync(event)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()