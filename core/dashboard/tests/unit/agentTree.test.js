import { describe, it, expect } from 'vitest'

// Agent tree building logic that will be extracted to utils
function buildAgentTree(events) {
  const agentMap = new Map()
  const rootAgents = []
  
  // First pass: create all agents
  events.forEach(event => {
    if (!agentMap.has(event.agent_id)) {
      agentMap.set(event.agent_id, {
        id: event.agent_id,
        name: event.agent_name || event.agent_id,
        type: event.agent_type || 'main',
        events: [],
        children: []
      })
    }
    
    const agent = agentMap.get(event.agent_id)
    agent.events.push(event)
  })
  
  // Second pass: build hierarchy
  events.forEach(event => {
    const agent = agentMap.get(event.agent_id)
    
    if (event.parent_agent_id && agentMap.has(event.parent_agent_id)) {
      const parent = agentMap.get(event.parent_agent_id)
      if (!parent.children.includes(agent)) {
        parent.children.push(agent)
      }
    } else if (!event.parent_agent_id) {
      if (!rootAgents.includes(agent)) {
        rootAgents.push(agent)
      }
    }
  })
  
  return { agentMap, rootAgents }
}

describe('Agent Tree Building', () => {
  it('builds flat agent list correctly', () => {
    const events = [
      {
        agent_id: 'agent_1',
        agent_name: 'Main Agent',
        agent_type: 'main',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'agent_2',
        agent_name: 'Secondary Agent',
        agent_type: 'main',
        hook_event_type: 'Start'
      }
    ]
    
    const { agentMap, rootAgents } = buildAgentTree(events)
    
    expect(agentMap.size).toBe(2)
    expect(rootAgents).toHaveLength(2)
    expect(rootAgents[0].name).toBe('Main Agent')
    expect(rootAgents[1].name).toBe('Secondary Agent')
  })
  
  it('builds hierarchy from parent_agent_id', () => {
    const events = [
      {
        agent_id: 'main_1',
        agent_name: 'Main Controller',
        agent_type: 'main',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'sub_1',
        agent_name: 'Code Analyzer',
        agent_type: 'subagent',
        parent_agent_id: 'main_1',
        hook_event_type: 'SubagentStart'
      },
      {
        agent_id: 'sub_2',
        agent_name: 'Test Runner',
        agent_type: 'subagent',
        parent_agent_id: 'main_1',
        hook_event_type: 'SubagentStart'
      }
    ]
    
    const { agentMap, rootAgents } = buildAgentTree(events)
    
    expect(rootAgents).toHaveLength(1)
    expect(rootAgents[0].id).toBe('main_1')
    expect(rootAgents[0].children).toHaveLength(2)
    expect(rootAgents[0].children[0].name).toBe('Code Analyzer')
    expect(rootAgents[0].children[1].name).toBe('Test Runner')
  })
  
  it('handles deep agent hierarchies', () => {
    const events = [
      {
        agent_id: 'root',
        agent_name: 'Root',
        agent_type: 'main',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'level1',
        agent_name: 'Level 1',
        agent_type: 'subagent',
        parent_agent_id: 'root',
        hook_event_type: 'SubagentStart'
      },
      {
        agent_id: 'level2',
        agent_name: 'Level 2',
        agent_type: 'subagent',
        parent_agent_id: 'level1',
        hook_event_type: 'SubagentStart'
      },
      {
        agent_id: 'level3',
        agent_name: 'Level 3',
        agent_type: 'subagent',
        parent_agent_id: 'level2',
        hook_event_type: 'SubagentStart'
      }
    ]
    
    const { rootAgents } = buildAgentTree(events)
    
    // Verify deep nesting
    expect(rootAgents[0].id).toBe('root')
    expect(rootAgents[0].children[0].id).toBe('level1')
    expect(rootAgents[0].children[0].children[0].id).toBe('level2')
    expect(rootAgents[0].children[0].children[0].children[0].id).toBe('level3')
  })
  
  it('handles orphaned subagents gracefully', () => {
    const events = [
      {
        agent_id: 'orphan_1',
        agent_name: 'Orphaned Agent',
        agent_type: 'subagent',
        parent_agent_id: 'missing_parent',
        hook_event_type: 'SubagentStart'
      },
      {
        agent_id: 'main_1',
        agent_name: 'Normal Agent',
        agent_type: 'main',
        hook_event_type: 'Start'
      }
    ]
    
    const { agentMap, rootAgents } = buildAgentTree(events)
    
    // Orphaned subagents should not appear in root
    expect(rootAgents).toHaveLength(1)
    expect(rootAgents[0].id).toBe('main_1')
    
    // But should still exist in map
    expect(agentMap.has('orphan_1')).toBe(true)
  })
  
  it('aggregates multiple events per agent', () => {
    const events = [
      {
        agent_id: 'agent_1',
        agent_name: 'Busy Agent',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'agent_1',
        agent_name: 'Busy Agent',
        hook_event_type: 'PreToolUse',
        payload: { tool: 'Bash' }
      },
      {
        agent_id: 'agent_1',
        agent_name: 'Busy Agent',
        hook_event_type: 'PostToolUse',
        payload: { tool: 'Bash', status: 'success' }
      },
      {
        agent_id: 'agent_1',
        agent_name: 'Busy Agent',
        hook_event_type: 'Stop'
      }
    ]
    
    const { agentMap } = buildAgentTree(events)
    
    const agent = agentMap.get('agent_1')
    expect(agent.events).toHaveLength(4)
    expect(agent.events[0].hook_event_type).toBe('Start')
    expect(agent.events[3].hook_event_type).toBe('Stop')
  })
  
  it('handles circular parent references', () => {
    const events = [
      {
        agent_id: 'agent_a',
        agent_name: 'Agent A',
        parent_agent_id: 'agent_b',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'agent_b',
        agent_name: 'Agent B',
        parent_agent_id: 'agent_a',
        hook_event_type: 'Start'
      }
    ]
    
    const { rootAgents } = buildAgentTree(events)
    
    // Should handle without infinite loop
    expect(rootAgents).toHaveLength(0) // Both have parents
  })
  
  it('preserves agent order by first appearance', () => {
    const events = [
      {
        agent_id: 'third',
        agent_name: 'Third Agent',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'first',
        agent_name: 'First Agent',
        hook_event_type: 'Start'
      },
      {
        agent_id: 'second',
        agent_name: 'Second Agent',
        hook_event_type: 'Start'
      }
    ]
    
    const { rootAgents } = buildAgentTree(events)
    
    expect(rootAgents[0].id).toBe('third')
    expect(rootAgents[1].id).toBe('first')
    expect(rootAgents[2].id).toBe('second')
  })
})