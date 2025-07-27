<template>
  <div id="app">
    <header>
      <h1>🔭 Claude Observability Dashboard</h1>
      <div class="status">
        <span :class="['indicator', connected ? 'connected' : 'disconnected']"></span>
        {{ connected ? 'Connected' : 'Disconnected' }}
        <span class="event-count">{{ events.length }} events</span>
      </div>
    </header>

    <main>
      <div class="controls">
        <input 
          v-model="filter"
          placeholder="Filter events..."
          class="filter-input"
        >
        <button @click="clearEvents" class="clear-btn">Clear</button>
      </div>

      <div class="event-list">
        <div 
          v-for="event in filteredEvents" 
          :key="event.event_uuid"
          class="event-row"
          :class="[`type-${event.hook_event_type}`, `agent-${event.agent_type}`]"
        >
          <div class="event-header">
            <span class="event-type">{{ getEmoji(event.hook_event_type) }} {{ event.hook_event_type }}</span>
            <span class="source-app">{{ event.source_app }}</span>
            <span class="timestamp">{{ formatTime(event.timestamp) }}</span>
          </div>
          <div class="event-details">
            <span class="agent-name">{{ event.agent_name || event.agent_id }}</span>
            <span v-if="event.parent_agent_id" class="parent-ref">
              ↳ {{ event.parent_agent_id }}
            </span>
          </div>
          <div class="payload" v-if="event.payload">
            <pre>{{ JSON.stringify(event.payload, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'

export default {
  name: 'App',
  setup() {
    const events = ref([])
    const filter = ref('')
    const connected = ref(false)
    let ws = null
    
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:4000'
    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:4000/stream'
    
    const filteredEvents = computed(() => {
      if (!filter.value) return events.value
      const searchTerm = filter.value.toLowerCase()
      return events.value.filter(event => 
        JSON.stringify(event).toLowerCase().includes(searchTerm)
      )
    })
    
    const getEmoji = (eventType) => {
      const emojiMap = {
        'PreToolUse': '🔧',
        'PostToolUse': '✅',
        'Notification': '🔔',
        'Stop': '🛑',
        'SubagentStop': '👥',
        'PreCompact': '📦',
        'UserPromptSubmit': '💬'
      }
      return emojiMap[eventType] || '❓'
    }
    
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString()
    }
    
    const clearEvents = () => {
      events.value = []
    }
    
    const connectWebSocket = () => {
      ws = new WebSocket(WS_URL)
      
      ws.onopen = () => {
        connected.value = true
        console.log('WebSocket connected')
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'new_event') {
            events.value.unshift(data.data)
            // Limit to 1000 events
            if (events.value.length > 1000) {
              events.value = events.value.slice(0, 1000)
            }
          }
        } catch (e) {
          console.error('WebSocket message error:', e)
        }
      }
      
      ws.onclose = () => {
        connected.value = false
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    }
    
    const loadInitialEvents = async () => {
      try {
        const response = await fetch(`${API_URL}/events?limit=100`)
        const data = await response.json()
        events.value = data
      } catch (e) {
        console.error('Failed to load events:', e)
      }
    }
    
    onMounted(() => {
      loadInitialEvents()
      connectWebSocket()
    })
    
    onUnmounted(() => {
      if (ws) {
        ws.close()
      }
    })
    
    return {
      events,
      filter,
      connected,
      filteredEvents,
      getEmoji,
      formatTime,
      clearEvents
    }
  }
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #0a0a0a;
  color: #ffffff;
}

#app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #333;
}

h1 {
  font-size: 28px;
  font-weight: 600;
}

.status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.indicator.connected {
  background-color: #4ade80;
}

.indicator.disconnected {
  background-color: #ef4444;
}

.event-count {
  margin-left: 20px;
  opacity: 0.7;
}

.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-input {
  flex: 1;
  padding: 10px;
  background-color: #1a1a1a;
  border: 1px solid #333;
  border-radius: 6px;
  color: white;
  font-size: 14px;
}

.clear-btn {
  padding: 10px 20px;
  background-color: #333;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
}

.clear-btn:hover {
  background-color: #444;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-row {
  background-color: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  padding: 15px;
  transition: all 0.2s;
}

.event-row:hover {
  border-color: #666;
  transform: translateY(-1px);
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.event-type {
  font-weight: 600;
  font-size: 16px;
}

.source-app {
  color: #60a5fa;
  font-size: 14px;
}

.timestamp {
  color: #999;
  font-size: 12px;
}

.event-details {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #ccc;
}

.agent-name {
  color: #34d399;
}

.parent-ref {
  color: #fbbf24;
}

.payload {
  margin-top: 10px;
  padding: 10px;
  background-color: #0a0a0a;
  border-radius: 4px;
  overflow-x: auto;
}

.payload pre {
  font-size: 12px;
  color: #999;
}

/* Event type colors */
.type-PreToolUse {
  border-left: 4px solid #3b82f6;
}

.type-PostToolUse {
  border-left: 4px solid #10b981;
}

.type-SubagentStop {
  border-left: 4px solid #f59e0b;
}

.type-Error {
  border-left: 4px solid #ef4444;
}
</style>