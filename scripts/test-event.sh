#!/bin/bash
# Test script to send sample events

echo "🧪 Testing Claude Observability Hub..."

# Send a main agent event
python3 templates/hooks/.claude/hooks/send_event.py \
    --source-app "test_project" \
    --event-type "PreToolUse" \
    --agent-name "main_controller" \
    --payload '{"tool": "Bash", "command": "ls -la"}'

# Send a subagent event
python3 templates/hooks/.claude/hooks/send_event.py \
    --source-app "test_project" \
    --event-type "SubagentStop" \
    --agent-name "code_reviewer" \
    --agent-type "subagent" \
    --parent-agent-id "agent_main_123" \
    --payload '{"task": "review changes", "status": "success"}'

echo "✅ Test events sent! Check dashboard at http://localhost:5173"