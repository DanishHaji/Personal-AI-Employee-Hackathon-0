/**
 * PM2 Ecosystem Configuration for Personal AI Employee - Bronze Tier MVP
 *
 * This configuration manages three background processes:
 * - Gmail Watcher: Monitors Gmail inbox for important/urgent emails (FR-004)
 * - Filesystem Watcher: Monitors /Inbox/ folder for dropped files (FR-009)
 * - Orchestrator: Monitors /Needs_Action/ and triggers Claude Code (FR-015)
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

// Note: Gmail watcher is optional - can be disabled if credentials not available
// Set GMAIL_ENABLED=false in .env to skip Gmail watcher
const gmailEnabled = process.env.GMAIL_ENABLED !== 'false';

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

module.exports = { apps };
