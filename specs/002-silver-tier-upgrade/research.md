# Research & Technology Decisions - Silver Tier

**Feature**: Silver Tier - Autonomous Task Execution & Multi-Channel Communication
**Date**: 2026-02-25
**Status**: Complete

## Overview

This document captures all research findings and technology decisions made during Phase 0 planning for Silver Tier implementation. Each decision includes rationale, alternatives considered, and tradeoffs.

---

## Decision 1: MCP Server Integration Architecture

### Context

Silver Tier requires integration with 5 external platforms:
- Gmail (send emails)
- LinkedIn (post content)
- Facebook (post to pages/groups)
- Twitter/X (tweet and threads)
- WhatsApp Business API (monitor messages)

Each platform has different authentication mechanisms, rate limits, error handling, and API patterns.

### Research Findings

**Python MCP SDK**:
- Official SDK: `mcp` package from Anthropic
- Installation: `uv add mcp`
- Client usage: Create MCP client, connect to server URL, call tools
- Authentication: Pass tokens via MCP context or environment variables
- Error handling: Standard exception hierarchy (MCPError, ConnectionError, TimeoutError)

**MCP Protocol Benefits**:
1. **Decoupling**: Business logic separated from integration details
2. **Testability**: Mock MCP responses for integration tests
3. **Reusability**: Same MCP servers usable by other agents
4. **Standardization**: Uniform error handling across platforms
5. **Security**: Credentials managed by MCP server, not in application code

**Retry Strategies**:
- Exponential backoff with jitter: `delay = base_delay * (2 ** retry_count) + random(0, 1)`
- Recommended delays: 1s, 2s, 4s, 8s, max 60s
- Max retries: 3 attempts for transient errors
- Non-retryable errors: 400 Bad Request, 401 Unauthorized (requires re-auth)
- Retryable errors: 429 Rate Limit, 500 Internal Server Error, 502/503/504 Gateway errors, Network timeouts

**Connection Pooling**:
- HTTP connection pool per MCP server (reuse TCP connections)
- Max connections: 5 concurrent per server
- Connection timeout: 10 seconds
- Read timeout: 30 seconds
- Implementation: `requests.Session()` with `HTTPAdapter` and `PoolManager`

**Testing Approach**:
- Integration tests: Mock MCP server responses using `responses` library or custom mock server
- Contract tests: Validate request/response schemas match MCP server expectations
- E2E tests: Use sandbox accounts on real platforms (Gmail test account, LinkedIn developer account)

### Alternatives Considered

1. **Direct API Calls** (rejected):
   - Use platform SDKs: `google-api-python-client`, `tweepy`, `facebook-sdk`
   - **Pros**: No intermediary, full API control, fewer network hops
   - **Cons**: Complex authentication (OAuth flows per platform), tightly coupled code, hard to test, credential management burden, inconsistent error handling

2. **Hybrid Approach** (rejected):
   - MCP for some platforms, direct SDK for others
   - **Pros**: Flexibility to choose per platform
   - **Cons**: Inconsistent patterns, maintenance burden, two authentication systems, harder to reason about

### Decision

**Use MCP protocol for all external integrations.**

### Rationale

1. **Alignment with Constitution**: Principle IV (Agent Skills Architecture) encourages modular, reusable components
2. **Testing**: Mocking MCP responses is simpler than mocking 5 different SDK clients
3. **Security**: MCP servers manage OAuth flows and credential refresh, reducing attack surface
4. **Maintainability**: Single integration pattern across all platforms
5. **Performance**: ~50ms network overhead acceptable for non-realtime actions (email, social posts)

### Tradeoffs

**Added Complexity**:
- Users must configure and run MCP servers (or use hosted MCP services)
- Additional network hop adds latency (~50ms per call)

**Dependency Risk**:
- MCP server availability becomes critical dependency
- Mitigated by graceful degradation (if Gmail MCP down, other integrations continue)

**Implementation Overhead**:
- Need to develop MCP client library
- Estimated effort: 2-3 hours

### Implementation Notes

```python
# MCP Client usage pattern
from mcp_client import MCPClient

# Initialize client
gmail_mcp = MCPClient(url=os.getenv('GMAIL_MCP_URL'))

# Call tool with retry
response = gmail_mcp.call_tool(
    tool_name='send_email',
    arguments={
        'to': 'user@example.com',
        'subject': 'Test',
        'body': 'Hello!'
    },
    max_retries=3
)

# Handle response
if response.success:
    message_id = response.result['message_id']
else:
    error = response.error
```

---

## Decision 2: Scheduling Library Selection

### Context

Silver Tier needs cron-like scheduled tasks:
- Daily briefings at 09:00
- Weekly summaries on Monday at 08:00
- Custom recurring tasks (every N days at specific time)

Requirements:
- Persistent state (survive restarts)
- Missed execution handling (catch up if offline)
- Dynamic configuration (read from Company_Handbook.md)
- Cross-platform (Windows, macOS, Linux)

### Research Findings

**APScheduler 3.10+**:
- Mature Python scheduling library
- Supports cron syntax: `CronTrigger('0 9 * * *')` for daily at 09:00
- Job stores: Memory, SQL, MongoDB, Redis, or custom JSON file
- Missed execution: `misfire_grace_time` parameter (catch up within N seconds)
- Dynamic jobs: Add/remove jobs at runtime
- Event listeners: Job executed, missed, error events

**schedule library**:
- Lightweight, simple API
- No persistence (all schedules lost on restart)
- No cron syntax (manual time checking)
- Suitable for simple scripts, not production systems

**Celery**:
- Distributed task queue with scheduling (Celery Beat)
- Requires message broker (Redis or RabbitMQ)
- Overkill for single-user system
- Adds significant infrastructure complexity

### Alternatives Considered

1. **System Cron** (rejected):
   - Use OS cron jobs (crontab on Linux/macOS, Task Scheduler on Windows)
   - **Pros**: Proven, reliable, no Python dependencies
   - **Cons**: OS-specific, can't read Company_Handbook.md dynamically, hard to test, no cross-platform

2. **schedule library** (rejected):
   - Lightweight Python scheduling
   - **Pros**: Simple API, no dependencies
   - **Cons**: No persistence, no cron syntax, manual state management, no missed execution handling

3. **Celery** (rejected):
   - Production-grade distributed task queue
   - **Pros**: Battle-tested, many features, horizontal scaling
   - **Cons**: Requires Redis/RabbitMQ, complex setup, overkill for single user

### Decision

**Use APScheduler 3.10+ with custom JSON-based job store.**

### Rationale

1. **Persistence**: Custom JSON job store aligns with local-first principle (no Redis needed)
2. **Cron Syntax**: Supports standard cron patterns users understand
3. **Missed Execution**: Built-in grace period for catch-up
4. **Dynamic Configuration**: Load schedule definitions from Company_Handbook.md on startup or schedule change
5. **Cross-Platform**: Pure Python, works on all platforms
6. **Maintainability**: Well-documented, actively maintained

### Tradeoffs

**Dependency Added**:
- APScheduler library (~500KB)
- Acceptable cost for scheduling functionality

**Event Loop Management**:
- APScheduler requires event loop (asyncio or threading)
- Mitigated by simple scheduler.py main loop with BackgroundScheduler

**File-Based State**:
- JSON writes on every execution (~1KB files)
- Acceptable I/O overhead for scheduled tasks (not high-frequency)

### Implementation Notes

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
import json

# Custom JSON job store
class JSONJobStore:
    def __init__(self, path):
        self.path = path
        self.jobs = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self.jobs, f, indent=2)

# Scheduler setup
scheduler = BackgroundScheduler()

# Add daily briefing at 09:00
scheduler.add_job(
    func=generate_daily_briefing,
    trigger=CronTrigger(hour=9, minute=0),
    id='daily_briefing',
    name='Daily Briefing',
    misfire_grace_time=3600  # 1-hour grace period
)

scheduler.start()
```

---

## Decision 3: Rate Limiting Strategy

### Context

API rate limits to respect:
- Gmail: 500 emails/day (1 email per ~173 seconds average)
- LinkedIn: 100 posts/day
- Twitter: 2400 tweets/day
- Facebook: 200 posts/day
- WhatsApp: 1000 messages/day inbound (no sending in Silver)

Requirements:
- Prevent quota exhaustion
- Allow short bursts (send 5 emails quickly if quota available)
- Persistent state (survive restarts)
- Per-platform limits

### Research Findings

**Token Bucket Algorithm**:
- Bucket holds tokens (capacity = daily limit)
- Each action consumes 1 token
- Tokens refill at constant rate (daily_limit / 86400 tokens per second)
- If no tokens available, block or queue action
- Allows bursts (send multiple quickly) while preventing long-term exhaustion

**Leaky Bucket Algorithm**:
- Actions added to queue, processed at constant rate
- No bursts allowed
- Simpler than token bucket but less flexible

**Fixed Window Counter**:
- Count actions per time window (e.g., per day)
- Reset counter at window boundary (midnight)
- Issue: Burst at boundary (send 500 at 23:59, 500 at 00:01)

**Sliding Window Log**:
- Track timestamp of each action
- Count actions in last 24 hours
- Most accurate but memory-intensive

### Alternatives Considered

1. **No Rate Limiting** (rejected):
   - Trust user to not exceed limits
   - **Pros**: Simple, no overhead
   - **Cons**: Easy to accidentally hit quota, hard to debug, risk of API ban

2. **Fixed Window** (rejected):
   - Count per day, reset at midnight
   - **Pros**: Simple implementation
   - **Cons**: Burst vulnerability at window boundary

3. **Sliding Window Log** (rejected):
   - Track all action timestamps
   - **Pros**: Most accurate, no burst vulnerability
   - **Cons**: Memory-intensive (store 500+ timestamps for Gmail), complex cleanup

### Decision

**Token Bucket with persistent JSON state per platform.**

### Rationale

1. **User Experience**: Allows sending several emails quickly when needed
2. **Quota Protection**: Prevents exhausting daily limit
3. **Platform Behavior**: Matches how most APIs implement rate limiting internally
4. **Persistence**: JSON state file survives restarts
5. **Simplicity**: Easier to implement and reason about than sliding window

### Tradeoffs

**Complexity**:
- Requires token calculation, refill rate management
- State persistence adds I/O operations

**State Management**:
- JSON file writes on every action (~100 bytes)
- Acceptable overhead for action-based system (not high-frequency)

**Burst Control**:
- Allows bursts up to bucket capacity
- Could exhaust quota quickly if user approves many plans at once
- Mitigated by executor sequential processing with delays

### Implementation Notes

```python
import time
import json
from pathlib import Path

class TokenBucketRateLimiter:
    def __init__(self, platform, daily_limit, state_file):
        self.platform = platform
        self.capacity = daily_limit
        self.refill_rate = daily_limit / 86400  # Tokens per second
        self.state_file = Path(state_file)
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.tokens = state.get(self.platform, {}).get('tokens', self.capacity)
                self.last_refill = state.get(self.platform, {}).get('last_refill', time.time())
        else:
            self.tokens = self.capacity
            self.last_refill = time.time()

    def _save_state(self):
        state = {}
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)

        state[self.platform] = {
            'tokens': self.tokens,
            'last_refill': self.last_refill
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        refill_amount = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + refill_amount)
        self.last_refill = now

    def acquire(self, tokens=1):
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            self._save_state()
            return True
        return False

    def wait_time(self):
        """Calculate seconds until next token available"""
        self._refill()
        if self.tokens >= 1:
            return 0
        deficit = 1 - self.tokens
        return deficit / self.refill_rate

# Usage
gmail_limiter = TokenBucketRateLimiter('gmail', 500, 'vault/Logs/rate_limit_state.json')

if gmail_limiter.acquire():
    # Send email
    pass
else:
    wait = gmail_limiter.wait_time()
    print(f"Rate limit reached. Wait {wait:.0f} seconds")
```

---

## Decision 4: Plan Validation Schema Format

### Context

Executor must validate plans before execution to ensure:
- Required fields present (recipient, subject, body for emails)
- Field types correct (string, datetime, enum)
- Field constraints met (email format, character limits, enum values)

Invalid plans should be rejected with clear error messages and moved to /Quarantine/.

### Research Findings

**JSON Schema**:
- Standard validation format (JSON Schema Draft 7)
- Python library: `jsonschema` (v4.20+)
- Generates detailed error messages with field paths
- Widely used, well-documented
- Supports: type validation, format validation (email, uri), pattern matching (regex), min/max length, enum constraints

**Pydantic**:
- Python data validation using type annotations
- Automatic validation on object creation
- Better IDE support (type hints)
- More Pythonic than JSON Schema

**Custom Validation**:
- Write validation functions manually
- Full control, no dependencies
- Harder to maintain, less standardized

### Alternatives Considered

1. **Pydantic** (rejected):
   - Type-annotated Python classes for validation
   - **Pros**: Pythonic, IDE support, automatic serialization
   - **Cons**: Tighter coupling (validation embedded in code), harder to share schemas with non-Python systems

2. **Custom Validation** (rejected):
   - Manual validation functions
   - **Pros**: Full control, no dependencies
   - **Cons**: Harder to maintain, non-standard, more code

### Decision

**JSON Schema with jsonschema library.**

### Rationale

1. **Standard Format**: JSON Schema is widely adopted, language-agnostic
2. **Clear Errors**: Generates detailed validation error messages
3. **Reusable**: Schema files can be used for contract tests
4. **Documented**: Extensive JSON Schema documentation and examples
5. **Integration**: Works well with pytest for contract testing

### Tradeoffs

**Additional Dependency**:
- jsonschema library (~200KB)
- Acceptable cost for validation functionality

**YAML Frontmatter Parsing**:
- Plans have YAML frontmatter, JSON Schema validates parsed data
- Need to parse YAML → dict → validate → OK
- Minor overhead for YAML parsing step

**Schema Maintenance**:
- Schema files must be kept in sync with code
- Mitigated by contract tests that validate schemas

### Implementation Notes

```python
import json
import yaml
from jsonschema import validate, ValidationError
from pathlib import Path

# Load schema
schema_path = Path('specs/002-silver-tier-upgrade/contracts/email-plan-schema.json')
with open(schema_path, 'r') as f:
    email_schema = json.load(f)

# Parse plan file
plan_path = Path('vault/Approved/PLAN_email_123.md')
with open(plan_path, 'r') as f:
    content = f.read()

# Extract YAML frontmatter
if content.startswith('---'):
    parts = content.split('---', 2)
    frontmatter = yaml.safe_load(parts[1])
else:
    raise ValueError("Plan missing YAML frontmatter")

# Validate against schema
try:
    validate(instance=frontmatter, schema=email_schema)
    print("Plan valid")
except ValidationError as e:
    print(f"Validation error: {e.message}")
    print(f"Field: {'.'.join(str(p) for p in e.path)}")
    # Move to Quarantine with error details
```

---

## Decision 5: WhatsApp Business API Integration Approach

### Context

WhatsApp integration options:
1. **WhatsApp Business Cloud API** (Meta's official cloud-hosted API)
2. **WhatsApp Business On-Premises API** (self-hosted official API)
3. **Third-Party Services** (Twilio, MessageBird, etc.)
4. **WhatsApp Web Automation** (Playwright/Selenium - unofficial)

Requirements:
- Official/supported API (no terms of service violations)
- Message polling (webhook optional for Silver, required for Gold)
- Media download support
- Reasonable cost

### Research Findings

**WhatsApp Business Cloud API**:
- **Authentication**: Business account + phone number ID + access token
- **Pricing**: Free tier 1000 conversations/month, then ~$0.005-0.10 per conversation
- **Rate Limits**: 80 messages/second, 1000 messages/day for new accounts
- **Media**: Download via media API endpoint
- **Polling**: GET /messages endpoint (not officially supported, webhooks recommended)
- **Setup**: Requires Meta Business verification (can take 1-2 weeks)

**WhatsApp Business On-Premises API**:
- **Cost**: Expensive (~$3000-5000/month for infrastructure)
- **Complexity**: Self-hosted on cloud VMs, Docker containers
- **Use Case**: High-volume businesses (>1M messages/month)
- **Not Suitable**: Overkill for single-user personal AI employee

**Third-Party MCP Server**:
- Community-built MCP servers that wrap WhatsApp API
- Abstracts authentication complexity
- Simplifies integration via MCP protocol

### Alternatives Considered

1. **WhatsApp Business On-Premises** (rejected):
   - **Pros**: Full control, self-hosted
   - **Cons**: Expensive, complex infrastructure, overkill for personal use

2. **Third-Party Services** (rejected):
   - Use Twilio/MessageBird WhatsApp integration
   - **Pros**: Easier setup, managed infrastructure
   - **Cons**: Monthly costs, vendor lock-in, less control

3. **WhatsApp Web Automation** (rejected):
   - Unofficial browser automation with Playwright
   - **Pros**: No API approval needed, free
   - **Cons**: Violates terms of service, fragile (breaks on UI changes), no official support

### Decision

**WhatsApp Business Cloud API via MCP server.**

### Rationale

1. **Official API**: Supported by Meta, no ToS violations
2. **Cost-Effective**: Free tier covers personal use (1000 conversations/month)
3. **MCP Integration**: Abstracts authentication complexity
4. **Polling Mode**: Sufficient for Silver Tier (pull messages every 60 seconds)
5. **Webhook Upgrade**: Can add webhooks in Gold Tier for instant notifications

### Tradeoffs

**Setup Complexity**:
- Requires Meta Business verification (1-2 weeks)
- Phone number setup and verification
- Access token management

**Polling Latency**:
- 60-second polling interval means up to 2-minute delay
- Acceptable for Silver Tier (meets SC-011: messages appear within 2 minutes)

**MCP Server Dependency**:
- Requires WhatsApp MCP server (user configures or uses hosted service)
- Mitigated by making WhatsApp optional (like Gmail in Bronze)

### Implementation Notes

```python
# WhatsApp watcher polls MCP server
from mcp_client import MCPClient

whatsapp_mcp = MCPClient(url=os.getenv('WHATSAPP_MCP_URL'))

# Poll for new messages
response = whatsapp_mcp.call_tool(
    tool_name='get_messages',
    arguments={
        'phone_number_id': os.getenv('WHATSAPP_PHONE_NUMBER_ID'),
        'since': last_poll_timestamp
    }
)

# Process messages
for message in response.result['messages']:
    message_id = message['id']

    # Check for duplicates
    if message_id in processed_message_ids:
        continue

    # Create WhatsApp entity in /Needs_Action/
    create_whatsapp_entity(message)
    processed_message_ids.add(message_id)
```

---

## Summary of Technology Decisions

| Area | Decision | Key Rationale |
|------|----------|---------------|
| **External Integrations** | MCP protocol for all platforms | Decoupling, testability, standardization |
| **Scheduling** | APScheduler with JSON job store | Cross-platform, cron syntax, persistent state |
| **Rate Limiting** | Token bucket with persistent state | Allows bursts, prevents quota exhaustion |
| **Plan Validation** | JSON Schema with jsonschema library | Standard format, clear errors, reusable |
| **WhatsApp API** | WhatsApp Business Cloud API via MCP | Official, cost-effective, MCP-aligned |

---

## Dependencies Added

**Python Packages** (add to pyproject.toml via UV):
```toml
[project.dependencies]
# Existing (Bronze Tier)
google-auth = ">=2.0.0"
google-api-python-client = ">=2.0.0"
watchdog = ">=3.0.0"
python-dotenv = ">=1.0.0"
pyyaml = ">=6.0.0"

# New (Silver Tier)
mcp = ">=0.9.0"  # MCP SDK for Python client
apscheduler = ">=3.10.0"  # Scheduling library
requests = ">=2.31.0"  # HTTP library for MCP calls
jsonschema = ">=4.20.0"  # JSON Schema validation
```

**Installation Command**:
```bash
uv add mcp apscheduler requests jsonschema
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MCP server unavailability | Medium | High | Graceful degradation, MCP mock for tests |
| APScheduler state corruption | Low | Medium | Atomic JSON writes, backup on startup |
| Rate limit complexity | Medium | Low | Conservative initial limits, tuning |
| WhatsApp API setup delays | High | Low | Make WhatsApp optional, provide setup guide |
| Token bucket burst abuse | Low | Medium | Sequential executor processing, delays |

---

## Next Steps

1. **Implementation**: Proceed to Phase 1 (data models, contracts, quickstart)
2. **ADRs**: Create 3 ADRs for MCP integration, scheduling engine, rate limiting
3. **Agent Context**: Update with new technologies (APScheduler, MCP SDK)
4. **MCP Configuration**: Document MCP server setup for each platform

---

**Research Status**: ✅ **COMPLETE**

**Date Completed**: 2026-02-25

**Next Phase**: Phase 1 - Data Model Design & API Contracts
