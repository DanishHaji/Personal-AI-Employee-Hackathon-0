# Odoo MCP Server - Platinum Tier US5

Professional accounting integration for Personal AI Employee using Odoo Community Edition.

## Overview

The Odoo MCP server provides seamless integration between the AI Employee expense tracking system and Odoo's accounting platform, enabling:

- **Automatic expense syncing** to Odoo accounting
- **Real-time budget monitoring** and alerts
- **Financial reporting** with month-over-month analytics
- **Professional accounting** with vendor management
- **Audit compliance** with complete expense trail

## Features

### 1. Expense Syncing
- Auto-sync approved expenses to Odoo
- Category mapping to Odoo chart of accounts
- Vendor auto-creation and lookup
- Receipt attachment linking
- Sync event logging

### 2. Budget Management
- Real-time budget status from Odoo
- Budget threshold alerts (80% warning, 100% critical)
- Automatic alert creation in `Needs_Action/`
- Category-level budget tracking

### 3. Financial Reporting
- Monthly financial reports
- Budget variance analysis
- Vendor spending breakdown
- Month-over-month trends
- Export to Odoo formats

### 4. MCP Tools Available

#### `odoo_create_expense`
Create expense entry in Odoo accounting.

```json
{
  "date": "2026-03-12",
  "amount": 45.99,
  "vendor": "Adobe",
  "category": "software",
  "description": "Creative Cloud subscription",
  "account_code": "600400"
}
```

#### `odoo_get_budget_status`
Get current budget status from Odoo.

```json
{
  "month": "2026-03"
}
```

#### `odoo_generate_financial_report`
Generate financial report for date range.

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-31",
  "format": "pdf"
}
```

#### `odoo_sync_all_expenses`
Batch sync all approved expenses to Odoo.

```json
{
  "month": "2026-03",
  "dry_run": false
}
```

#### `odoo_backup_database`
Create Odoo database backup.

```json
{
  "include_filestore": true
}
```

## Installation

### 1. Install Odoo (Cloud VM)

```bash
# On Ubuntu 22.04 server
cd /opt/ai-employee/deployment
sudo ./install-odoo.sh
```

This script will:
- Install PostgreSQL database
- Clone Odoo Community Edition v17.0
- Configure nginx reverse proxy
- Create systemd services
- Generate configuration files

### 2. Setup SSL Certificate

```bash
sudo ./setup-ssl.sh odoo.yourdomain.com
```

### 3. Configure Odoo

1. Access Odoo at `https://odoo.yourdomain.com`
2. Create database: `odoo`
3. Set admin password
4. Install **Accounting** module
5. Configure chart of accounts:
   - 600000: Miscellaneous Expenses
   - 600100: Meals & Entertainment
   - 600200: Transportation
   - 600300: Utilities
   - 600400: Software & Subscriptions
   - 600500: Office Supplies
   - 600600: Marketing & Advertising
   - 600700: Professional Services
   - 600800: Training & Education
   - 600900: Travel & Accommodation
   - 601000: Entertainment & Events
   - 601100: Health & Insurance

6. Generate API key:
   - Settings → Users → Administrator
   - API Keys → Generate New Key
   - Copy key for configuration

### 4. Configure AI Employee

Update `.env.cloud`:

```bash
# Odoo Integration (Platinum Tier US5)
ODOO_URL=https://odoo.yourdomain.com
ODOO_DATABASE=odoo
ODOO_USERNAME=admin
ODOO_API_KEY=your_api_key_here
```

### 5. Setup Automated Backups

```bash
# Install cron jobs for automated tasks
cd /opt/ai-employee/deployment/scripts
sudo ./setup-cron-jobs.sh
```

This configures:
- Daily Odoo database backup (2 AM)
- Weekly health reports (Monday 8 AM)
- Monthly financial reports (1st of month, 9 AM)

## Usage

### Automatic Expense Syncing

Expenses are automatically synced to Odoo when approved:

```python
from src.services.expense_service import ExpenseService
from pathlib import Path

# Initialize with Odoo config
service = ExpenseService(
    vault_path=Path("/vault"),
    odoo_url="https://odoo.example.com",
    odoo_api_key="your_api_key",
    odoo_database="odoo"
)

# Create and approve expense (auto-syncs to Odoo)
expense = service.create_expense_from_receipt(
    receipt_path="receipts/adobe_receipt.pdf",
    month="2026-03",
    auto_approve=True
)
```

### Manual Batch Sync

```python
# Sync all approved expenses for a month
results = service.sync_all_approved_expenses(month="2026-03")

print(f"Synced: {results['synced']}")
print(f"Failed: {results['failed']}")
print(f"Skipped: {results['skipped']}")
```

### Budget Monitoring

```python
# Check budget status from Odoo
budget_status = service.get_budget_status_from_odoo("2026-03")

# Check for budget warnings
warnings = service.check_budget_warnings("2026-03")

for warning in warnings:
    print(f"{warning['category']}: {warning['message']}")
    # Alerts automatically created in Needs_Action/
```

### Monthly Financial Reports

```bash
# Generate monthly report
python3 -m src.scripts.generate_monthly_report 2026-03

# Report saved to: Reports/Financial/2026-03_Financial_Report.md
```

Or via scheduler (automated monthly on 1st):

```yaml
# In Company_Handbook.md
scheduled_tasks:
  - task_id: monthly_financial_report
    task_name: Monthly Financial Report
    task_type: monthly_report
    schedule_pattern: "0 9 1 * *"  # 1st of month, 9 AM
    enabled: true
    output_path: Reports/Financial
```

## Category Mappings

The AI Employee categories map to Odoo account codes:

| AI Employee Category | Odoo Account | Code |
|---------------------|--------------|------|
| food, dining, restaurant | Meals & Entertainment | 600100 |
| transport, taxi, fuel | Transportation | 600200 |
| utilities, electricity, internet | Utilities | 600300 |
| software, subscription, saas | Software & Subscriptions | 600400 |
| office, supplies, equipment | Office Supplies | 600500 |
| marketing, advertising | Marketing & Advertising | 600600 |
| professional, consulting, legal | Professional Services | 600700 |
| training, education, courses | Training & Education | 600800 |
| travel, hotel, flight | Travel & Accommodation | 600900 |
| entertainment, team-building | Entertainment & Events | 601000 |
| health, medical, insurance | Health & Insurance | 601100 |
| other, miscellaneous | Miscellaneous | 600000 |

## Sync Event Logging

All Odoo sync events are logged to `Logs/odoo_sync.jsonl`:

```json
{
  "timestamp": "2026-03-12T14:30:00Z",
  "expense_id": "EXPENSE_2026_03_12_001",
  "status": "success",
  "details": {
    "odoo_id": 42,
    "account_code": "600400",
    "vendor": "Adobe Creative Cloud"
  }
}
```

## Backup & Recovery

### Automated Backups

Daily backups run at 2 AM (configured via cron):

```bash
/opt/ai-employee/deployment/scripts/backup-odoo.sh
```

Backups stored in `/opt/backups/odoo/` with 30-day retention:
- `odoo_backup_YYYYMMDD_HHMMSS.sql.gz` - Database dump
- `odoo_filestore_YYYYMMDD_HHMMSS.tar.gz` - Attachments

### Manual Backup

```bash
# Run backup script manually
sudo /opt/ai-employee/deployment/scripts/backup-odoo.sh

# Or via MCP tool
# Use odoo_backup_database tool
```

### Restore from Backup

```bash
# Stop Odoo
sudo systemctl stop odoo

# Restore database
gunzip < /opt/backups/odoo/odoo_backup_20260312_020000.sql.gz | \
  sudo -u postgres psql odoo

# Restore filestore
tar -xzf /opt/backups/odoo/odoo_filestore_20260312_020000.tar.gz \
  -C /opt/odoo/.local/share/Odoo/filestore/

# Start Odoo
sudo systemctl start odoo
```

## Monitoring

### Health Checks

```bash
# Check Odoo service status
sudo systemctl status odoo

# View Odoo logs
sudo journalctl -u odoo -f

# Check nginx status
sudo systemctl status nginx

# View nginx logs
sudo tail -f /var/log/nginx/odoo-access.log
sudo tail -f /var/log/nginx/odoo-error.log
```

### Access Odoo Web Interface

```bash
# Open browser to Odoo
https://odoo.yourdomain.com

# Default admin credentials set during installation
# Username: admin
# Password: (check /etc/odoo.conf: grep admin_passwd /etc/odoo.conf)
```

## Troubleshooting

### Sync Failures

Check sync log for errors:

```bash
cat /vault/Logs/odoo_sync.jsonl | grep failed
```

Common issues:
- **Authentication failed**: Check `ODOO_API_KEY` in `.env.cloud`
- **Network timeout**: Verify Odoo server is accessible
- **Account code not found**: Check category mappings in `config.json`

### Budget Warnings Not Creating Alerts

1. Verify Odoo connection:
   ```python
   service.get_budget_status_from_odoo("2026-03")
   ```

2. Check budget configuration in Odoo:
   - Accounting → Configuration → Budgets
   - Ensure budgets exist for current month

3. Verify category mappings match Odoo accounts

### Monthly Report Missing Data

1. Ensure expenses exist for the month:
   ```bash
   ls -la /vault/Expenses/2026-03/
   ```

2. Check Odoo connection and sync status:
   ```bash
   grep "2026-03" /vault/Logs/odoo_sync.jsonl
   ```

3. Run report manually with verbose logging:
   ```bash
   LOG_LEVEL=DEBUG python3 -m src.scripts.generate_monthly_report 2026-03
   ```

## Security

### Access Control

- Odoo admin password: Randomly generated during installation
- API keys: Stored in `.env.cloud` (never committed to git)
- Database credentials: Stored in `/etc/odoo.conf` (restricted permissions)
- SSL/TLS: Enforced via Let's Encrypt certificates

### Network Security

- Odoo listens on `127.0.0.1:8069` (localhost only)
- nginx reverse proxy handles external HTTPS traffic
- Firewall: Only ports 80 (HTTP redirect) and 443 (HTTPS) open

### Data Protection

- Daily encrypted backups
- 30-day backup retention
- Filestore backups include attachments
- Audit trail in `odoo_sync.jsonl`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Personal AI Employee                      │
│                                                               │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ Expense      │───>│ Odoo MCP       │                     │
│  │ Service      │    │ Server         │                     │
│  │              │<───│                │                     │
│  └──────────────┘    └────────────────┘                     │
│         │                     │                              │
│         │                     │ HTTPS/REST API              │
│         v                     v                              │
│  ┌──────────────────────────────────────┐                   │
│  │     Logs/odoo_sync.jsonl             │                   │
│  └──────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                                │
                                │ HTTPS (nginx reverse proxy)
                                v
┌─────────────────────────────────────────────────────────────┐
│                    Odoo Server (Cloud VM)                    │
│                                                               │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ nginx        │───>│ Odoo 17.0      │                     │
│  │ (reverse     │    │ (Python)       │                     │
│  │  proxy)      │<───│                │                     │
│  └──────────────┘    └────────────────┘                     │
│         │                     │                              │
│         v                     v                              │
│  ┌──────────────┐    ┌────────────────┐                     │
│  │ Let's        │    │ PostgreSQL     │                     │
│  │ Encrypt      │    │ Database       │                     │
│  │ SSL          │    │                │                     │
│  └──────────────┘    └────────────────┘                     │
│                              │                               │
│                              v                               │
│                      ┌────────────────┐                      │
│                      │ Daily Backups  │                      │
│                      │ (cron)         │                      │
│                      └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## References

- **Odoo Documentation**: https://www.odoo.com/documentation/17.0/
- **Odoo REST API**: https://www.odoo.com/documentation/17.0/developer/reference/backend/http.html
- **MCP Specification**: https://spec.modelcontextprotocol.io/
- **Platinum Tier Spec**: `specs/004-platinum-tier-upgrade/spec.md`

---

**Created**: 2026-03-12
**Part of**: Platinum Tier US5 - Odoo Integration
**Maintained by**: Personal AI Employee Team
