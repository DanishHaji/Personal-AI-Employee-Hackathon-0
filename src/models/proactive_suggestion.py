"""
ProactiveSuggestion Model for Personal AI Employee - Gold Tier

AI-initiated task suggestions based on patterns and context.

Entity Definition: specs/003-gold-tier-upgrade/data-model.md#proactive-suggestion
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Literal
from pathlib import Path

from src.models.base_model import SimpleEntity

logger = logging.getLogger(__name__)


# Type aliases for clarity
SuggestionCategory = Literal["follow_up", "reminder", "relationship_maintenance", "task_chain"]
Priority = Literal["high", "medium", "low"]
UserResponse = Literal["accepted", "rejected", "modified", "expired"]


@dataclass
class ProactiveSuggestion(SimpleEntity):
    """
    AI-initiated task suggestion based on patterns, context, and relationships.

    Features:
    - Proactive follow-up detection (unanswered emails, stale relationships)
    - Incomplete task chain identification (scheduled meeting but no agenda)
    - Recurring pattern reminders (monthly expense reports)
    - Confidence scoring for relevance
    - User feedback learning

    Storage: /Needs_Action/SUGGEST_{category}_{id}.md

    Example:
        suggestion = ProactiveSuggestion(
            suggestion_id="SUGGEST_followup_2026_02_27",
            category="follow_up",
            reason="No reply received to important email within 3 days",
            confidence_score=0.82,
            context="Email sent 2026-02-24 to john@example.com regarding Q2 project timeline",
            suggested_action="Send follow-up email to check status",
            related_entities=["EMAIL_abc123"],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            priority="high"
        )

        # Save to vault
        suggestion.save_to_file(
            "/vault/Needs_Action/SUGGEST_followup_2026_02_27.md",
            body="Draft follow-up email content here..."
        )
    """

    # Required fields
    suggestion_id: str
    category: SuggestionCategory
    reason: str
    confidence_score: float  # 0.0-1.0
    context: str
    suggested_action: str
    related_entities: List[str]
    created_at: datetime
    priority: Priority

    # Optional fields
    draft_content: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_response: Optional[UserResponse] = None
    user_feedback: Optional[str] = None

    # Type identifier
    type: str = field(default="proactive_suggestion", init=False)

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_confidence_score()
        self._validate_expiration()
        self._validate_category()
        self._validate_priority()

        # Set default expiration if not provided (7 days)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=7)

    def _validate_confidence_score(self):
        """Ensure confidence score is in valid range."""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")

    def _validate_expiration(self):
        """Ensure expiration date is after creation date."""
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError(f"expires_at ({self.expires_at}) must be after created_at ({self.created_at})")

    def _validate_category(self):
        """Validate category is one of allowed values."""
        valid_categories = ["follow_up", "reminder", "relationship_maintenance", "task_chain"]
        if self.category not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}, got '{self.category}'")

    def _validate_priority(self):
        """Validate priority is one of allowed values."""
        valid_priorities = ["high", "medium", "low"]
        if self.priority not in valid_priorities:
            raise ValueError(f"priority must be one of {valid_priorities}, got '{self.priority}'")

    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def mark_accepted(self, feedback: Optional[str] = None):
        """Mark suggestion as accepted by user."""
        self.user_response = "accepted"
        if feedback:
            self.user_feedback = feedback
        logger.info(f"Suggestion {self.suggestion_id} marked as accepted")

    def mark_rejected(self, feedback: Optional[str] = None):
        """
        Mark suggestion as rejected by user.

        Rejection feedback is used to decrease confidence for similar future suggestions.
        """
        self.user_response = "rejected"
        if feedback:
            self.user_feedback = feedback
        logger.info(f"Suggestion {self.suggestion_id} marked as rejected")

    def mark_modified(self, feedback: Optional[str] = None):
        """Mark suggestion as modified by user before acceptance."""
        self.user_response = "modified"
        if feedback:
            self.user_feedback = feedback
        logger.info(f"Suggestion {self.suggestion_id} marked as modified")

    def mark_expired(self):
        """Mark suggestion as expired (no action taken before deadline)."""
        self.user_response = "expired"
        logger.info(f"Suggestion {self.suggestion_id} marked as expired")

    def get_filename(self) -> str:
        """
        Generate standard filename for suggestion.

        Returns:
            str: Filename in format "SUGGEST_{category}_{id}.md"
        """
        return f"{self.suggestion_id}.md"

    def to_markdown_body(self) -> str:
        """
        Generate markdown body content for suggestion file.

        Returns:
            str: Formatted markdown body with suggestion details
        """
        # Format draft content if present
        draft_section = ""
        if self.draft_content:
            draft_section = f"""
**Draft Message**:
```
{self.draft_content}
```
"""

        # Format expiration
        expiry_str = "No expiration" if self.expires_at is None else self.expires_at.strftime("%Y-%m-%d %H:%M")

        # Format related entities
        entities_list = "\n".join([f"- {entity}" for entity in self.related_entities])

        body = f"""# Proactive Suggestion: {self.category.replace('_', ' ').title()}

**Reason**: {self.reason}

**Suggested Action**: {self.suggested_action}
{draft_section}
**Context**: {self.context}

**Related Entities**:
{entities_list}

**Confidence**: {self.confidence_score:.0%}
**Priority**: {self.priority.upper()}
**Expires**: {expiry_str}

---

**Actions**:
- ✅ **Accept**: Move to /Approved/ to execute this suggestion
- ❌ **Reject**: Move to /Done/ if not needed
- ✏️ **Modify**: Edit draft content before approving
"""
        return body.strip()

    @classmethod
    def generate_id(cls, category: str, date: Optional[datetime] = None) -> str:
        """
        Generate unique suggestion ID.

        Args:
            category: Suggestion category
            date: Creation date (default: now)

        Returns:
            str: Unique ID in format "SUGGEST_{category}_{date}"
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y_%m_%d")
        return f"SUGGEST_{category}_{date_str}"

    @classmethod
    def create_follow_up(
        cls,
        email_id: str,
        contact_email: str,
        original_subject: str,
        days_since_sent: int,
        draft_message: Optional[str] = None
    ) -> "ProactiveSuggestion":
        """
        Factory method to create a follow-up email suggestion.

        Args:
            email_id: ID of original email
            contact_email: Email address of recipient
            original_subject: Subject of original email
            days_since_sent: Number of days since original email was sent
            draft_message: Pre-drafted follow-up message

        Returns:
            ProactiveSuggestion: Follow-up suggestion instance
        """
        now = datetime.now()
        suggestion_id = cls.generate_id("followup", now)

        # Calculate priority based on how long it's been
        if days_since_sent >= 5:
            priority = "high"
        elif days_since_sent >= 3:
            priority = "medium"
        else:
            priority = "low"

        # Calculate confidence (higher if more days passed)
        confidence = min(0.95, 0.60 + (days_since_sent * 0.10))

        return cls(
            suggestion_id=suggestion_id,
            category="follow_up",
            reason=f"No reply received to important email within {days_since_sent} days",
            confidence_score=confidence,
            context=f"Email sent {days_since_sent} days ago to {contact_email} regarding '{original_subject}'",
            suggested_action="Send follow-up email to check status",
            draft_content=draft_message,
            related_entities=[email_id],
            created_at=now,
            expires_at=now + timedelta(days=7),
            priority=priority
        )

    @classmethod
    def create_reminder(
        cls,
        task_name: str,
        due_date: datetime,
        related_entities: List[str],
        context: str
    ) -> "ProactiveSuggestion":
        """
        Factory method to create a recurring task reminder.

        Args:
            task_name: Name of the recurring task
            due_date: When task is due
            related_entities: Related entity IDs
            context: Additional context about the task

        Returns:
            ProactiveSuggestion: Reminder suggestion instance
        """
        now = datetime.now()
        suggestion_id = cls.generate_id("reminder", now)

        # Calculate days until due
        days_until_due = (due_date - now).days

        # Priority based on urgency
        if days_until_due <= 1:
            priority = "high"
        elif days_until_due <= 3:
            priority = "medium"
        else:
            priority = "low"

        return cls(
            suggestion_id=suggestion_id,
            category="reminder",
            reason=f"Recurring task '{task_name}' due in {days_until_due} days",
            confidence_score=0.90,
            context=context,
            suggested_action=f"Complete '{task_name}' before {due_date.strftime('%Y-%m-%d')}",
            related_entities=related_entities,
            created_at=now,
            expires_at=due_date,
            priority=priority
        )

    @classmethod
    def create_relationship_maintenance(
        cls,
        contact_id: str,
        contact_name: str,
        days_since_contact: int,
        last_conversation_topic: Optional[str] = None
    ) -> "ProactiveSuggestion":
        """
        Factory method to create a relationship maintenance suggestion.

        Args:
            contact_id: Contact entity ID
            contact_name: Name of contact
            days_since_contact: Days since last interaction
            last_conversation_topic: Topic of last conversation

        Returns:
            ProactiveSuggestion: Relationship maintenance suggestion instance
        """
        now = datetime.now()
        suggestion_id = cls.generate_id("relationship", now)

        # Context includes last conversation topic if available
        context_parts = [f"No contact with {contact_name} in {days_since_contact} days"]
        if last_conversation_topic:
            context_parts.append(f"Last conversation: {last_conversation_topic}")
        context = ". ".join(context_parts)

        return cls(
            suggestion_id=suggestion_id,
            category="relationship_maintenance",
            reason=f"VIP contact {contact_name} hasn't been contacted in {days_since_contact} days",
            confidence_score=0.85,
            context=context,
            suggested_action=f"Send check-in message to {contact_name}",
            related_entities=[contact_id],
            created_at=now,
            expires_at=now + timedelta(days=7),
            priority="high" if days_since_contact >= 45 else "medium"
        )

    @classmethod
    def create_task_chain(
        cls,
        incomplete_task: str,
        blocking_task: str,
        related_entities: List[str],
        context: str
    ) -> "ProactiveSuggestion":
        """
        Factory method to create an incomplete task chain suggestion.

        Args:
            incomplete_task: What task is incomplete
            blocking_task: What task is blocked
            related_entities: Related entity IDs
            context: Additional context

        Returns:
            ProactiveSuggestion: Task chain suggestion instance
        """
        now = datetime.now()
        suggestion_id = cls.generate_id("taskchain", now)

        return cls(
            suggestion_id=suggestion_id,
            category="task_chain",
            reason=f"Incomplete task chain detected: {incomplete_task}",
            confidence_score=0.78,
            context=context,
            suggested_action=f"Complete '{incomplete_task}' to unblock '{blocking_task}'",
            related_entities=related_entities,
            created_at=now,
            expires_at=now + timedelta(days=3),
            priority="medium"
        )


# Helper functions

def load_suggestions_from_directory(directory: Path, decrypt: bool = False) -> List[ProactiveSuggestion]:
    """
    Load all suggestion files from a directory.

    Args:
        directory: Path to directory containing suggestion files
        decrypt: Whether to decrypt encrypted fields

    Returns:
        List[ProactiveSuggestion]: List of suggestion instances
    """
    suggestions = []

    if not directory.exists():
        logger.warning(f"Suggestions directory does not exist: {directory}")
        return suggestions

    for file_path in directory.glob("SUGGEST_*.md"):
        try:
            suggestion, _ = ProactiveSuggestion.load_from_file(file_path, decrypt=decrypt)
            suggestions.append(suggestion)
        except Exception as e:
            logger.error(f"Failed to load suggestion from {file_path}: {e}")

    return suggestions


def get_pending_suggestions(directory: Path) -> List[ProactiveSuggestion]:
    """
    Get all pending suggestions (not responded to yet).

    Args:
        directory: Path to directory containing suggestion files

    Returns:
        List[ProactiveSuggestion]: List of pending suggestions
    """
    all_suggestions = load_suggestions_from_directory(directory)

    pending = [
        s for s in all_suggestions
        if s.user_response is None and not s.is_expired()
    ]

    # Sort by priority (high first) then confidence score
    priority_order = {"high": 0, "medium": 1, "low": 2}
    pending.sort(key=lambda s: (priority_order[s.priority], -s.confidence_score))

    return pending


def expire_old_suggestions(directory: Path) -> int:
    """
    Mark expired suggestions and move them to Done.

    Args:
        directory: Path to directory containing suggestion files

    Returns:
        int: Number of suggestions expired
    """
    suggestions = load_suggestions_from_directory(directory)
    expired_count = 0

    for suggestion in suggestions:
        if suggestion.is_expired() and suggestion.user_response is None:
            suggestion.mark_expired()

            # Save updated suggestion
            file_path = directory / suggestion.get_filename()
            suggestion.save_to_file(file_path, body=suggestion.to_markdown_body())

            expired_count += 1
            logger.info(f"Expired suggestion: {suggestion.suggestion_id}")

    return expired_count
