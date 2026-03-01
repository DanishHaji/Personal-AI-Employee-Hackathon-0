"""
Contact Model for Personal AI Employee - Gold Tier

CRM profile for relationship tracking and management.

Entity Definition: specs/003-gold-tier-upgrade/data-model.md#contact
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.models.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class Contact(BaseModel):
    """
    CRM contact profile for relationship tracking and management.

    Features:
    - Automatic interaction tracking (emails, meetings, WhatsApp)
    - Relationship strength scoring
    - VIP contact designation
    - Important dates tracking (birthdays, anniversaries)
    - Conversation history
    - Tags and notes
    - Encryption support for sensitive contacts

    Storage: /Contacts/{contact_id}.md

    Example:
        contact = Contact(
            contact_id="CONTACT_john_smith",
            name="John Smith",
            email="john.smith@example.com",
            phone="+14155551234",
            organization="Acme Corp",
            title="VP Engineering",
            first_contact_date=datetime(2025, 11, 15),
            last_contact_date=datetime.now(),
            interaction_count=28,
            vip=True,
            tags=["client", "executive", "decision_maker"]
        )

        # Calculate relationship strength
        contact.update_relationship_strength()

        # Save to vault
        contact.save_to_file(
            "/vault/Contacts/CONTACT_john_smith.md",
            body=contact.generate_body()
        )
    """

    # Required fields
    contact_id: str
    name: str
    email: str
    first_contact_date: datetime
    last_contact_date: datetime
    interaction_count: int

    # Optional fields
    phone: Optional[str] = None
    organization: Optional[str] = None
    title: Optional[str] = None
    relationship_strength: int = 0
    vip: bool = False
    important_dates: Optional[List[Dict[str, str]]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    encryption_status: bool = False

    # Type identifier
    type: str = field(default="contact", init=False)

    # Encrypted fields (for VIP contacts)
    ENCRYPTED_FIELDS = ["notes", "phone"]

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_contact_id()
        self._validate_email()
        self._validate_phone()
        self._validate_dates()

        # Initialize optional fields
        if self.important_dates is None:
            self.important_dates = []
        if self.tags is None:
            self.tags = []

        # Calculate initial relationship strength
        if self.relationship_strength == 0:
            self.update_relationship_strength()

    def _validate_contact_id(self):
        """Ensure contact_id follows format CONTACT_{slug}."""
        if not self.contact_id.startswith("CONTACT_"):
            raise ValueError(f"contact_id must start with 'CONTACT_', got '{self.contact_id}'")

        # Check slug is lowercase with underscores
        slug = self.contact_id.replace("CONTACT_", "")
        if not re.match(r"^[a-z0-9_]+$", slug):
            raise ValueError(f"contact_id slug must be lowercase alphanumeric with underscores, got '{slug}'")

    def _validate_email(self):
        """Ensure email is valid format."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, self.email):
            raise ValueError(f"Invalid email format: {self.email}")

    def _validate_phone(self):
        """Ensure phone is in E.164 format if provided."""
        if self.phone is not None:
            # E.164 format: +[country code][number] (max 15 digits)
            phone_pattern = r"^\+[1-9]\d{1,14}$"
            if not re.match(phone_pattern, self.phone):
                logger.warning(f"Phone number not in E.164 format: {self.phone}")

    def _validate_dates(self):
        """Ensure dates are logical."""
        if self.last_contact_date < self.first_contact_date:
            raise ValueError("last_contact_date cannot be before first_contact_date")

    def get_schema_name(self) -> Optional[str]:
        """Get JSON Schema filename for validation."""
        return "contact-schema.json"

    def update_relationship_strength(self):
        """
        Calculate and update relationship strength score.

        Formula: interaction_count * 10 - days_since_last_contact
        """
        days_since = (datetime.now() - self.last_contact_date).days
        self.relationship_strength = (self.interaction_count * 10) - days_since

        logger.debug(f"Updated relationship strength for {self.name}: {self.relationship_strength}")

    def record_interaction(self, interaction_date: Optional[datetime] = None):
        """
        Record a new interaction with this contact.

        Args:
            interaction_date: Date of interaction (defaults to now)
        """
        if interaction_date is None:
            interaction_date = datetime.now()

        self.interaction_count += 1
        self.last_contact_date = interaction_date
        self.update_relationship_strength()

        logger.info(f"Recorded interaction with {self.name} (total: {self.interaction_count})")

    def days_since_last_contact(self) -> int:
        """
        Get number of days since last contact.

        Returns:
            int: Days since last contact
        """
        return (datetime.now() - self.last_contact_date).days

    def is_stale(self, vip_threshold: int = 30, regular_threshold: int = 60) -> bool:
        """
        Check if relationship is stale based on contact type.

        Args:
            vip_threshold: Days threshold for VIP contacts
            regular_threshold: Days threshold for regular contacts

        Returns:
            bool: True if relationship is stale
        """
        threshold = vip_threshold if self.vip else regular_threshold
        return self.days_since_last_contact() >= threshold

    def promote_to_vip(self, reason: Optional[str] = None):
        """
        Promote contact to VIP status.

        Args:
            reason: Optional reason for VIP promotion
        """
        self.vip = True
        if reason and self.notes:
            self.notes += f"\n\n**VIP Promotion ({datetime.now().date()})**: {reason}"
        elif reason:
            self.notes = f"**VIP Promotion ({datetime.now().date()})**: {reason}"

        logger.info(f"Promoted {self.name} to VIP: {reason}")

    def add_tag(self, tag: str):
        """Add a tag to the contact."""
        if tag not in self.tags:
            self.tags.append(tag)
            logger.debug(f"Added tag '{tag}' to {self.name}")

    def remove_tag(self, tag: str):
        """Remove a tag from the contact."""
        if tag in self.tags:
            self.tags.remove(tag)
            logger.debug(f"Removed tag '{tag}' from {self.name}")

    def add_important_date(self, date: str, event: str):
        """
        Add an important date to track.

        Args:
            date: Date in YYYY-MM-DD format
            event: Event description (e.g., "Birthday", "Work Anniversary")
        """
        self.important_dates.append({"date": date, "event": event})
        logger.info(f"Added important date for {self.name}: {event} on {date}")

    def generate_body(self, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate markdown body for contact profile.

        Args:
            conversation_history: Optional list of conversation entries

        Returns:
            str: Formatted markdown body
        """
        # Header with contact info
        phone_str = f" | {self.phone}" if self.phone else ""
        body = f"""# {self.name}
**{self.title or 'Contact'}** at **{self.organization or 'Unknown Organization'}** | [{self.email}](mailto:{self.email}){phone_str}

## Relationship Summary
- **First Contact**: {self.first_contact_date.strftime('%B %Y')}
- **Interactions**: {self.interaction_count} (emails, meetings, calls)
- **Last Contact**: {self.days_since_last_contact()} days ago
- **Relationship Strength**: {self.relationship_strength} {"(Strong)" if self.relationship_strength > 200 else "(Moderate)" if self.relationship_strength > 100 else "(Weak)"}
{"- **VIP Contact** ⭐" if self.vip else ""}

"""

        # Tags
        if self.tags:
            tags_str = ", ".join([f"`{tag}`" for tag in self.tags])
            body += f"**Tags**: {tags_str}\n\n"

        # Important dates
        if self.important_dates:
            body += "## Important Dates\n\n"
            for date_info in self.important_dates:
                body += f"- **{date_info['event']}**: {date_info['date']}\n"
            body += "\n"

        # Conversation history
        if conversation_history:
            body += "## Conversation History\n\n"
            for conv in conversation_history:
                date_str = conv.get("date", "Unknown date")
                medium = conv.get("medium", "Unknown")
                topics = conv.get("topics", [])

                body += f"### {date_str} - {conv.get('title', 'Conversation')}\n"
                body += f"**Medium**: {medium}\n"

                if topics:
                    body += f"- Topics: {', '.join(topics)}\n"

                if conv.get("summary"):
                    body += f"- Summary: {conv['summary']}\n"

                if conv.get("follow_up"):
                    body += f"- Follow-up: {conv['follow_up']}\n"

                body += "\n"

        # Notes
        if self.notes:
            body += "## Important Notes\n\n"
            body += self.notes + "\n\n"

        return body.strip()

    @classmethod
    def generate_id(cls, name: str, email: Optional[str] = None) -> str:
        """
        Generate contact ID from name.

        Args:
            name: Contact name
            email: Optional email (used for deduplication)

        Returns:
            str: Contact ID in format CONTACT_{slug}
        """
        # Create slug from name
        slug = name.lower()

        # Remove special characters
        slug = re.sub(r'[^a-z0-9\s]', '', slug)

        # Replace spaces with underscores
        slug = slug.replace(' ', '_')

        # Limit length
        slug = slug[:30]

        return f"CONTACT_{slug}"

    def get_filename(self) -> str:
        """
        Generate filename for contact profile.

        Returns:
            str: Filename in format "{contact_id}.md"
        """
        return f"{self.contact_id}.md"

    @classmethod
    def from_email_interaction(
        cls,
        name: str,
        email: str,
        interaction_date: Optional[datetime] = None,
        context: Optional[str] = None
    ) -> "Contact":
        """
        Factory method to create contact from email interaction.

        Args:
            name: Contact name
            email: Contact email
            interaction_date: Date of interaction
            context: Optional context about how contact was made

        Returns:
            Contact: New contact instance
        """
        if interaction_date is None:
            interaction_date = datetime.now()

        contact_id = cls.generate_id(name, email)

        notes = None
        if context:
            notes = f"**First Contact ({interaction_date.date()})**: {context}"

        return cls(
            contact_id=contact_id,
            name=name,
            email=email,
            first_contact_date=interaction_date,
            last_contact_date=interaction_date,
            interaction_count=1,
            notes=notes
        )


# Helper functions

def parse_contact_profile(file_path: Path, decrypt: bool = False) -> tuple[Contact, str]:
    """
    Parse contact profile from markdown file.

    Args:
        file_path: Path to contact file
        decrypt: Whether to decrypt encrypted fields

    Returns:
        tuple: (Contact instance, body content)
    """
    return Contact.load_from_file(file_path, decrypt=decrypt)


def save_contact_profile(
    contact: Contact,
    vault_path: Path,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    encrypt: bool = False
) -> Path:
    """
    Save contact profile to vault.

    Args:
        contact: Contact instance
        vault_path: Path to vault root
        conversation_history: Optional conversation history
        encrypt: Whether to encrypt sensitive fields (for VIP contacts)

    Returns:
        Path: Path to saved file
    """
    contacts_dir = vault_path / "Contacts"
    contacts_dir.mkdir(parents=True, exist_ok=True)

    filename = contact.get_filename()
    file_path = contacts_dir / filename

    body = contact.generate_body(conversation_history=conversation_history)

    # Encrypt if VIP and encryption requested
    should_encrypt = encrypt and contact.vip

    contact.save_to_file(file_path, body=body, encrypt=should_encrypt)

    logger.info(f"Saved contact profile to {file_path}")
    return file_path


def load_all_contacts(vault_path: Path, decrypt: bool = False) -> List[Contact]:
    """
    Load all contact profiles from vault.

    Args:
        vault_path: Path to vault root
        decrypt: Whether to decrypt encrypted fields

    Returns:
        List[Contact]: List of contact instances
    """
    contacts_dir = vault_path / "Contacts"

    if not contacts_dir.exists():
        return []

    contacts = []
    for contact_file in contacts_dir.glob("CONTACT_*.md"):
        try:
            contact, _ = Contact.load_from_file(contact_file, decrypt=decrypt)
            contacts.append(contact)
        except Exception as e:
            logger.error(f"Error loading contact from {contact_file}: {e}")
            continue

    return contacts
