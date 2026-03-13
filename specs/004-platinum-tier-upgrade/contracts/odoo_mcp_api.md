# Odoo MCP Server API Contract

**Feature**: 004-platinum-tier-upgrade
**Component**: Odoo Community Integration via MCP Server
**Version**: 1.0.0

## Overview

Defines the MCP (Model Context Protocol) server API for Odoo Community accounting system integration.

**Implementation**: Python MCP server (`mcp-servers/odoo/server.py`)
**Protocol**: MCP (JSON-RPC over stdio)
**Odoo API**: JSON-RPC API (Bearer token authentication)

---

## MCP Tools

### `odoo_create_expense`

Creates an expense entry in Odoo accounting system.

**Parameters**:
```json
{
  "expense_id": "EXPENSE_002_AWS_20260304",
  "amount": 289.50,
  "category": "cloud_services",
  "vendor": "Amazon Web Services",
  "date": "2026-03-04",
  "description": "AWS Invoice - March 2026",
  "receipt_path": "vault/Expenses/receipts/aws_march_2026.pdf"
}
```

**Returns**:
```json
{
  "success": true,
  "odoo_entry_id": 1247,
  "message": "Expense synced to Odoo successfully"
}
```

**Behavior**:
1. Authenticates with Odoo via Bearer token
2. Looks up or creates vendor (partner)
3. Looks up account based on category mapping
4. Creates `account.move.line` entry
5. Returns Odoo entry ID

**Error Responses**:
```json
{
  "success": false,
  "error": "Odoo authentication failed",
  "code": "AUTH_FAILED"
}
```

---

### `odoo_get_budget_status`

Retrieves current budget status for a category.

**Parameters**:
```json
{
  "category": "cloud_services",
  "month": "2026-03"
}
```

**Returns**:
```json
{
  "category": "cloud_services",
  "month": "2026-03",
  "budget_limit": 1000.00,
  "spent": 289.50,
  "remaining": 710.50,
  "percent_used": 28.95,
  "alert_threshold": 800.00,
  "status": "ok"
}
```

**Status Values**:
- `"ok"`: Under threshold
- `"warning"`: Above threshold but under limit
- `"exceeded"`: Over budget limit

**Behavior**:
1. Queries Odoo for budget configuration
2. Sums all expenses in category for month
3. Calculates remaining budget
4. Determines alert status

---

### `odoo_generate_financial_report`

Generates monthly financial summary report.

**Parameters**:
```json
{
  "report_type": "monthly_summary",
  "month": "2026-03"
}
```

**Returns**:
```json
{
  "report_id": "REPORT_2026-03",
  "month": "2026-03",
  "total_expenses": 1847.32,
  "total_income": 0.00,
  "categories": {
    "cloud_services": 289.50,
    "software": 60.98,
    "office_supplies": 147.84,
    "other": 1349.00
  },
  "budget_compliance": {
    "within_budget": 3,
    "over_budget": 0,
    "warnings": 1
  },
  "top_vendors": [
    {"name": "Amazon Web Services", "amount": 289.50},
    {"name": "Adobe Inc", "amount": 45.99},
    {"name": "Zoom Video Communications", "amount": 14.99}
  ]
}
```

**Behavior**:
1. Queries all transactions for month
2. Groups by category and vendor
3. Calculates totals and summaries
4. Generates formatted report

---

### `odoo_sync_all_expenses`

Batch syncs all unsynced expenses to Odoo.

**Parameters**:
```json
{
  "since_date": "2026-03-01"
}
```

**Returns**:
```json
{
  "synced_count": 12,
  "failed_count": 1,
  "synced_ids": ["EXPENSE_001", "EXPENSE_002", ...],
  "failed_ids": ["EXPENSE_013"],
  "errors": [
    {"expense_id": "EXPENSE_013", "error": "Vendor not found"}
  ]
}
```

**Behavior**:
1. Scans `vault/Expenses/` for unsynced entries
2. Filters by date (`since_date`)
3. Syncs each expense via `odoo_create_expense`
4. Returns summary with successes and failures

---

### `odoo_backup_database`

Triggers Odoo database backup to cloud storage.

**Parameters**:
```json
{
  "backup_type": "full",
  "storage_provider": "s3",
  "retention_days": 30
}
```

**Returns**:
```json
{
  "success": true,
  "backup_id": "backup_2026-03-04_153000",
  "size_mb": 124.7,
  "location": "s3://backups/odoo/backup_2026-03-04_153000.tar.gz"
}
```

**Behavior**:
1. Calls Odoo database export API
2. Compresses database dump (tar.gz)
3. Uploads to configured cloud storage (S3/Backblaze/etc.)
4. Logs backup metadata

---

## Odoo JSON-RPC API Integration

### Authentication

**Endpoint**: `https://odoo.cloud.example.com/api/2/token`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "db": "odoo_production",
    "login": "admin",
    "password": "secure_password"
  },
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "access_token": "eyJhbGciOiJIUzI1...",
    "expires_in": 3600
  },
  "id": 1
}
```

**Token Storage**:
- Stored in `vault/.odoo_token` (local-only, not synced)
- Auto-refreshed 5 minutes before expiry

---

### Create Expense Entry

**Endpoint**: `https://odoo.cloud.example.com/api/2/account.move.line`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "create",
  "params": {
    "model": "account.move.line",
    "values": {
      "name": "AWS Invoice - March 2026",
      "account_id": 42,
      "debit": 289.50,
      "credit": 0.0,
      "date": "2026-03-04",
      "partner_id": 89,
      "analytic_account_id": 15,
      "ref": "EXPENSE_002_AWS_20260304"
    }
  },
  "id": 2
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": 1247,
  "id": 2
}
```

---

### Query Budget Status

**Endpoint**: `https://odoo.cloud.example.com/api/2/account.move.line`

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "search_read",
  "params": {
    "model": "account.move.line",
    "domain": [
      ["analytic_account_id", "=", 15],
      ["date", ">=", "2026-03-01"],
      ["date", "<=", "2026-03-31"]
    ],
    "fields": ["debit", "date"]
  },
  "id": 3
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": [
    {"debit": 289.50, "date": "2026-03-04"},
    {"debit": 45.99, "date": "2026-03-03"}
  ],
  "id": 3
}
```

---

## Category Mapping

**Expense Category → Odoo Account**:

| AI Employee Category | Odoo Account ID | Odoo Account Name |
|----------------------|-----------------|-------------------|
| `cloud_services` | 15 | Cloud & Hosting |
| `software` | 16 | Software Licenses |
| `office_supplies` | 17 | Office Expenses |
| `travel` | 18 | Travel & Accommodation |
| `meals` | 19 | Meals & Entertainment |
| `other` | 20 | Miscellaneous Expenses |

**Configured in**: `mcp-servers/odoo/config.json`

---

## MCP Server Configuration

**File**: `mcp-servers/odoo/config.json`

```json
{
  "odoo_url": "https://odoo.cloud.example.com",
  "odoo_database": "odoo_production",
  "odoo_username": "admin",
  "odoo_token_file": "vault/.odoo_token",
  "category_mapping": {
    "cloud_services": 15,
    "software": 16,
    "office_supplies": 17,
    "travel": 18,
    "meals": 19,
    "other": 20
  },
  "vendor_cache_ttl_hours": 24,
  "budget_alert_threshold": 0.80
}
```

**Environment Variables**:
```bash
ODOO_URL=https://odoo.cloud.example.com
ODOO_DATABASE=odoo_production
ODOO_USERNAME=admin
ODOO_PASSWORD=secure_password  # Local-only, not synced
```

---

## Deployment

### Odoo Community Installation (Cloud VM)

```bash
# Install Odoo Community 18.0 (latest 2026)
sudo apt update
sudo apt install postgresql-14
sudo apt install python3-pip python3-dev libxml2-dev libxslt1-dev \
                 libldap2-dev libsasl2-dev libjpeg-dev zlib1g-dev

# Create Odoo user
sudo useradd -m -d /opt/odoo -U -r -s /bin/bash odoo

# Install Odoo from source
sudo su - odoo
git clone https://github.com/odoo/odoo.git --depth 1 --branch 18.0
cd odoo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Odoo
cp debian/odoo.conf /etc/odoo.conf
# Edit /etc/odoo.conf with db credentials

# Setup systemd service
sudo systemctl enable odoo.service
sudo systemctl start odoo.service
```

### HTTPS Setup (Let's Encrypt)

```bash
# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/odoo

# Obtain SSL certificate
sudo certbot --nginx -d odoo.cloud.example.com
```

### MCP Server Deployment

```bash
# Install MCP server
cd mcp-servers/odoo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start MCP server
python server.py
```

---

## Security

1. **Token-Based Auth**: Bearer tokens (not password in every request)
2. **HTTPS Only**: All communication encrypted
3. **Token Storage**: `.odoo_token` excluded from cloud sync (local-only)
4. **Password Security**: Odoo password stored in local `.env` only
5. **API Rate Limiting**: Max 100 requests/minute per token

---

## Error Handling

### Authentication Failure

**Scenario**: Odoo password incorrect

**Response**:
```json
{
  "success": false,
  "error": "Authentication failed: Invalid credentials",
  "code": "AUTH_FAILED"
}
```

**Retry**: None (manual intervention required)

### Vendor Not Found

**Scenario**: Expense vendor doesn't exist in Odoo

**Behavior**:
1. Auto-creates vendor in Odoo
2. Retries expense creation
3. Success on retry

### Network Timeout

**Scenario**: Odoo server unreachable

**Response**:
```json
{
  "success": false,
  "error": "Network timeout: Odoo server unreachable",
  "code": "NETWORK_ERROR"
}
```

**Retry**: Exponential backoff (1s, 2s, 4s, 8s)

---

## Testing

### Unit Tests

```python
def test_create_expense_success(mock_odoo_api):
    result = odoo_mcp.create_expense(
        expense_id="EXPENSE_TEST",
        amount=100.00,
        category="software",
        vendor="Test Vendor",
        date="2026-03-04"
    )
    assert result["success"] == True
    assert "odoo_entry_id" in result

def test_budget_status():
    status = odoo_mcp.get_budget_status(
        category="cloud_services",
        month="2026-03"
    )
    assert status["status"] in ["ok", "warning", "exceeded"]
```

### Integration Tests

- Real Odoo API calls (test database)
- Expense creation and retrieval
- Budget calculation accuracy
- Vendor auto-creation

---

## Performance

**Create Expense**: 200-500ms (network latency)
**Get Budget Status**: 100-300ms
**Generate Report**: 500-1000ms (complex query)
**Batch Sync (10 expenses)**: 3-5 seconds

---

## Monitoring

**Odoo Sync Log** (`vault/Logs/odoo_sync.jsonl`):

```jsonl
{"sync_id": "ODOO_SYNC_20260304_153500", "expense_id": "EXPENSE_002", "status": "synced", "odoo_entry_id": 1247, "duration_ms": 347}
{"sync_id": "ODOO_SYNC_20260304_153510", "expense_id": "EXPENSE_003", "status": "failed", "error": "Network timeout", "duration_ms": 5000}
```

---

*Contract complete. Ready for implementation in `/sp.tasks`.*
