"""
TrustRule Entity Model for Personal AI Employee - Gold Tier US1

Represents configurable rules for auto-approval of actions without HITL review.
Implements Trust Framework from data-model.md

Attributes:
    rule_id: Unique identifier (RULE_email_known_contacts, etc.)
    rule_name: Human-readable name
    action_type: Type of action (email_send, social_post, calendar_create, etc.)
    trust_level: 0=Always approve, 1=Auto-approve, 2=Auto+notify, 3=Silent auto
    contact_filter: Allowed contacts (emails, phone numbers, or group names)
    content_pattern: Regex pattern for content matching
    time_pattern: Time-based filter (e.g., "weekdays 9am-5pm")
    max_value: Maximum financial amount for auto-approval
    created_at: Rule creation timestamp
    created_by: Always "user" (human-created rules only)
    last_used: Last time rule triggered auto-approval
    usage_count: Number of times rule has auto-approved
    effectiveness_score: Approval accuracy (0.0-1.0)
    enabled: Whether rule is active

Validation:
    - JSON Schema validation against contracts/trust-rule-schema.json
    - rule_id format: RULE_{lowercase_description}
    - trust_level: 0-3 only
    - effectiveness_score: 0.0-1.0
    - Auto-disable if effectiveness_score < 0.80
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Literal
from pathlib import Path

from src.models.base_model import BaseModel


@dataclass
class TrustRule(BaseModel):
    """TrustRule entity with YAML frontmatter serialization and JSON Schema validation."""

    # Required attributes
    rule_id: str
    rule_name: str
    action_type: Literal[
        "email_send",
        "social_post",
        "calendar_create",
        "expense_record",
        "document_generate",
        "whatsapp_send",
        "task_complete"
    ]
    trust_level: Literal[0, 1, 2, 3]
    created_at: datetime
    created_by: Literal["user"]
    usage_count: int = 0
    effectiveness_score: float = 1.0
    enabled: bool = True

    # Optional filters
    contact_filter: Optional[List[str]] = None
    content_pattern: Optional[str] = None
    time_pattern: Optional[str] = None
    max_value: Optional[float] = None
    last_used: Optional[datetime] = None

    # Type identifier
    type: str = field(default="trust_rule", init=False)

    # Encryption not needed for trust rules (configuration data, not sensitive)
    ENCRYPTED_FIELDS: List[str] = field(default_factory=list, init=False)

    def get_schema_name(self) -> str:
        """Return JSON Schema filename for validation."""
        return "trust-rule-schema.json"

    def validate(self) -> bool:
        """
        Validate TrustRule attributes.

        Returns:
            bool: True if valid

        Raises:
            ValueError: If validation fails
        """
        # First validate against JSON Schema
        super().validate()

        # Additional business logic validations

        # Validate rule_id format
        if not self.rule_id.startswith("RULE_"):
            raise ValueError(f"rule_id must start with 'RULE_': {self.rule_id}")

        # Validate rule_id is lowercase after prefix
        rule_slug = self.rule_id[5:]  # Remove "RULE_" prefix
        if rule_slug != rule_slug.lower():
            raise ValueError(f"rule_id must be lowercase after 'RULE_': {self.rule_id}")

        # Validate trust_level range
        if self.trust_level not in [0, 1, 2, 3]:
            raise ValueError(f"trust_level must be 0-3: {self.trust_level}")

        # Validate effectiveness_score range
        if not (0.0 <= self.effectiveness_score <= 1.0):
            raise ValueError(
                f"effectiveness_score must be 0.0-1.0: {self.effectiveness_score}"
            )

        # Validate usage_count is non-negative
        if self.usage_count < 0:
            raise ValueError(f"usage_count must be >= 0: {self.usage_count}")

        # Validate max_value is non-negative if provided
        if self.max_value is not None and self.max_value < 0:
            raise ValueError(f"max_value must be >= 0: {self.max_value}")

        # Validate content_pattern is valid regex if provided
        if self.content_pattern is not None:
            try:
                import re
                re.compile(self.content_pattern)
            except re.error as e:
                raise ValueError(f"Invalid content_pattern regex: {e}")

        return True

    def should_auto_disable(self) -> bool:
        """
        Check if rule should be auto-disabled due to low effectiveness.

        Returns:
            bool: True if effectiveness_score < 0.80
        """
        return self.effectiveness_score < 0.80

    def update_effectiveness(self, user_would_approve: bool):
        """
        Update effectiveness score based on user feedback.

        Uses exponential moving average to weight recent feedback more heavily.

        Args:
            user_would_approve: Whether user would have approved this action
        """
        # Weight: 0.8 for existing score, 0.2 for new feedback
        weight = 0.8
        new_score = 1.0 if user_would_approve else 0.0
        self.effectiveness_score = (weight * self.effectiveness_score) + ((1 - weight) * new_score)

        # Auto-disable if effectiveness drops below threshold
        if self.should_auto_disable():
            self.enabled = False

    def record_usage(self):
        """Record that this rule was used for auto-approval."""
        self.usage_count += 1
        self.last_used = datetime.utcnow()

    def matches_contact(self, contact: str) -> bool:
        """
        Check if contact matches contact_filter.

        Args:
            contact: Email address or phone number

        Returns:
            bool: True if contact matches filter (or no filter set)
        """
        # No filter means match all contacts
        if not self.contact_filter:
            return True

        # Check each filter pattern
        for filter_pattern in self.contact_filter:
            # Domain match (e.g., "@example.com")
            if filter_pattern.startswith("@") and contact.endswith(filter_pattern):
                return True

            # Exact match
            if filter_pattern == contact:
                return True

            # Group name match (handled by caller, placeholder for now)
            # TODO: Implement group name resolution in TrustEvaluator

        return False

    def matches_content(self, content: str) -> bool:
        """
        Check if content matches content_pattern regex.

        Args:
            content: Content to match against

        Returns:
            bool: True if content matches pattern (or no pattern set)
        """
        # No pattern means match all content
        if not self.content_pattern:
            return True

        # Regex match
        import re
        try:
            return bool(re.search(self.content_pattern, content, re.IGNORECASE))
        except re.error:
            # Invalid regex, fail safe by not matching
            return False

    def matches_time(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Check if current time matches time_pattern.

        Args:
            timestamp: Time to check (defaults to now)

        Returns:
            bool: True if time matches pattern (or no pattern set)
        """
        # No pattern means match all times
        if not self.time_pattern:
            return True

        # Use current time if not provided
        if timestamp is None:
            timestamp = datetime.now()

        # Parse common time patterns
        pattern = self.time_pattern.lower()

        # Weekdays (Monday-Friday)
        if "weekday" in pattern or "monday-friday" in pattern:
            if timestamp.weekday() >= 5:  # Saturday=5, Sunday=6
                return False

        # Business hours (9am-5pm)
        if "business_hours" in pattern or "9am-5pm" in pattern:
            hour = timestamp.hour
            if hour < 9 or hour >= 17:
                return False

        # TODO: Implement more sophisticated time pattern parsing if needed

        return True

    def matches_value(self, value: Optional[float]) -> bool:
        """
        Check if value is within max_value limit.

        Args:
            value: Financial amount to check

        Returns:
            bool: True if value within limit (or no limit set)
        """
        # No limit means match all values
        if self.max_value is None:
            return True

        # No value provided means no match if limit is set
        if value is None:
            return False

        # Check value is within limit
        return value <= self.max_value


def create_default_trust_rules() -> List[TrustRule]:
    """
    Create a set of sensible default trust rules for new users.

    Returns:
        List[TrustRule]: Default trust rules (all disabled by default)
    """
    return [
        TrustRule(
            rule_id="RULE_email_known_contacts",
            rule_name="Email Replies to Known Contacts",
            action_type="email_send",
            trust_level=1,
            contact_filter=["@example.com"],  # Replace with user's domain
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=False  # User must explicitly enable
        ),
        TrustRule(
            rule_id="RULE_small_expenses",
            rule_name="Small Expense Auto-Approval",
            action_type="expense_record",
            trust_level=1,
            max_value=50.00,
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=False
        ),
        TrustRule(
            rule_id="RULE_routine_calendar",
            rule_name="Routine Calendar Events",
            action_type="calendar_create",
            trust_level=2,  # Auto-approve with notification
            time_pattern="weekdays 9am-5pm",
            created_at=datetime.utcnow(),
            created_by="user",
            enabled=False
        ),
    ]


def get_next_rule_id(existing_rules: List[TrustRule], description: str) -> str:
    """
    Generate next unique rule ID.

    Args:
        existing_rules: List of existing trust rules
        description: Human-readable description for slug generation

    Returns:
        str: Unique rule ID (e.g., "RULE_email_team")
    """
    # Create slug from description
    import re
    slug = description.lower().replace(' ', '_')
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    slug = slug[:50]  # Limit length

    # Try with base slug first
    candidate_id = f"RULE_{slug}"
    existing_ids = {rule.rule_id for rule in existing_rules}

    if candidate_id not in existing_ids:
        return candidate_id

    # Add numeric suffix if collision
    counter = 2
    while f"{candidate_id}_{counter}" in existing_ids:
        counter += 1

    return f"{candidate_id}_{counter}"
