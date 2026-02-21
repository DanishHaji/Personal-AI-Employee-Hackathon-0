---
name: vault-manager
description: Manage Obsidian vault - read items, create plans, move files
arguments:
  - name: action
    description: Action to perform (read|plan|move)
    required: true
  - name: file_path
    description: Path to file to process (for read/plan actions)
    required: false
---

# Vault Manager Skill

This skill manages Obsidian vault operations for the AI Employee, including:
- Reading and analyzing items from /Needs_Action/
- Creating actionable plans in /Plans/
- Moving completed items to /Done/

## Usage

### Read Action
Read and analyze a file from /Needs_Action/:

```
Use vault-manager skill with action=read and file_path=/path/to/vault/Needs_Action/EMAIL_123.md
```

### Plan Action
Create a plan based on an Email or FileDrop entity:

```
Use vault-manager skill with action=plan and file_path=/path/to/vault/Needs_Action/EMAIL_123.md
```

### Move Action
Move a completed item to /Done/:

```
Use vault-manager skill with action=move and file_path=/path/to/vault/Needs_Action/EMAIL_123.md
```

## Implementation: Read Action (T036)

When `action=read`, parse and analyze the file:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.services.vault_service import VaultService

# Parse arguments
file_path = Path(arguments['file_path'])
vault_path = file_path.parents[1]  # Vault root is 2 levels up from Needs_Action/

# Read file with frontmatter
vault = VaultService(vault_path)
frontmatter, body = vault.read_markdown_with_frontmatter(file_path)

# Determine entity type
entity_type = frontmatter.get('type', 'unknown')

# Display parsed information
print(f"Entity Type: {entity_type}")
print(f"\nFrontmatter:")
for key, value in frontmatter.items():
    print(f"  {key}: {value}")

print(f"\nBody Content:")
print(body[:500])  # First 500 chars

# Return structured data for further processing
{
    "entity_type": entity_type,
    "frontmatter": frontmatter,
    "body": body,
    "file_path": str(file_path)
}
```

## Implementation: Plan Action (T037-T041)

When `action=plan`, create an ActionPlan based on the entity:

```python
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.cwd()))

from src.services.vault_service import VaultService
from src.models.action_plan import ActionPlan, Step, create_plan_filename, get_next_plan_id
from src.services.logger_service import AuditLogger

# Parse arguments
file_path = Path(arguments['file_path'])
vault_path = file_path.parents[1]

# Initialize services
vault = VaultService(vault_path)
logger = AuditLogger(vault_path)

# Read source entity
frontmatter, body = vault.read_markdown_with_frontmatter(file_path)
entity_type = frontmatter.get('type')

# Read Company_Handbook.md for context rules (T041)
handbook_path = vault_path / 'Company_Handbook.md'
handbook_rules = ""
if handbook_path.exists():
    _, handbook_rules = vault.read_markdown_with_frontmatter(handbook_path)

# Get existing plan IDs for sequential numbering (T040)
plan_files = vault.list_files('Plans', 'PLAN_*.md')
existing_ids = [f.stem.split('_')[0] + '_' + f.stem.split('_')[1] for f in plan_files]
plan_id = get_next_plan_id(existing_ids)

# Generate plan based on entity type (T037)
if entity_type == "email":
    # Email-based plan
    from_addr = frontmatter.get('from', 'unknown')
    subject = frontmatter.get('subject', 'No subject')
    priority = frontmatter.get('priority', 'medium')

    # Create objective (1-2 sentences)
    objective = f"Address email from {from_addr}: {subject}"

    # Create title (3-10 words)
    title_words = subject.split()[:6]  # Take first 6 words
    title = ' '.join(title_words) if title_words else "Email Response Plan"

    # Generate steps based on email content
    steps = []
    subject_lower = subject.lower()

    # Step 1: Always clarify (best practice from handbook)
    steps.append(Step(1, "Review email thoroughly and clarify objective"))

    # Content-specific steps
    if "invoice" in subject_lower or "payment" in subject_lower:
        steps.append(Step(2, f"Verify invoice details and amount"))
        steps.append(Step(3, "Check if payment exceeds $100 (requires approval)"))
        steps.append(Step(4, "Prepare invoice or payment confirmation"))
        steps.append(Step(5, "Get approval if needed, then send response"))
    elif "meeting" in subject_lower:
        steps.append(Step(2, "Check calendar for availability"))
        steps.append(Step(3, "Propose meeting time or confirm existing time"))
        steps.append(Step(4, "Send meeting confirmation"))
    elif "urgent" in subject_lower or priority == "high":
        steps.append(Step(2, "Identify urgent action required"))
        steps.append(Step(3, "Draft immediate response"))
        steps.append(Step(4, "Send response within 2 hours"))
    else:
        steps.append(Step(2, "Draft appropriate response"))
        steps.append(Step(3, "Review response for clarity and tone"))
        steps.append(Step(4, "Send response within 24 hours"))

    # Final step: Always verify completion
    final_step_num = len(steps) + 1
    steps.append(Step(final_step_num, "Verify task completion and move email to /Done/"))

    # Approval detection (T038)
    approval_required = False
    approval_context = []

    if "invoice" in subject_lower or "payment" in subject_lower:
        approval_required = True
        approval_context.append("payment request")

    if any(word in subject_lower for word in ["send email", "reply", "respond"]):
        # Check if it's a new contact (not in Company_Handbook)
        if from_addr not in handbook_rules:
            approval_required = True
            approval_context.append("email to new contact")

elif entity_type == "file_drop":
    # File-based plan
    original_name = frontmatter.get('original_name', 'unknown file')
    file_type = frontmatter.get('file_type', '')
    size = frontmatter.get('size', 0)

    objective = f"Process and review {original_name}"
    title = f"Process {original_name}"

    # Generate steps based on file type
    steps = []
    steps.append(Step(1, "Review file content thoroughly"))

    if file_type.lower() in ['.pdf', '.doc', '.docx']:
        steps.append(Step(2, "Extract key information and highlights"))
        steps.append(Step(3, "Summarize main points"))
        steps.append(Step(4, "File in appropriate folder or archive"))
    elif file_type.lower() in ['.xls', '.xlsx', '.csv']:
        steps.append(Step(2, "Analyze data and identify key insights"))
        steps.append(Step(3, "Update relevant records if needed"))
        steps.append(Step(4, "Archive processed data"))
    else:
        steps.append(Step(2, "Determine file purpose and next actions"))
        steps.append(Step(3, "Process or archive as appropriate"))

    steps.append(Step(len(steps) + 1, "Verify completion and move to /Done/"))

    # Approval detection
    approval_required = False
    approval_context = []

    if size > 50 * 1024 * 1024:  # > 50MB
        approval_required = True
        approval_context.append("large file (>50MB)")

else:
    # Unknown entity type
    objective = "Review and process unknown entity"
    title = "Process Unknown Entity"
    steps = [
        Step(1, "Identify entity type and purpose"),
        Step(2, "Determine appropriate action"),
        Step(3, "Execute action or request clarification"),
    ]
    approval_required = False
    approval_context = []

# Validate step count (3-7 steps required)
if len(steps) < 3:
    steps.append(Step(len(steps) + 1, "Request additional context from user"))
if len(steps) > 7:
    steps = steps[:7]  # Truncate to 7

# Create approval file if needed (T039)
approval_file_path = None
if approval_required:
    context_str = " and ".join(approval_context)
    approval_filename = f"APPROVAL_{plan_id.lower()}_{datetime.now().strftime('%Y%m%d')}.md"
    approval_file_path = f"/Pending_Approval/{approval_filename}"

    approval_content = f"""---
type: approval_request
plan_id: {plan_id}
context: {context_str}
created: {datetime.now().isoformat()}
status: pending
---

## Approval Required

**Plan**: {title}

**Context**: This plan involves {context_str}.

**Source**: {file_path.name}

## Actions Requiring Approval

{chr(10).join([f"- {step.description}" for step in steps if any(keyword in step.description.lower() for keyword in ["send", "payment", "delete", "post"])])}

## To Approve

1. Review the plan at `/Plans/{plan_id}_{title.lower().replace(' ', '-')}.md`
2. Verify the actions are appropriate
3. Move this file to `/Approved/` folder

## To Reject

1. Move this file to `/Done/` with note explaining why
2. Update the plan status to "rejected"

---

**This approval request was automatically generated based on security rules.**
"""

    vault.write_markdown(Path("Pending_Approval") / approval_filename, approval_content)
    print(f"✅ Created approval request: {approval_filename}")

# Create ActionPlan
plan = ActionPlan(
    plan_id=plan_id,
    title=title,
    source_type=entity_type,
    source_id=frontmatter.get('email_id', frontmatter.get('original_name', 'unknown')),
    created=datetime.now(),
    objective=objective,
    steps=steps,
    approval_required=approval_required,
    approval_file=approval_file_path,
    status="awaiting_approval" if approval_required else "draft"
)

# Validate plan
plan.validate()

# Generate markdown
plan_markdown = plan.to_markdown()

# Write plan file
plan_filename = create_plan_filename(plan_id, title)
plan_path = Path("Plans") / plan_filename
vault.write_markdown(plan_path, plan_markdown)

print(f"✅ Created plan: {plan_filename}")
print(f"  - Plan ID: {plan_id}")
print(f"  - Steps: {len(steps)}")
print(f"  - Approval required: {approval_required}")

# Log to audit
logger.log_plan_created(
    plan_id=plan_id,
    source_type=entity_type,
    source_id=frontmatter.get('email_id', frontmatter.get('original_name', 'unknown')),
    approval_required=approval_required,
    result="success"
)

# Return plan details
{
    "plan_id": plan_id,
    "filename": plan_filename,
    "steps_count": len(steps),
    "approval_required": approval_required,
    "status": plan.status
}
```

## Implementation: Move Action

When `action=move`, move file to /Done/:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.services.vault_service import VaultService

# Parse arguments
file_path = Path(arguments['file_path'])
vault_path = file_path.parents[1]

# Move file
vault = VaultService(vault_path)
new_path = vault.move_file(file_path, "Done")

print(f"✅ Moved to: {new_path}")
```

## Approval Detection Rules (T038)

Set `approval_required=true` if steps mention:
- **Email sends**: "send email", "reply", "respond" (to new contacts not in handbook)
- **Payments**: "payment", "invoice" (over $100)
- **Irreversible actions**: "delete", "remove"
- **Social media**: "post", "tweet", "share" (DM/reply)

## Step Count Validation (T037)

- **Minimum**: 3 steps
- **Maximum**: 7 steps
- **First step**: Should clarify objective/review content
- **Last step**: Should verify completion

If source is unclear, include "Request clarification from user" as a step.

## Company Handbook Integration (T041)

Always read `/Company_Handbook.md` before generating plans to incorporate:
- Email response guidelines
- Financial rules (payment thresholds)
- Priority classification
- Custom user rules

## Error Handling

- If source file malformed: Create plan with "Review malformed input" step
- If plan_id collision: Increment ID and retry
- If Company_Handbook.md missing: Use default rules from constitution
- Log all errors to audit log

## Success Criteria

- Plan files created in `/Plans/` folder
- 3-7 actionable steps included
- Approval files created when needed in `/Pending_Approval/`
- Sequential plan IDs (PLAN_001, PLAN_002, etc.)
- All actions logged to audit trail
