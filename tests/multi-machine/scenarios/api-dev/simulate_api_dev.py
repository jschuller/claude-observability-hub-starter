#!/usr/bin/env python3
"""
Simulates API development with multiple subagents.
"""
import os
import sys
import time
import random
import uuid
from datetime import datetime

sys.path.insert(0, '/app')
from send_event import send_event_sync

PROJECT_NAME = os.getenv('PROJECT_NAME', 'api-service')
SESSION_ID = os.getenv('SESSION_ID', f'session-{os.getpid()}')
MACHINE_ID = os.getenv('MACHINE_ID', 'machine-api-dev')

def simulate_api_development():
    """Simulate API development with code review and test subagents."""
    
    # Main controller agent
    main_agent_id = f"agent_controller_{uuid.uuid4().hex[:8]}"
    
    print(f"[{MACHINE_ID}] Starting API development with subagents...")
    
    # 1. Main agent starts
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'API Controller',
        'agent_type': 'main',
        'hook_event_type': 'Start',
        'payload': {
            'task': 'Implement REST API endpoints',
            'endpoints': ['/users', '/products', '/orders']
        }
    })
    
    time.sleep(0.5)
    
    # 2. Spawn code generator subagent
    code_agent_id = f"agent_codegen_{uuid.uuid4().hex[:8]}"
    
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': code_agent_id,
        'agent_name': 'Code Generator',
        'agent_type': 'subagent',
        'parent_agent_id': main_agent_id,
        'hook_event_type': 'SubagentStart',
        'payload': {
            'task': 'Generate API endpoint handlers',
            'language': 'Python',
            'framework': 'FastAPI'
        }
    })
    
    # Code generator works
    for endpoint in ['/users', '/products', '/orders']:
        time.sleep(0.3)
        
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': code_agent_id,
            'agent_name': 'Code Generator',
            'agent_type': 'subagent',
            'parent_agent_id': main_agent_id,
            'hook_event_type': 'PreToolUse',
            'payload': {
                'tool': 'Write',
                'file': f'src/endpoints{endpoint}.py'
            }
        })
        
        time.sleep(0.5)
        
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': code_agent_id,
            'agent_name': 'Code Generator',
            'agent_type': 'subagent',
            'parent_agent_id': main_agent_id,
            'hook_event_type': 'PostToolUse',
            'payload': {
                'tool': 'Write',
                'status': 'success',
                'lines_written': random.randint(50, 150)
            }
        })
    
    # 3. Spawn code reviewer subagent
    review_agent_id = f"agent_reviewer_{uuid.uuid4().hex[:8]}"
    
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': review_agent_id,
        'agent_name': 'Code Reviewer',
        'agent_type': 'subagent',
        'parent_agent_id': main_agent_id,
        'hook_event_type': 'SubagentStart',
        'payload': {
            'task': 'Review generated code for best practices'
        }
    })
    
    time.sleep(1)
    
    # Review findings
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': review_agent_id,
        'agent_name': 'Code Reviewer',
        'agent_type': 'subagent',
        'parent_agent_id': main_agent_id,
        'hook_event_type': 'Notification',
        'payload': {
            'review_status': 'completed',
            'issues_found': 3,
            'suggestions': [
                'Add input validation',
                'Implement rate limiting',
                'Add authentication middleware'
            ]
        }
    })
    
    # 4. Spawn test writer subagent
    test_agent_id = f"agent_tester_{uuid.uuid4().hex[:8]}"
    
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': test_agent_id,
        'agent_name': 'Test Writer',
        'agent_type': 'subagent',
        'parent_agent_id': main_agent_id,
        'hook_event_type': 'SubagentStart',
        'payload': {
            'task': 'Write unit and integration tests'
        }
    })
    
    time.sleep(0.5)
    
    # Write tests
    for test_type in ['unit', 'integration']:
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': test_agent_id,
            'agent_name': 'Test Writer',
            'agent_type': 'subagent',
            'parent_agent_id': main_agent_id,
            'hook_event_type': 'PreToolUse',
            'payload': {
                'tool': 'Write',
                'file': f'tests/test_{test_type}.py'
            }
        })
        
        time.sleep(0.3)
    
    # 5. Stop subagents
    for agent_id, agent_name in [
        (code_agent_id, 'Code Generator'),
        (review_agent_id, 'Code Reviewer'),
        (test_agent_id, 'Test Writer')
    ]:
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': agent_id,
            'agent_name': agent_name,
            'agent_type': 'subagent',
            'parent_agent_id': main_agent_id,
            'hook_event_type': 'SubagentStop',
            'payload': {
                'status': 'completed'
            }
        })
        
        time.sleep(0.2)
    
    # 6. Main agent completes
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'API Controller',
        'agent_type': 'main',
        'hook_event_type': 'Stop',
        'payload': {
            'result': 'API implementation complete',
            'endpoints_created': 3,
            'tests_written': 6,
            'review_issues_addressed': 3
        }
    })
    
    print(f"[{MACHINE_ID}] API development simulation complete!")

def continuous_simulation():
    """Run continuous simulation."""
    while True:
        try:
            simulate_api_development()
            
            # Random delay (2-8 minutes)
            delay = random.randint(120, 480)
            print(f"[{MACHINE_ID}] Waiting {delay}s before next session...")
            time.sleep(delay)
            
            # New session
            global SESSION_ID
            SESSION_ID = f"session-api-{uuid.uuid4().hex[:8]}"
            
        except KeyboardInterrupt:
            print(f"[{MACHINE_ID}] Simulation stopped.")
            break
        except Exception as e:
            print(f"[{MACHINE_ID}] Error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    continuous_simulation()