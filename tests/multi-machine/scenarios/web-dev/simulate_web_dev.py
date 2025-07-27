#!/usr/bin/env python3
"""
Simulates a web development project with Claude Code agent activities.
"""
import os
import sys
import time
import random
import subprocess
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '/app')
from send_event import send_event_sync

PROJECT_NAME = os.getenv('PROJECT_NAME', 'web-app')
SESSION_ID = os.getenv('SESSION_ID', f'session-{os.getpid()}')
MACHINE_ID = os.getenv('MACHINE_ID', 'machine-web-dev')

def simulate_agent_activity():
    """Simulate typical web development workflow."""
    
    # Main agent starts
    main_agent_id = f"agent_main_{random.randint(1000, 9999)}"
    
    print(f"[{MACHINE_ID}] Starting web development simulation...")
    
    # 1. Start event
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'agent_type': 'main',
        'hook_event_type': 'Start',
        'payload': {
            'task': 'Build responsive landing page',
            'project': PROJECT_NAME
        }
    })
    
    time.sleep(0.5)
    
    # 2. Tool use - Read files
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'hook_event_type': 'PreToolUse',
        'payload': {
            'tool': 'Read',
            'file': 'src/components/Header.vue'
        }
    })
    
    time.sleep(0.2)
    
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'hook_event_type': 'PostToolUse',
        'payload': {
            'tool': 'Read',
            'status': 'success',
            'lines_read': 145
        }
    })
    
    time.sleep(1)
    
    # 3. Edit files
    for file in ['Header.vue', 'Footer.vue', 'styles.css']:
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': main_agent_id,
            'agent_name': 'Web Developer Agent',
            'hook_event_type': 'PreToolUse',
            'payload': {
                'tool': 'Edit',
                'file': f'src/components/{file}',
                'changes': random.randint(5, 50)
            }
        })
        
        time.sleep(0.3)
        
        send_event_sync({
            'source_app': PROJECT_NAME,
            'session_id': SESSION_ID,
            'agent_id': main_agent_id,
            'agent_name': 'Web Developer Agent',
            'hook_event_type': 'PostToolUse',
            'payload': {
                'tool': 'Edit',
                'status': 'success'
            }
        })
        
        time.sleep(0.5)
    
    # 4. Run tests
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'hook_event_type': 'PreToolUse',
        'payload': {
            'tool': 'Bash',
            'command': 'npm test'
        }
    })
    
    time.sleep(2)
    
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'hook_event_type': 'PostToolUse',
        'payload': {
            'tool': 'Bash',
            'status': 'success',
            'tests_passed': 42,
            'tests_failed': 0
        }
    })
    
    # 5. Complete
    send_event_sync({
        'source_app': PROJECT_NAME,
        'session_id': SESSION_ID,
        'agent_id': main_agent_id,
        'agent_name': 'Web Developer Agent',
        'hook_event_type': 'Stop',
        'payload': {
            'result': 'Landing page completed successfully',
            'files_modified': 3,
            'tests_passed': 42
        }
    })
    
    print(f"[{MACHINE_ID}] Web development simulation complete!")

def continuous_simulation():
    """Run continuous simulation with random delays."""
    while True:
        try:
            simulate_agent_activity()
            
            # Random delay between sessions (1-5 minutes)
            delay = random.randint(60, 300)
            print(f"[{MACHINE_ID}] Waiting {delay}s before next session...")
            time.sleep(delay)
            
            # Generate new session ID
            global SESSION_ID
            SESSION_ID = f"session-web-{random.randint(10000, 99999)}"
            
        except KeyboardInterrupt:
            print(f"[{MACHINE_ID}] Simulation stopped.")
            break
        except Exception as e:
            print(f"[{MACHINE_ID}] Error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    continuous_simulation()