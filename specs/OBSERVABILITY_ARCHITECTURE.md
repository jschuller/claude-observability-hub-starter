# 🚀 Claude Code Observability Architecture v2.0

## Executive Summary

This document outlines a production-ready, scalable observability system for Claude Code agents and sub-agents. The architecture supports multi-machine deployments, sub-agent tracking, and provides enterprise-grade reliability with minimal integration overhead.

## 🎯 Core Design Principles

1. **Minimal Integration Friction**: 2-file setup per project
2. **Zero Dependencies**: Pure Python hooks with stdlib only
3. **Sub-millisecond Latency**: Fire-and-forget with local fallback
4. **Horizontal Scalability**: From single machine to distributed clusters
5. **Complete Observability**: Full agent lineage and delegation tracking

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY HUB                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Ingestion Layer                                     │   │
│  │  - REST API (single & batch events)                 │   │
│  │  - WebSocket (real-time streaming)                  │   │
│  │  - Deduplication (UUID-based)                       │   │
│  │  - Authentication (HMAC/JWT)                        │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │  Storage Layer                                       │   │
│  │  - SQLite (local dev) / TimescaleDB (production)   │   │
│  │  - Event queue for retries                         │   │
│  │  - Agent hierarchy views                           │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │  Visualization Layer                                 │   │
│  │  - Vue 3 Dashboard                                  │   │
│  │  - D3.js Agent Trees                               │   │
│  │  - Real-time Updates                               │   │
│  │  - Session Replay                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS/WSS
     ┌────────────────────────┴────────────────────┐
     │                        │                     │
┌────▼─────┐          ┌──────▼──────┐      ┌──────▼──────┐
│Project A │          │  Project B   │      │  Project C  │
│.claude/  │          │  .claude/    │      │  .claude/   │
│ └─hooks/ │          │   └─hooks/   │      │   └─hooks/  │
└──────────┘          └──────────────┘      └─────────────┘
```

## 📊 Enhanced Database Schema

```sql
-- Events table with full tracking
CREATE TABLE events (
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
    payload JSON,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    replay_state TEXT DEFAULT 'live',
    
    -- Performance indexes
    INDEX idx_uuid (event_uuid),
    INDEX idx_session (session_id),
    INDEX idx_agent_tree (agent_id, parent_agent_id),
    INDEX idx_timestamp (timestamp)
);

-- Retry queue for resilience
CREATE TABLE event_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uuid TEXT UNIQUE NOT NULL,
    event_data JSON NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_retry DATETIME,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_retry (retry_count, last_retry)
);

-- Agent hierarchy view
CREATE VIEW agent_hierarchy AS
WITH RECURSIVE tree AS (
    SELECT 
        agent_id, 
        agent_name, 
        agent_type,
        parent_agent_id, 
        session_id,
        0 as depth,
        agent_id as root_agent
    FROM events
    WHERE parent_agent_id IS NULL
    
    UNION ALL
    
    SELECT 
        e.agent_id, 
        e.agent_name, 
        e.agent_type,
        e.parent_agent_id, 
        e.session_id,
        t.depth + 1,
        t.root_agent
    FROM events e
    JOIN tree t ON e.parent_agent_id = t.agent_id
)
SELECT * FROM tree;

-- Session statistics
CREATE VIEW session_stats AS
SELECT 
    session_id,
    source_app,
    machine_id,
    COUNT(DISTINCT agent_id) as agent_count,
    MAX(depth) as max_depth,
    COUNT(*) as event_count,
    MIN(timestamp) as started_at,
    MAX(timestamp) as ended_at,
    CAST((julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 86400 AS INTEGER) as duration_seconds
FROM events e
LEFT JOIN agent_hierarchy ah ON e.agent_id = ah.agent_id
GROUP BY session_id, source_app, machine_id;
```

## 🔒 Security & Reliability Features

### Event Signing (Optional)
```python
# HMAC signature for tamper detection
signature = hmac.new(
    secret_key.encode(),
    json.dumps(event, sort_keys=True).encode(),
    hashlib.sha256
).hexdigest()
```

### Deduplication
- UUID-based idempotency
- Server returns 409 for duplicates
- Client treats 409 as success

### Retry Logic
- Local queue for network failures
- Exponential backoff
- Max retry limits
- Batch flushing on reconnect

## 📈 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Event Latency | <1ms | Time to return from send_nowait() |
| Throughput | 10k events/sec | Single hub instance |
| Storage | <100KB/session | Average session size |
| Dashboard Load | <500ms | Initial render time |
| Agent Tree Render | <100ms | For 1000 agents |

## 🚀 Deployment Options

### Local Development
```bash
# Single command start
docker-compose up -d
```

### Cloud Deployment (Fly.io)
```toml
# fly.toml
app = "claude-observability"

[build]
  dockerfile = "Dockerfile.hub"

[http_service]
  internal_port = 4000
  force_https = true

[mounts]
  source = "event_data"
  destination = "/data"
```

### Kubernetes (Future)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: observability-hub
spec:
  replicas: 3
  selector:
    matchLabels:
      app: observability
  template:
    spec:
      containers:
      - name: hub
        image: claude-observability:latest
        env:
        - name: DATABASE_URL
          value: "postgres://..."
```

## 🔧 Integration Guide

### Quick Start (Per Project)
```bash
curl -sL https://observability.your-domain.com/install.sh | bash
```

### Manual Setup
1. Copy `send_event.py` to `.claude/hooks/`
2. Add hooks to `.claude/settings.json`
3. Set `CLAUDE_OBSERVABILITY_HUB` env var

### Environment Variables
- `CLAUDE_OBSERVABILITY_HUB`: Hub URL (default: http://localhost:4000)
- `CLAUDE_OBSERVABILITY_SECRET`: HMAC key (optional)
- `CLAUDE_AGENT_VERSION`: Agent version tracking

## 📊 Visualization Features

### Agent Tree View
- Force-directed graph (D3.js)
- Color coding by agent type
- Size by event count
- Click for details
- Filter by status/type

### Session Timeline
- Chronological event stream
- Agent delegation visualization
- Error highlighting
- Replay controls

### Analytics Dashboard
- Sessions per day/hour
- Agent type distribution
- Error rates
- Performance metrics
- Top failing agents

## 🧪 Testing Strategy

### Unit Tests
- Event sender logic
- Queue management
- Deduplication

### Integration Tests
- End-to-end event flow
- Retry scenarios
- Batch processing

### Load Tests
```bash
# Simulate 1000 concurrent sessions
python scripts/load_test.py --sessions 1000 --concurrent 100
```

## 🎯 Success Metrics

1. **Adoption**: 80% of projects using observability within 1 month
2. **Reliability**: 99.9% event delivery rate
3. **Performance**: P99 latency <5ms
4. **Usability**: <5 minute setup time

## 🚦 Implementation Phases

### Phase 1: MVP (Week 1)
- [ ] Core event ingestion
- [ ] Basic dashboard
- [ ] Local development setup

### Phase 2: Production Ready (Week 2)
- [ ] Retry queues
- [ ] Batch APIs
- [ ] Agent tree visualization

### Phase 3: Scale (Week 3)
- [ ] Cloud deployment
- [ ] Performance optimization
- [ ] Advanced analytics

### Phase 4: Polish (Week 4)
- [ ] Auto-installer
- [ ] Documentation
- [ ] Open source release

## 📚 Additional Resources

- [Claude Code Hooks Documentation](https://docs.anthropic.com/claude-code/hooks)
- [D3.js Force Layout](https://d3js.org/d3-force)
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [TimescaleDB Time-Series](https://www.timescale.com/)

---

*This architecture is designed to scale from a single developer to enterprise teams while maintaining simplicity and reliability.*