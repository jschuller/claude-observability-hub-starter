import { Database } from 'bun:sqlite';

// Initialize SQLite database
const db = new Database('/data/events.db', { create: true });

// Create tables
db.run(`
  CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uuid TEXT UNIQUE NOT NULL,
    source_app TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_type TEXT CHECK(agent_type IN ('main', 'subagent')),
    agent_name TEXT,
    parent_agent_id TEXT,
    agent_version TEXT,
    plugin_version TEXT,
    hook_event_type TEXT NOT NULL,
    payload TEXT,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    replay_state TEXT DEFAULT 'live'
  )
`);

// Create indexes
db.run('CREATE INDEX IF NOT EXISTS idx_uuid ON events(event_uuid)');
db.run('CREATE INDEX IF NOT EXISTS idx_session ON events(session_id)');
db.run('CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)');

// WebSocket clients
const wsClients = new Set<any>();

// Bun server
const server = Bun.serve({
  port: 4000,
  
  async fetch(req) {
    const url = new URL(req.url);
    
    // CORS headers
    const headers = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Event-UUID',
      'Content-Type': 'application/json'
    };
    
    // Handle preflight
    if (req.method === 'OPTIONS') {
      return new Response(null, { headers });
    }
    
    // Health check
    if (url.pathname === '/health') {
      return Response.json({ status: 'healthy', timestamp: new Date() }, { headers });
    }
    
    // POST /events - Single event
    if (url.pathname === '/events' && req.method === 'POST') {
      try {
        const event = await req.json();
        
        // Check for duplicate
        const existing = db.query('SELECT id FROM events WHERE event_uuid = ?').get(event.event_uuid);
        if (existing) {
          return new Response(JSON.stringify({ status: 'duplicate' }), { 
            status: 409,
            headers 
          });
        }
        
        // Insert event
        const stmt = db.prepare(`
          INSERT INTO events (
            event_uuid, source_app, machine_id, session_id,
            agent_id, agent_type, agent_name, parent_agent_id,
            agent_version, plugin_version, hook_event_type,
            payload, timestamp, replay_state
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);
        
        stmt.run(
          event.event_uuid,
          event.source_app,
          event.machine_id || 'unknown',
          event.session_id,
          event.agent_id || 'unknown',
          event.agent_type || 'main',
          event.agent_name || null,
          event.parent_agent_id || null,
          event.agent_version || null,
          event.plugin_version || null,
          event.hook_event_type,
          JSON.stringify(event.payload || {}),
          event.timestamp || new Date().toISOString(),
          event.replay_state || 'live'
        );
        
        // Broadcast to WebSocket clients
        const message = JSON.stringify({ type: 'new_event', data: event });
        wsClients.forEach(client => {
          try {
            client.send(message);
          } catch (e) {
            wsClients.delete(client);
          }
        });
        
        return Response.json({ status: 'success', event_uuid: event.event_uuid }, { headers });
        
      } catch (error) {
        console.error('Event error:', error);
        return new Response(JSON.stringify({ error: error.message }), { 
          status: 400,
          headers 
        });
      }
    }
    
    // POST /events/batch - Multiple events
    if (url.pathname === '/events/batch' && req.method === 'POST') {
      try {
        const { events } = await req.json();
        let processed = 0;
        let duplicates = 0;
        
        for (const event of events) {
          const existing = db.query('SELECT id FROM events WHERE event_uuid = ?').get(event.event_uuid);
          if (existing) {
            duplicates++;
            continue;
          }
          
          // Insert event (same as above)
          // ... insert logic ...
          processed++;
        }
        
        return Response.json({ 
          status: 'success',
          processed,
          duplicates,
          total: events.length 
        }, { headers });
        
      } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), { 
          status: 400,
          headers 
        });
      }
    }
    
    // GET /events - Query events
    if (url.pathname === '/events' && req.method === 'GET') {
      const limit = parseInt(url.searchParams.get('limit') || '100');
      const offset = parseInt(url.searchParams.get('offset') || '0');
      
      const events = db.query(`
        SELECT * FROM events 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
      `).all(limit, offset);
      
      // Parse JSON payloads
      const parsed = events.map(e => ({
        ...e,
        payload: JSON.parse(e.payload)
      }));
      
      return Response.json(parsed, { headers });
    }
    
    // GET /install.sh - Auto-installer
    if (url.pathname === '/install.sh') {
      const script = `#!/bin/bash
set -e
echo "🔧 Installing Claude Observability Hooks..."
mkdir -p .claude/hooks
curl -sL "${url.origin}/hooks/send_event.py" -o .claude/hooks/send_event.py
PROJECT_NAME=$(basename "$PWD")
# ... rest of install script ...
echo "✅ Installation complete!"
`;
      return new Response(script, { 
        headers: { 
          'Content-Type': 'text/plain',
          'Content-Disposition': 'inline; filename="install.sh"'
        }
      });
    }
    
    // 404
    return new Response('Not found', { status: 404, headers });
  },
  
  // WebSocket support
  websocket: {
    open(ws) {
      wsClients.add(ws);
      ws.send(JSON.stringify({ type: 'connected', clients: wsClients.size }));
    },
    message(ws, message) {
      // Echo for now
      ws.send(message);
    },
    close(ws) {
      wsClients.delete(ws);
    }
  }
});

console.log(`🚀 Observability Hub running at http://localhost:${server.port}`);
console.log(`📊 WebSocket: ws://localhost:${server.port}/stream`);
console.log(`📦 Database: /data/events.db`);