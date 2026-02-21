"""
Email Entity Model for Personal AI Employee - Bronze Tier MVP

Represents incoming Gmail messages detected by the Gmail Watcher.
Implements Entity 1 from data-model.md

Attributes:
    type: Entity type identifier (always "email")
    email_id: Gmail message ID (unique)
    from_addr: Sender email address
    subject: Email subject line
    received: Timestamp when email was received (ISO 8601)
    priority: Priority level ("high" or "medium")
    status: Processing status ("pending", "processing", "done")
    snippet: Email body preview (first 200 characters)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import yaml


@dataclass
class Email:
    """Email entity with YAML frontmatter serialization."""

    # Required attributes
    email_id: str
    from_addr: str
    subject: str
    received: datetime
    priority: Literal["high", "medium"]
    status: Literal["pending", "processing", "done"] = "pending"
    snippet: str = ""

    # Type identifier (constant)
    type: str = field(default="email", init=False)

    def to_frontmatter(self) -> dict:
        """
        Convert Email to YAML frontmatter dictionary.

        Returns:
            dict: Frontmatter data ready for YAML serialization
        """
        return {
            "type": self.type,
            "email_id": self.email_id,
            "from": self.from_addr,
            "subject": self.subject,
            "received": self.received.isoformat(),
            "priority": self.priority,
            "status": self.status,
        }

    @classmethod
    def from_frontmatter(cls, frontmatter: dict) -> "Email":
        """
        Create Email instance from YAML frontmatter dictionary.

        Args:
            frontmatter: Dictionary containing email metadata

        Returns:
            Email: Email instance
        """
        return cls(
            email_id=frontmatter["email_id"],
            from_addr=frontmatter["from"],
            subject=frontmatter["subject"],
            received=datetime.fromisoformat(frontmatter["received"]),
            priority=frontmatter["priority"],
            status=frontmatter.get("status", "pending"),
            snippet="",  # Snippet stored in body, not frontmatter
        )

    def to_markdown(self) -> str:
        """
        Generate complete Markdown file content with frontmatter and body.

        Format matches Contract 1 from contracts/file-interfaces.md:
        ---
        [YAML frontmatter]
        ---

        ## Email Content

        [snippet]

        ## Suggested Actions

        - [ ] [action 1]
        - [ ] [action 2]

        Returns:
            str: Complete markdown file content
        """
        frontmatter_yaml = yaml.dump(
            self.to_frontmatter(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Generate suggested actions based on email content
        actions = self._generate_suggested_actions()

        markdown_content = f"""---
{frontmatter_yaml.strip()}
---

## Email Content

{self.snippet}

## Suggested Actions

{actions}
"""
        return markdown_content

    def _generate_suggested_actions(self) -> str:
        """
        Generate suggested action checkboxes based on email content.

        Returns:
            str: Checkbox list of suggested actions
        """
        # Basic action suggestions (can be enhanced with AI in Silver tier)
        actions = []

        # Common actions based on subject/priority
        if self.priority == "high":
            actions.append("- [ ] Review email immediately")

        # Keyword-based suggestions
        subject_lower = self.subject.lower()
        if "invoice" in subject_lower or "payment" in subject_lower:
            actions.append("- [ ] Review invoice details")
            actions.append("- [ ] Verify payment amount")
            actions.append("- [ ] Get approval if over $100")
        elif "meeting" in subject_lower:
            actions.append("- [ ] Check calendar availability")
            actions.append("- [ ] Confirm or propose alternative time")
        elif "urgent" in subject_lower or "asap" in subject_lower:
            actions.append("- [ ] Respond within 2 hours")
        else:
            actions.append("- [ ] Read email thoroughly")
            actions.append("- [ ] Draft response if needed")

        actions.append("- [ ] Move to /Done/ when complete")

        return "\n".join(actions)

    def validate(self) -> bool:
        """
        Validate email attributes according to data-model.md rules.

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        # Validate email_id (alphanumeric from Gmail API)
        if not self.email_id or not isinstance(self.email_id, str):
            raise ValueError("email_id must be a non-empty string")

        # Validate from_addr (basic email format check)
        if "@" not in self.from_addr:
            raise ValueError(f"Invalid email format: {self.from_addr}")

        # Validate subject (max 255 chars from data-model.md)
        if len(self.subject) > 255:
            raise ValueError(f"Subject exceeds 255 characters: {len(self.subject)}")

        # Validate snippet (max 200 chars from data-model.md)
        if len(self.snippet) > 200:
            raise ValueError(f"Snippet exceeds 200 characters: {len(self.snippet)}")

        # Validate priority
        if self.priority not in ["high", "medium"]:
            raise ValueError(f"Invalid priority: {self.priority}")

        # Validate status
        if self.status not in ["pending", "processing", "done"]:
            raise ValueError(f"Invalid status: {self.status}")

        return True


def create_email_filename(email_id: str) -> str:
    """
    Generate standardized filename for Email entity.

    Format: EMAIL_{email_id}.md

    Args:
        email_id: Gmail message ID

    Returns:
        str: Filename for email markdown file
    """
    return f"EMAIL_{email_id}.md"
