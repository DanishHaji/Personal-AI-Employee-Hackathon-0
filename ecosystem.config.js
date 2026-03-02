/**
 * PM2 Ecosystem Configuration for Personal AI Employee - Gold Tier
 *
 * This configuration manages all background processes across three tiers:
 *
 * Bronze Tier (Monitoring):
 * - Gmail Watcher: Monitors Gmail inbox for important/urgent emails (FR-004)
 * - Filesystem Watcher: Monitors /Inbox/ folder for dropped files (FR-009)
 * - Orchestrator: Monitors /Needs_Action/ and triggers Claude Code (FR-015)
 *
 * Silver Tier (Execution):
 * - Executor: Monitors /Approved/ folder and executes approved plans (US1)
 * - Scheduler: Manages scheduled tasks and daily briefings (US4)
 * - WhatsApp Watcher: Monitors WhatsApp Business API for messages (US3)
 *
 * Gold Tier (Autonomous AI):
 * - Calendar Watcher: Syncs Google Calendar and manages meetings (US2)
 * - Analytics Engine: Generates weekly insights and patterns (US4)
 * - Suggestion Engine: Proactive follow-ups and reminders (US5)
 * - CRM Watcher: Monitors relationships and contact health (US7)
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 status
 *   pm2 logs
 *   pm2 stop all
 *   pm2 restart all
 *
 * Startup on boot:
 *   pm2 startup
 *   pm2 save
 */

// Feature flags from .env
const gmailEnabled = process.env.GMAIL_ENABLED !== 'false';
const calendarEnabled = process.env.CALENDAR_MANAGEMENT_ENABLED === 'true';
const analyticsEnabled = process.env.ANALYTICS_INSIGHTS_ENABLED === 'true';
const suggestionsEnabled = process.env.PROACTIVE_SUGGESTIONS_ENABLED === 'true';
const crmEnabled = process.env.CRM_INTEGRATION_ENABLED === 'true';

const apps = [];

// Gmail Watcher (OPTIONAL - only if credentials available)
if (gmailEnabled) {
  apps.push({
    name: 'gmail-watcher',
    script: 'src/watchers/gmail_watcher.py',
    interpreter: 'python3',
    cwd: __dirname,

      // Auto-restart settings
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,  // 5 seconds between restarts
      min_uptime: 10000,    // Consider app stable after 10 seconds

      // Environment variables (read from .env)
      env: {
        VAULT_PATH: process.env.VAULT_PATH || './vault',
        PYTHONUNBUFFERED: '1'  // Disable Python output buffering for logs
      },

      // Log settings
      error_file: './logs/pm2/gmail-watcher-error.log',
      out_file: './logs/pm2/gmail-watcher-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,

      // Resource limits
      max_memory_restart: '200M',  // Restart if memory exceeds 200MB

      // Stop gracefully
      kill_timeout: 5000,
      wait_ready: false,
      listen_timeout: 3000
    });
}

// Filesystem Watcher (ALWAYS ENABLED)
apps.push({
  name: 'filesystem-watcher',
  script: 'src/watchers/filesystem_watcher.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/filesystem-watcher-error.log',
  out_file: './logs/pm2/filesystem-watcher-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000,
  wait_ready: false,
  listen_timeout: 3000
});

// Orchestrator (ALWAYS ENABLED)
apps.push({
  name: 'orchestrator',
  script: 'src/orchestrator.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/orchestrator-error.log',
  out_file: './logs/pm2/orchestrator-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000,
  wait_ready: false,
  listen_timeout: 3000
});

// ========================================
// SILVER TIER - Execution Processes
// ========================================

// Executor (ALWAYS ENABLED - Silver Tier US1)
apps.push({
  name: 'executor',
  script: 'src/executor.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    DRY_RUN: process.env.DRY_RUN || 'true',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/executor-error.log',
  out_file: './logs/pm2/executor-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000,
  wait_ready: false,
  listen_timeout: 3000
});

// Scheduler (ALWAYS ENABLED - Silver Tier US4)
apps.push({
  name: 'scheduler',
  script: 'src/scheduler.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    DRY_RUN: process.env.DRY_RUN || 'true',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/scheduler-error.log',
  out_file: './logs/pm2/scheduler-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000,
  wait_ready: false,
  listen_timeout: 3000
});

// WhatsApp Watcher (ALWAYS ENABLED - Silver Tier US3)
apps.push({
  name: 'whatsapp-watcher',
  script: 'src/watchers/whatsapp_watcher.py',
  interpreter: 'python3',
  cwd: __dirname,
  autorestart: true,
  max_restarts: 10,
  restart_delay: 5000,
  min_uptime: 10000,
  env: {
    VAULT_PATH: process.env.VAULT_PATH || './vault',
    DRY_RUN: process.env.DRY_RUN || 'true',
    PYTHONUNBUFFERED: '1'
  },
  error_file: './logs/pm2/whatsapp-watcher-error.log',
  out_file: './logs/pm2/whatsapp-watcher-out.log',
  log_date_format: 'YYYY-MM-DD HH:mm:ss',
  merge_logs: true,
  max_memory_restart: '200M',
  kill_timeout: 5000,
  wait_ready: false,
  listen_timeout: 3000
});

// ========================================
// GOLD TIER - Autonomous AI Processes
// ========================================

// Calendar Watcher (OPTIONAL - Gold Tier US2)
if (calendarEnabled) {
  apps.push({
    name: 'calendar-watcher',
    script: 'src/watchers/calendar_watcher.py',
    interpreter: 'python3',
    cwd: __dirname,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
    min_uptime: 10000,
    env: {
      VAULT_PATH: process.env.VAULT_PATH || './vault',
      GOOGLE_CALENDAR_CREDENTIALS_PATH: process.env.GOOGLE_CALENDAR_CREDENTIALS_PATH || './google_calendar_credentials.json',
      GOOGLE_CALENDAR_TOKEN_PATH: process.env.GOOGLE_CALENDAR_TOKEN_PATH || './google_calendar_token.json',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/pm2/calendar-watcher-error.log',
    out_file: './logs/pm2/calendar-watcher-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    max_memory_restart: '300M',  // Higher memory for calendar API
    kill_timeout: 5000,
    wait_ready: false,
    listen_timeout: 3000
  });
}

// Analytics Engine (OPTIONAL - Gold Tier US4)
if (analyticsEnabled) {
  apps.push({
    name: 'analytics-engine',
    script: 'src/services/analytics_engine.py',
    interpreter: 'python3',
    cwd: __dirname,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
    min_uptime: 10000,
    env: {
      VAULT_PATH: process.env.VAULT_PATH || './vault',
      ANALYTICS_SCHEDULE: process.env.ANALYTICS_SCHEDULE || '0 17 * * 5',  // Friday 5pm
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/pm2/analytics-engine-error.log',
    out_file: './logs/pm2/analytics-engine-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    max_memory_restart: '500M',  // Higher memory for pandas processing
    kill_timeout: 5000,
    wait_ready: false,
    listen_timeout: 3000
  });
}

// Suggestion Engine (OPTIONAL - Gold Tier US5)
if (suggestionsEnabled) {
  apps.push({
    name: 'suggestion-engine',
    script: 'src/services/suggestion_engine.py',
    interpreter: 'python3',
    cwd: __dirname,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
    min_uptime: 10000,
    env: {
      VAULT_PATH: process.env.VAULT_PATH || './vault',
      SUGGESTION_CHECK_INTERVAL: process.env.SUGGESTION_CHECK_INTERVAL || '3600',
      MAX_SUGGESTIONS_PER_CATEGORY: process.env.MAX_SUGGESTIONS_PER_CATEGORY || '3',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/pm2/suggestion-engine-error.log',
    out_file: './logs/pm2/suggestion-engine-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    max_memory_restart: '300M',
    kill_timeout: 5000,
    wait_ready: false,
    listen_timeout: 3000
  });
}

// CRM Watcher (OPTIONAL - Gold Tier US7)
if (crmEnabled) {
  apps.push({
    name: 'crm-watcher',
    script: 'src/watchers/crm_watcher.py',
    interpreter: 'python3',
    cwd: __dirname,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
    min_uptime: 10000,
    env: {
      VAULT_PATH: process.env.VAULT_PATH || './vault',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/pm2/crm-watcher-error.log',
    out_file: './logs/pm2/crm-watcher-out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    max_memory_restart: '300M',
    kill_timeout: 5000,
    wait_ready: false,
    listen_timeout: 3000
  });
}

module.exports = { apps };
