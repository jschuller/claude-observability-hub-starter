# Testing Guide

This guide covers the Test-Driven Development (TDD) approach for the Claude Observability Hub project.

## Overview

We follow a lean TDD approach focusing on critical paths:
- **Event Pipeline**: Ingestion, deduplication, queuing
- **Agent Hierarchies**: Parent-child relationships, tree building
- **Real-time Updates**: WebSocket broadcasting, UI reactivity

## Test Structure

```
claude-observability-hub-starter/
├── templates/hooks/.claude/hooks/tests/    # Python hook tests
│   ├── conftest.py                        # Shared fixtures
│   └── test_send_event.py                 # Event sender tests
├── core/server/src/__tests__/             # Bun/TypeScript tests
│   ├── events.test.ts                     # API endpoint tests
│   └── installer.test.ts                  # Auto-installer tests
├── core/dashboard/tests/                  # Vue tests
│   ├── components/                        # Component tests
│   │   └── App.test.js
│   └── unit/                             # Unit tests
│       └── agentTree.test.js
└── tests/integration/                     # End-to-end tests
    └── test_end_to_end.py
```

## Running Tests

### Quick Start

```bash
# Run all tests
./scripts/test-all.sh

# Run specific stack tests
./scripts/test-python.sh
cd core/server && bun test
cd core/dashboard && npm test
```

### Python Tests

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run with coverage
pytest -v --cov=templates/hooks/.claude/hooks --cov-fail-under=80

# Run specific test
pytest templates/hooks/.claude/hooks/tests/test_send_event.py::TestSendEventSync::test_event_sent_successfully

# Run with markers
pytest -m unit      # Fast unit tests only
pytest -m integration  # Integration tests
```

### Bun/TypeScript Tests

```bash
cd core/server

# Install dependencies
bun install

# Run all tests
bun test

# Run with coverage
bun test --coverage

# Watch mode
bun test --watch

# Run specific file
bun test src/__tests__/events.test.ts
```

### Vue Tests

```bash
cd core/dashboard

# Install dependencies
npm install

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm test -- --watch

# Run component tests only
npm test tests/components/
```

### Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Run with random order (catches state pollution)
pytest tests/integration/ -v --random-order

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

### Edge-Case Testing Scenarios

While not all edge cases can be automated in CI, these scenarios should be tested periodically:

#### 1. Disk Full Simulation
```bash
# Create a small loopback device to simulate disk full
dd if=/dev/zero of=/tmp/small.img bs=1M count=10
sudo losetup /dev/loop0 /tmp/small.img
sudo mkfs.ext4 /dev/loop0
sudo mount /dev/loop0 /mnt/test

# Run hub with data directory on limited space
DATABASE_PATH=/mnt/test/events.db bun run src/index.ts

# Send events until disk full
python tests/stress/disk_full_test.py
```

#### 2. Database Corruption Recovery
```python
# Simulate corrupted SQLite database
import sqlite3
import os

# Corrupt the WAL file
with open('/data/events.db-wal', 'r+b') as f:
    f.seek(100)
    f.write(b'\x00' * 100)

# Hub should detect and recover or fail gracefully
```

#### 3. Network Partition Simulation
```bash
# Using iptables to simulate network issues
# Block hub connectivity
sudo iptables -A OUTPUT -p tcp --dport 4000 -j DROP

# Events should queue locally
python send_test_events.py

# Restore connectivity
sudo iptables -D OUTPUT -p tcp --dport 4000 -j DROP

# Queued events should flush
```

#### 4. Clock Skew Testing
```bash
# Simulate clock skew between services
docker run --rm -it --cap-add SYS_TIME alpine \
  sh -c "date -s '2025-01-01 00:00:00' && wget http://hub:4000/health"

# Events with future timestamps should be handled
```

#### 5. Memory Exhaustion
```bash
# Run hub with memory limit
docker run -m 50m claude-observability/hub

# Send large payloads
python tests/stress/memory_test.py --payload-size 10MB

# Should handle gracefully without OOM crashes
```

#### 6. Slow Hub Response
```python
# Simulate slow hub with toxiproxy
docker run -d --name toxiproxy -p 8474:8474 -p 4001:4001 shopify/toxiproxy

# Add latency
toxiproxy-cli toxic add -n latency -t latency -a latency=5000 hub

# Events should timeout and queue
```

#### 7. Database Lock Contention
```bash
# Hold exclusive lock on database
sqlite3 /data/events.db "BEGIN EXCLUSIVE; SELECT pg_sleep(30);" &

# Send events - should handle lock timeout
python send_test_events.py
```

#### 8. Certificate Expiration (HTTPS)
```bash
# Generate expired certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days -1 -nodes -subj "/CN=localhost"

# Run hub with expired cert
HTTPS_CERT=cert.pem HTTPS_KEY=key.pem bun run src/index.ts

# Clients should handle gracefully
```

## Writing Tests

### TDD Workflow

1. **Red**: Write a failing test for new functionality
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code while keeping tests green

### Python Test Example

```python
def test_event_queued_when_hub_down(sample_event, mock_urlopen_failure, temp_queue_dir):
    """Test event queuing when hub is unreachable."""
    with patch.dict(os.environ, {'HOME': str(temp_queue_dir)}):
        result = send_event_sync(sample_event)
        
        assert result is True
        
        # Check queue file was created
        queue_file = temp_queue_dir / '.claude' / 'event_queue.jsonl'
        assert queue_file.exists()
```

### TypeScript Test Example

```typescript
describe('POST /events', () => {
  it('should reject duplicate UUID with 409 status', async () => {
    const duplicateEvent = {
      event_uuid: 'duplicate-uuid',
      source_app: 'test_app',
      hook_event_type: 'Stop'
    };
    
    // Mock existing event
    db.query().get.mockReturnValue({ id: 1 });
    
    const response = await server.fetch(
      new Request('http://localhost:4000/events', {
        method: 'POST',
        body: JSON.stringify(duplicateEvent)
      })
    );
    
    expect(response.status).toBe(409);
  });
});
```

### Vue Test Example

```javascript
it('filters events based on search input', async () => {
  wrapper = mount(App);
  
  wrapper.vm.events = [
    { event_uuid: '1', hook_event_type: 'PreToolUse', payload: { tool: 'Bash' } },
    { event_uuid: '2', hook_event_type: 'PostToolUse', payload: { tool: 'Git' } }
  ];
  
  await nextTick();
  expect(wrapper.findAll('.event-row')).toHaveLength(2);
  
  await wrapper.find('.filter-input').setValue('Bash');
  expect(wrapper.findAll('.event-row')).toHaveLength(1);
});
```

## Test Conventions

### Naming

- Test files: `test_*.py`, `*.test.ts`, `*.test.js`
- Test functions: `test_*` (Python), `it('should...')` (JS/TS)
- Describe blocks: Feature or component name
- Test names: Describe expected behavior clearly

### Organization

- Group related tests in describe blocks
- Use beforeEach/afterEach for setup/teardown
- Keep tests focused on single behaviors
- Mock external dependencies

### Assertions

- Use descriptive assertion messages
- Test both success and failure paths
- Verify edge cases and error handling
- Check for proper error messages

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Python Hooks | 80% | - |
| Bun Server | 80% | - |
| Vue Dashboard | 60% | - |
| Integration | N/A | - |

### What to Test

**High Priority (80%+ coverage)**:
- Event ingestion and validation
- Deduplication logic
- Queue mechanisms
- Agent hierarchy building
- WebSocket broadcasting
- Error handling

**Medium Priority (60%+ coverage)**:
- UI component behavior
- Event filtering
- State management
- User interactions

**Low Priority**:
- Static configuration
- Simple getters/setters
- Third-party integrations

## CI/CD Integration

Tests run automatically on:
- Every push to main/develop branches
- All pull requests
- Pre-commit hooks (optional)

### GitHub Actions

See `.github/workflows/test.yml` for the complete CI pipeline:
1. Linting (Python, TypeScript, Vue)
2. Unit tests across all stacks
3. Integration tests with Docker
4. Coverage reporting
5. DevContainer validation

### Pre-commit Hooks

To enable local pre-commit testing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Debugging Tests

### Python

```bash
# Run with debugger
pytest --pdb

# Show print statements
pytest -s

# Verbose output
pytest -vv
```

### JavaScript/TypeScript

```javascript
// Add debugger statement
it('test case', () => {
  debugger;  // Pause here when debugging
  expect(true).toBe(true);
});

// Run with Node inspector
node --inspect-brk node_modules/.bin/vitest
```

### Integration Tests

```bash
# Keep containers running after tests
docker-compose -f docker-compose.test.yml up

# Check logs
docker-compose -f docker-compose.test.yml logs test-hub

# Execute commands in container
docker-compose -f docker-compose.test.yml exec test-hub sh
```

## Best Practices

1. **Test First**: Write tests before implementation
2. **Keep It Simple**: Each test should verify one thing
3. **Fast Feedback**: Unit tests should run in <100ms
4. **Deterministic**: Tests should not be flaky
5. **Independent**: Tests should not depend on each other
6. **Readable**: Tests document expected behavior

## Common Issues

### Port Conflicts

If tests fail due to port conflicts:
```bash
# Find process using port
lsof -i :4000

# Use different test port
TEST_PORT=4001 pytest
```

### Database Lock

If SQLite database is locked:
```bash
# Remove test database
rm -f /tmp/test-events.db
```

### WebSocket Timeouts

Increase timeout for slow CI environments:
```javascript
// Increase timeout for specific test
it('slow test', async () => {
  // test code
}, 30000);  // 30 second timeout
```

## Contributing

When adding new features:
1. Start with a failing test
2. Implement the feature
3. Ensure all tests pass
4. Add integration test if needed
5. Update this guide if necessary

Remember: **No code without tests!**