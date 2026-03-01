# CRM Manager Agent Skill

**Skill Name**: crm-manager
**Tier**: Gold Tier - US7
**Description**: Automated contact relationship management and tracking

## Purpose

The CRM Manager enables automated contact tracking, relationship maintenance, and follow-up management across all interactions (email, meetings, WhatsApp).

## Key Features

1. **Auto-Creation**: Contacts created automatically from email/meeting interactions
2. **Deduplication**: Fuzzy matching prevents duplicate contacts
3. **Relationship Scoring**: Dynamic strength calculation (interactions × 10 - days_since_contact)
4. **VIP Management**: Auto-promotion and special handling for key contacts
5. **Stale Detection**: Identifies relationships needing attention (VIP: 30+ days, Regular: 60+ days)
6. **Follow-up Suggestions**: Proactive reminders for relationship maintenance
7. **Encryption**: VIP contact data encrypted for security

## Usage

### Create/Update Contact from Email

```python
from src.services.contact_service import ContactService

service = ContactService(vault_path="/path/to/vault")

contact = service.create_or_update_from_email(
    name="John Smith",
    email="john@example.com",
    context="Q2 project discussion"
)
```

### Find Stale Relationships

```python
stale_vips = service.find_stale_relationships(vip_only=True)
print(f"Found {len(stale_vips)} VIP contacts needing follow-up")
```

### CRM Monitoring (Daily)

```python
from src.watchers.crm_watcher import CRMWatcher

watcher = CRMWatcher(vault_path="/path/to/vault", run_hour=9)
watcher.start()  # Runs daily at 9 AM
```

## Configuration

- **VIP Threshold**: 30 days (configurable)
- **Regular Threshold**: 60 days (configurable)
- **Auto-Promotion**: Contacts with strength >200 promoted to VIP
- **Max Suggestions**: 5 follow-ups per day

## File Structure

**Contact Profiles**: `/Contacts/CONTACT_{name}.md`

## Success Metrics

- ✅ **SC-019**: All interactions captured within 5 minutes
- ✅ **SC-020**: Stale relationships detected within 24 hours
- ✅ **SC-021**: Contact lookup <2 seconds

---

**Status**: ✅ Implemented (MVP)
**Last Updated**: 2026-03-02
