import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../../src/App.vue'

// Mock fetch API
global.fetch = vi.fn()

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    
    // Simulate connection
    setTimeout(() => {
      this.readyState = 1
      if (this.onopen) this.onopen()
    }, 10)
  }
  
  send(data) {
    // Mock send
  }
  
  close() {
    this.readyState = 3
    if (this.onclose) this.onclose()
  }
}

global.WebSocket = MockWebSocket

describe('App.vue', () => {
  let wrapper
  
  beforeEach(() => {
    vi.clearAllMocks()
    fetch.mockResolvedValue({
      ok: true,
      json: async () => []
    })
  })
  
  describe('Component Rendering', () => {
    it('renders header with title', () => {
      wrapper = mount(App)
      expect(wrapper.find('h1').text()).toBe('🔭 Claude Observability Dashboard')
    })
    
    it('shows disconnected status initially', () => {
      wrapper = mount(App)
      expect(wrapper.find('.status').text()).toContain('Disconnected')
      expect(wrapper.find('.indicator.disconnected').exists()).toBe(true)
    })
    
    it('shows connected status after WebSocket connects', async () => {
      wrapper = mount(App)
      
      // Wait for WebSocket connection
      await new Promise(resolve => setTimeout(resolve, 20))
      await nextTick()
      
      expect(wrapper.find('.status').text()).toContain('Connected')
      expect(wrapper.find('.indicator.connected').exists()).toBe(true)
    })
    
    it('displays event count', () => {
      wrapper = mount(App)
      expect(wrapper.find('.event-count').text()).toBe('0 events')
    })
  })
  
  describe('Event Loading', () => {
    it('loads initial events on mount', async () => {
      const mockEvents = [
        {
          event_uuid: 'test-1',
          hook_event_type: 'PreToolUse',
          source_app: 'test_app',
          timestamp: new Date().toISOString(),
          payload: { tool: 'Bash' }
        }
      ]
      
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockEvents
      })
      
      wrapper = mount(App)
      await nextTick()
      
      expect(fetch).toHaveBeenCalledWith('http://localhost:4000/events?limit=100')
    })
    
    it('handles event loading error gracefully', async () => {
      fetch.mockRejectedValue(new Error('Network error'))
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      wrapper = mount(App)
      await nextTick()
      
      expect(consoleSpy).toHaveBeenCalledWith('Failed to load events:', expect.any(Error))
      consoleSpy.mockRestore()
    })
  })
  
  describe('Event Filtering', () => {
    it('filters events based on search input', async () => {
      wrapper = mount(App)
      
      // Add test events
      wrapper.vm.events = [
        {
          event_uuid: '1',
          hook_event_type: 'PreToolUse',
          source_app: 'app1',
          payload: { tool: 'Bash' }
        },
        {
          event_uuid: '2',
          hook_event_type: 'PostToolUse',
          source_app: 'app2',
          payload: { tool: 'Git' }
        }
      ]
      
      await nextTick()
      expect(wrapper.findAll('.event-row')).toHaveLength(2)
      
      // Filter by tool name
      await wrapper.find('.filter-input').setValue('Bash')
      expect(wrapper.findAll('.event-row')).toHaveLength(1)
      
      // Filter by event type
      await wrapper.find('.filter-input').setValue('PostToolUse')
      expect(wrapper.findAll('.event-row')).toHaveLength(1)
    })
    
    it('shows all events when filter is cleared', async () => {
      wrapper = mount(App)
      wrapper.vm.events = [
        { event_uuid: '1', hook_event_type: 'Type1' },
        { event_uuid: '2', hook_event_type: 'Type2' }
      ]
      
      await wrapper.find('.filter-input').setValue('Type1')
      await nextTick()
      expect(wrapper.findAll('.event-row')).toHaveLength(1)
      
      await wrapper.find('.filter-input').setValue('')
      await nextTick()
      expect(wrapper.findAll('.event-row')).toHaveLength(2)
    })
  })
  
  describe('WebSocket Events', () => {
    it('adds new events from WebSocket', async () => {
      wrapper = mount(App)
      
      // Wait for WebSocket connection
      await new Promise(resolve => setTimeout(resolve, 20))
      
      // Simulate WebSocket message
      const newEvent = {
        event_uuid: 'ws-event-1',
        hook_event_type: 'Notification',
        source_app: 'test',
        timestamp: new Date().toISOString()
      }
      
      const ws = wrapper.vm.ws
      ws.onmessage({
        data: JSON.stringify({
          type: 'new_event',
          data: newEvent
        })
      })
      
      await nextTick()
      
      expect(wrapper.vm.events).toHaveLength(1)
      expect(wrapper.vm.events[0].event_uuid).toBe('ws-event-1')
    })
    
    it('limits events to 1000 maximum', async () => {
      wrapper = mount(App)
      
      // Add 1000 events
      wrapper.vm.events = Array(1000).fill(null).map((_, i) => ({
        event_uuid: `event-${i}`,
        hook_event_type: 'Test'
      }))
      
      // Wait for WebSocket
      await new Promise(resolve => setTimeout(resolve, 20))
      
      // Add one more event
      const ws = wrapper.vm.ws
      ws.onmessage({
        data: JSON.stringify({
          type: 'new_event',
          data: { event_uuid: 'new-event', hook_event_type: 'Test' }
        })
      })
      
      await nextTick()
      
      expect(wrapper.vm.events).toHaveLength(1000)
      expect(wrapper.vm.events[0].event_uuid).toBe('new-event')
    })
    
    it('reconnects WebSocket after disconnection', async () => {
      vi.useFakeTimers()
      wrapper = mount(App)
      
      // Wait for initial connection
      await vi.advanceTimersByTimeAsync(20)
      
      const ws = wrapper.vm.ws
      expect(wrapper.vm.connected).toBe(true)
      
      // Simulate disconnection
      ws.onclose()
      await nextTick()
      expect(wrapper.vm.connected).toBe(false)
      
      // Should reconnect after 3 seconds
      await vi.advanceTimersByTimeAsync(3000)
      await nextTick()
      
      // New WebSocket should be created
      expect(wrapper.vm.ws).not.toBe(ws)
      
      vi.useRealTimers()
    })
  })
  
  describe('Event Display', () => {
    it('shows correct emoji for event types', () => {
      wrapper = mount(App)
      
      expect(wrapper.vm.getEmoji('PreToolUse')).toBe('🔧')
      expect(wrapper.vm.getEmoji('PostToolUse')).toBe('✅')
      expect(wrapper.vm.getEmoji('SubagentStop')).toBe('👥')
      expect(wrapper.vm.getEmoji('UnknownType')).toBe('❓')
    })
    
    it('formats timestamp correctly', () => {
      wrapper = mount(App)
      
      const timestamp = '2024-01-15T10:30:45.000Z'
      const formatted = wrapper.vm.formatTime(timestamp)
      
      // Should be locale time string
      expect(formatted).toMatch(/\d{1,2}:\d{2}:\d{2}/)
    })
    
    it('displays agent hierarchy information', async () => {
      wrapper = mount(App)
      
      wrapper.vm.events = [{
        event_uuid: '1',
        hook_event_type: 'SubagentStop',
        agent_name: 'code_reviewer',
        parent_agent_id: 'main_agent_123',
        agent_type: 'subagent'
      }]
      
      await nextTick()
      
      const eventRow = wrapper.find('.event-row')
      expect(eventRow.find('.agent-name').text()).toBe('code_reviewer')
      expect(eventRow.find('.parent-ref').text()).toContain('main_agent_123')
    })
    
    it('applies correct CSS classes for event types', async () => {
      wrapper = mount(App)
      
      wrapper.vm.events = [
        { event_uuid: '1', hook_event_type: 'PreToolUse', agent_type: 'main' },
        { event_uuid: '2', hook_event_type: 'SubagentStop', agent_type: 'subagent' }
      ]
      
      await nextTick()
      
      const rows = wrapper.findAll('.event-row')
      expect(rows[0].classes()).toContain('type-PreToolUse')
      expect(rows[0].classes()).toContain('agent-main')
      expect(rows[1].classes()).toContain('type-SubagentStop')
      expect(rows[1].classes()).toContain('agent-subagent')
    })
  })
  
  describe('User Actions', () => {
    it('clears all events when clear button clicked', async () => {
      wrapper = mount(App)
      
      wrapper.vm.events = [
        { event_uuid: '1', hook_event_type: 'Test1' },
        { event_uuid: '2', hook_event_type: 'Test2' }
      ]
      
      await nextTick()
      expect(wrapper.vm.events).toHaveLength(2)
      
      await wrapper.find('.clear-btn').trigger('click')
      expect(wrapper.vm.events).toHaveLength(0)
    })
  })
  
  describe('Cleanup', () => {
    it('closes WebSocket on unmount', async () => {
      wrapper = mount(App)
      
      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 20))
      
      const ws = wrapper.vm.ws
      const closeSpy = vi.spyOn(ws, 'close')
      
      wrapper.unmount()
      
      expect(closeSpy).toHaveBeenCalled()
    })
  })
})