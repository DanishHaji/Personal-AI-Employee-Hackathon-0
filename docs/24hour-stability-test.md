# 24-Hour Stability Test Guide

**Performance Validation for Bronze Tier MVP (T057, SC-005)**

This guide describes how to run a 24-hour stability test to validate the system runs continuously without crashes or manual intervention.

---

## Test Objective

Validate that the Personal AI Employee system meets **SC-005**:

> System runs continuously for 24 hours without crashes or manual intervention (tested with Watchers + Orchestrator running)

## Prerequisites

Before starting the test:

1. **System Setup Complete**:
   - ✅ Obsidian vault initialized
   - ✅ Gmail API credentials configured
   - ✅ PM2 installed globally
   - ✅ All dependencies installed (`uv sync`)

2. **Initial Validation**:
   ```bash
   # Verify vault structure
   ls /path/to/vault
   # Expected: Inbox, Needs_Action, Plans, Logs, etc.

   # Test Gmail authentication
   uv run python src/watchers/gmail_watcher.py
   # Should connect successfully (Ctrl+C to stop)

   # Test file drop
   touch /path/to/vault/Inbox/test.txt
   # Should appear in /Needs_Action/ within 30 seconds
   ```

3. **Monitoring Tools**:
   - Terminal access for PM2 commands
   - System monitoring (htop, Activity Monitor, Task Manager)
   - Disk space monitoring

---

## Test Procedure

### Phase 1: Startup (0:00 - 0:10)

1. **Start all watchers with PM2**:

```bash
cd /path/to/ai-employee
pm2 start ecosystem.config.js
```

2. **Verify all processes started**:

```bash
pm2 status
```

Expected output:
```
┌────┬────────────────────────┬─────────┬──────┬───────────┐
│ id │ name                   │ status  │ cpu  │ memory    │
├────┼────────────────────────┼─────────┼──────┼───────────┤
│ 0  │ gmail-watcher          │ online  │ 0%   │ 45.2 MB   │
│ 1  │ filesystem-watcher     │ online  │ 0%   │ 40.1 MB   │
│ 2  │ orchestrator           │ online  │ 0%   │ 38.5 MB   │
└────┴────────────────────────┴─────────┴──────┴───────────┘
```

3. **Check initial logs**:

```bash
pm2 logs --lines 20
```

Expected: No errors, watchers started successfully

4. **Open Obsidian vault**:
   - Verify Dashboard.md shows all watchers running
   - Note initial pending counts

5. **Record baseline metrics**:

```bash
# Note start time
date
echo "Test started: $(date)" > stability-test-log.txt

# Record initial memory usage
pm2 status >> stability-test-log.txt

# Record disk space
df -h /path/to/vault >> stability-test-log.txt
```

### Phase 2: Monitoring (0:10 - 23:50)

During the 24-hour period, perform these checks:

#### Automated Monitoring (Every 15 Minutes)

Set up automated health checks with cron or a monitoring script:

```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP] Health Check" >> stability-test-log.txt

# Check PM2 status
pm2 jlist | jq -r '.[] | "\(.name): \(.pm2_env.status)"' >> stability-test-log.txt

# Check memory usage
echo "Memory:" >> stability-test-log.txt
pm2 jlist | jq -r '.[] | "  \(.name): \(.monit.memory / 1024 / 1024 | floor) MB"' >> stability-test-log.txt

# Check restart count (should be 0)
echo "Restarts:" >> stability-test-log.txt
pm2 jlist | jq -r '.[] | "  \(.name): \(.pm2_env.restart_time) restarts"' >> stability-test-log.txt

echo "" >> stability-test-log.txt
EOF

chmod +x monitor.sh

# Run every 15 minutes
watch -n 900 ./monitor.sh
```

#### Manual Checks (Every 6 Hours)

**At 6:00, 12:00, 18:00, 00:00**:

1. **Process Status**:
   ```bash
   pm2 status
   ```
   - All processes should show "online"
   - Uptime should be continuous

2. **Log Review**:
   ```bash
   pm2 logs --lines 100 | grep -i "error\|fatal\|crash"
   ```
   - Should find no critical errors
   - Rate limit warnings are acceptable (handled by backoff)

3. **Dashboard Check**:
   - Open Obsidian vault
   - Verify Dashboard.md updates
   - Check system health status

4. **Resource Usage**:
   ```bash
   # Check CPU and memory
   pm2 monit  # Interactive monitoring

   # Or programmatically
   pm2 jlist | jq -r '.[] | "\(.name): CPU \(.monit.cpu)%, Memory \(.monit.memory / 1024 / 1024 | floor) MB"'
   ```

5. **Disk Space**:
   ```bash
   df -h /path/to/vault
   ```
   - Ensure sufficient space (>1GB free)

6. **Audit Logs**:
   ```bash
   # Check today's audit log
   cat /path/to/vault/Logs/$(date +%Y-%m-%d).json | wc -l
   ```
   - Should show activity

7. **Heartbeat Check**:
   ```bash
   cat /path/to/vault/Logs/heartbeat.json
   ```
   - All watchers should have recent timestamps (< 5 minutes)

#### Test Activity (Throughout Test)

To ensure watchers are active, generate test events:

**Gmail Activity**:
- Send 2-3 test emails per day with subject "TEST: [timestamp]"
- Verify emails appear in /Needs_Action/ within 2 minutes

**File Drop Activity**:
- Drop 2-3 test files into /Inbox/ per day
- Verify files appear in /Needs_Action/ within 30 seconds

**Plan Generation** (optional):
- Manually trigger plan generation for test items
- Verify plans created in /Plans/

### Phase 3: Completion (23:50 - 24:00)

1. **Final Health Check**:

```bash
pm2 status
pm2 logs --lines 50
```

2. **Collect Final Metrics**:

```bash
# Record end time
echo "Test completed: $(date)" >> stability-test-log.txt

# Final PM2 status
echo "Final Status:" >> stability-test-log.txt
pm2 status >> stability-test-log.txt

# Total uptime
pm2 jlist | jq -r '.[] | "\(.name): uptime \(.pm2_env.pm_uptime / 1000 / 60 / 60 | floor) hours"' >> stability-test-log.txt

# Restart count
pm2 jlist | jq -r '.[] | "\(.name): \(.pm2_env.restart_time) restarts"' >> stability-test-log.txt

# Resource usage
echo "Resource Usage:" >> stability-test-log.txt
pm2 jlist | jq -r '.[] | "  \(.name): \(.monit.memory / 1024 / 1024 | floor) MB memory, \(.monit.cpu)% CPU"' >> stability-test-log.txt

# Disk usage
echo "Disk Usage:" >> stability-test-log.txt
df -h /path/to/vault >> stability-test-log.txt
```

3. **Audit Log Analysis**:

```bash
# Count total events
cat /path/to/vault/Logs/*.json | wc -l

# Count by type
cat /path/to/vault/Logs/*.json | jq -r '.action_type' | sort | uniq -c
```

4. **Stop Processes**:

```bash
pm2 stop all
pm2 save
```

---

## Success Criteria

The test **PASSES** if ALL conditions are met:

1. **✅ Zero crashes**: All 3 processes show 0 restarts
2. **✅ Continuous uptime**: All processes ran for full 24 hours
3. **✅ No manual intervention**: No `pm2 restart` commands needed
4. **✅ Heartbeat active**: heartbeat.json shows recent timestamps throughout
5. **✅ No memory leaks**: Memory usage stable or growing < 10% over 24 hours
6. **✅ Functional watchers**: Test emails/files detected throughout test
7. **✅ Dashboard updates**: Dashboard.md reflects current state
8. **✅ Log integrity**: No fatal errors in PM2 logs or audit logs

The test **FAILS** if ANY condition occurs:

- ❌ Any process crashes (restart_count > 0)
- ❌ Process stops and requires manual restart
- ❌ Memory grows >50% over 24 hours (indicates memory leak)
- ❌ Watcher stops detecting new items
- ❌ Dashboard stops updating
- ❌ Fatal errors in logs

---

## Expected Results

### Normal Behavior

- **Memory Usage**: 40-60 MB per process (stable)
- **CPU Usage**: 0-5% average (spikes during checks normal)
- **Restarts**: 0 (PM2 auto-restart feature not triggered)
- **Uptime**: Exactly 24 hours
- **Heartbeats**: Updated every 60 seconds
- **Logs**: 200-500 audit log entries (depends on activity)

### Acceptable Issues

These are normal and do NOT indicate failure:

- **Gmail rate limit warnings**: Handled by exponential backoff
- **Network timeouts** (1-2 occurrences): Handled by retry logic
- **Temporary vault inaccessibility** (< 1 minute): Queuing mechanism activates

### Failure Indicators

- Process restart count > 0
- Memory usage > 200 MB
- Continuous error messages
- Dashboard not updating for > 10 minutes
- Heartbeat stale for > 10 minutes

---

## Troubleshooting Common Issues

### Process Crashes

If a process crashes during test:

1. **Check PM2 logs**:
   ```bash
   pm2 logs <process-name> --err --lines 100
   ```

2. **Check audit logs**:
   ```bash
   cat /path/to/vault/Logs/$(date +%Y-%m-%d).json | tail -20
   ```

3. **Identify root cause**:
   - Python exception? → Code bug
   - Out of memory? → Memory leak
   - Permission error? → Vault access issue

4. **Document the failure** in stability-test-log.txt

### Memory Leak Detection

If memory grows continuously:

```bash
# Monitor memory every 5 minutes for 1 hour
for i in {1..12}; do
  echo "Check $i: $(date)"
  pm2 jlist | jq -r '.[] | "\(.name): \(.monit.memory / 1024 / 1024 | floor) MB"'
  sleep 300
done
```

If memory grows > 5MB per hour → investigate leak

### Network Issues

If Gmail API fails:

1. Check internet connectivity: `ping google.com`
2. Verify credentials not expired: `ls -la credentials.json token.json`
3. Check rate limits: Look for HTTP 429 in logs

---

## Test Report Template

After completing the test, create a report:

```markdown
# 24-Hour Stability Test Report

**Date**: YYYY-MM-DD
**Test Duration**: 24:00:00
**System**: Personal AI Employee Bronze Tier MVP

## Results

**Overall Status**: ✅ PASS / ❌ FAIL

### Process Uptime

- Gmail Watcher: XX:XX:XX (restarts: 0)
- Filesystem Watcher: XX:XX:XX (restarts: 0)
- Orchestrator: XX:XX:XX (restarts: 0)

### Resource Usage

| Process | Initial Memory | Final Memory | Peak Memory | Avg CPU |
|---------|----------------|--------------|-------------|---------|
| gmail-watcher | 45 MB | 48 MB | 52 MB | 1.2% |
| filesystem-watcher | 40 MB | 42 MB | 45 MB | 0.8% |
| orchestrator | 38 MB | 40 MB | 43 MB | 0.5% |

### Activity

- Emails detected: XX
- Files processed: XX
- Plans created: XX
- Dashboard updates: XX
- Audit log entries: XX

### Issues Encountered

- None / [List any issues]

### Conclusion

[Summary of test results and any recommendations]

**SC-005 Compliance**: ✅ Validated / ❌ Not validated
```

---

## Automation Script

For automated 24-hour testing, use this script:

```bash
#!/bin/bash
# 24hour-test.sh - Automated stability test runner

TEST_LOG="stability-test-$(date +%Y%m%d-%H%M%S).txt"

echo "Starting 24-hour stability test..." | tee -a $TEST_LOG
echo "Start time: $(date)" | tee -a $TEST_LOG

# Start processes
pm2 start ecosystem.config.js
sleep 10

# Record initial state
echo "Initial state:" | tee -a $TEST_LOG
pm2 status | tee -a $TEST_LOG

# Monitor for 24 hours
for hour in {1..24}; do
  sleep 3600  # 1 hour

  echo "Hour $hour check ($(date)):" | tee -a $TEST_LOG

  # Check status
  pm2 jlist | jq -r '.[] | "\(.name): \(.pm2_env.status), \(.pm2_env.restart_time) restarts, \(.monit.memory / 1024 / 1024 | floor) MB"' | tee -a $TEST_LOG

  # Check for crashes
  CRASHES=$(pm2 jlist | jq -r '.[].pm2_env.restart_time' | awk '{s+=$1} END {print s}')
  if [ "$CRASHES" -gt 0 ]; then
    echo "❌ FAILURE: Detected $CRASHES restart(s)" | tee -a $TEST_LOG
    pm2 logs --err --lines 50 | tee -a $TEST_LOG
    exit 1
  fi

  echo "" | tee -a $TEST_LOG
done

echo "Test completed: $(date)" | tee -a $TEST_LOG
echo "✅ 24-hour test PASSED - No crashes detected" | tee -a $TEST_LOG

pm2 status | tee -a $TEST_LOG
```

---

**Test Duration**: 24 hours
**Recommended Schedule**: Run during low-activity period (weekend)
**Prerequisites**: SC-001 through SC-004 already validated
**Next Step**: After passing, Bronze Tier MVP is production-ready
