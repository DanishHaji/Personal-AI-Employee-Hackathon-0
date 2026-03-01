"""
Contact Service for Personal AI Employee - Gold Tier

CRM contact management with auto-creation, deduplication, and relationship tracking.

Features:
- Auto-creation from email/meeting/WhatsApp interactions
- Fuzzy matching deduplication
- Relationship strength scoring
- Conversation history tracking
- Important dates extraction
- VIP stale relationship detection
- Follow-up suggestions
- Encryption for VIP contacts

Usage:
    service = ContactService(vault_path="/path/to/vault")

    # Create contact from email
    contact = service.create_or_update_from_email(
        name="John Smith",
        email="john@example.com",
        context="Q2 project discussion"
    )

    # Check for stale relationships
    stale_contacts = service.find_stale_relationships()

    # Generate follow-up suggestions
    service.create_follow_up_suggestions(stale_contacts)
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from src.models.contact import Contact, save_contact_profile, load_all_contacts
from src.models.proactive_suggestion import ProactiveSuggestion

logger = logging.getLogger(__name__)


class ContactService:
    """
    CRM service for contact management and relationship tracking.

    Handles contact lifecycle from creation through relationship maintenance.
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize ContactService.

        Args:
            vault_path: Path to Obsidian vault root
        """
        self.vault_path = Path(vault_path).resolve()
        self.contacts_dir = self.vault_path / "Contacts"
        self.needs_action_dir = self.vault_path / "Needs_Action"

        # Ensure directories exist
        self.contacts_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded contacts (reduces file I/O)
        self._contact_cache: Dict[str, Contact] = {}
        self._cache_loaded = False

        # Try to import fuzzywuzzy for deduplication
        try:
            from fuzzywuzzy import fuzz
            self.fuzz = fuzz
            self.fuzzy_available = True
            logger.info("Fuzzy matching available for contact deduplication")
        except ImportError:
            self.fuzz = None
            self.fuzzy_available = False
            logger.warning("fuzzywuzzy not installed - deduplication will use exact matching only")

        logger.info("ContactService initialized")

    def _load_cache(self):
        """Load all contacts into cache."""
        if self._cache_loaded:
            return

        contacts = load_all_contacts(self.vault_path, decrypt=False)
        for contact in contacts:
            self._contact_cache[contact.contact_id] = contact

        self._cache_loaded = True
        logger.info(f"Loaded {len(self._contact_cache)} contacts into cache")

    def _save_contact(
        self,
        contact: Contact,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        encrypt_vip: bool = True
    ) -> Path:
        """
        Save contact and update cache.

        Args:
            contact: Contact to save
            conversation_history: Optional conversation history
            encrypt_vip: Whether to encrypt VIP contact data

        Returns:
            Path: Path to saved file
        """
        # Save to file
        file_path = save_contact_profile(
            contact=contact,
            vault_path=self.vault_path,
            conversation_history=conversation_history,
            encrypt=encrypt_vip
        )

        # Update cache
        self._contact_cache[contact.contact_id] = contact

        return file_path

    def find_contact_by_email(self, email: str) -> Optional[Contact]:
        """
        Find contact by exact email match.

        Args:
            email: Email address to search for

        Returns:
            Contact: Matching contact, or None if not found
        """
        self._load_cache()

        email_lower = email.lower()

        for contact in self._contact_cache.values():
            if contact.email.lower() == email_lower:
                return contact

        return None

    def find_similar_contacts(
        self,
        name: str,
        email: str,
        similarity_threshold: float = 0.85
    ) -> List[Tuple[Contact, float]]:
        """
        Find similar contacts using fuzzy matching.

        Args:
            name: Contact name
            email: Contact email
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List[Tuple[Contact, float]]: List of (contact, similarity_score) tuples
        """
        self._load_cache()

        if not self.fuzzy_available:
            # Fall back to exact email matching
            exact_match = self.find_contact_by_email(email)
            return [(exact_match, 1.0)] if exact_match else []

        similar_contacts = []

        for contact in self._contact_cache.values():
            # Check email similarity
            email_similarity = self.fuzz.ratio(email.lower(), contact.email.lower()) / 100.0

            # Check name similarity
            name_similarity = self.fuzz.ratio(name.lower(), contact.name.lower()) / 100.0

            # Combined similarity (weighted towards email)
            combined_similarity = (email_similarity * 0.7) + (name_similarity * 0.3)

            if combined_similarity >= similarity_threshold:
                similar_contacts.append((contact, combined_similarity))

        # Sort by similarity (highest first)
        similar_contacts.sort(key=lambda x: x[1], reverse=True)

        return similar_contacts

    def create_or_update_from_email(
        self,
        name: str,
        email: str,
        interaction_date: Optional[datetime] = None,
        context: Optional[str] = None,
        auto_merge: bool = True
    ) -> Contact:
        """
        Create new contact or update existing from email interaction.

        Args:
            name: Contact name
            email: Contact email
            interaction_date: Date of interaction (defaults to now)
            context: Context about the interaction
            auto_merge: Whether to automatically merge with similar contacts

        Returns:
            Contact: Created or updated contact
        """
        if interaction_date is None:
            interaction_date = datetime.now()

        # Check for exact email match
        existing = self.find_contact_by_email(email)

        if existing:
            # Update existing contact
            existing.record_interaction(interaction_date)
            self._save_contact(existing)
            logger.info(f"Updated existing contact: {existing.name} ({existing.email})")
            return existing

        # Check for similar contacts (potential duplicates)
        if auto_merge and self.fuzzy_available:
            similar = self.find_similar_contacts(name, email, similarity_threshold=0.90)

            if similar:
                # Use most similar contact
                best_match, similarity = similar[0]
                logger.info(
                    f"Found similar contact (similarity: {similarity:.0%}): "
                    f"{best_match.name} - merging with new email {email}"
                )

                # Update contact info (keep original email but note the new one)
                if best_match.notes:
                    best_match.notes += f"\n\n**Alternative Email**: {email} (added {interaction_date.date()})"
                else:
                    best_match.notes = f"**Alternative Email**: {email} (added {interaction_date.date()})"

                best_match.record_interaction(interaction_date)
                self._save_contact(best_match)
                return best_match

        # Create new contact
        contact = Contact.from_email_interaction(
            name=name,
            email=email,
            interaction_date=interaction_date,
            context=context
        )

        self._save_contact(contact)
        logger.info(f"Created new contact: {contact.name} ({contact.email})")

        return contact

    def create_or_update_from_meeting(
        self,
        attendees: List[Dict[str, str]],
        meeting_date: datetime,
        meeting_title: str
    ) -> List[Contact]:
        """
        Create or update contacts from meeting attendees.

        Args:
            attendees: List of attendee dicts with name, email, role
            meeting_date: Date of the meeting
            meeting_title: Title of the meeting

        Returns:
            List[Contact]: List of created/updated contacts
        """
        contacts = []

        for attendee in attendees:
            name = attendee.get("name", "Unknown")
            email = attendee.get("email")

            if not email:
                logger.warning(f"Skipping attendee without email: {name}")
                continue

            context = f"Met in '{meeting_title}' meeting"
            if attendee.get("role"):
                context += f" (role: {attendee['role']})"

            contact = self.create_or_update_from_email(
                name=name,
                email=email,
                interaction_date=meeting_date,
                context=context
            )

            # Update title/organization if provided
            if attendee.get("role") and not contact.title:
                contact.title = attendee["role"]
                self._save_contact(contact)

            contacts.append(contact)

        logger.info(f"Processed {len(contacts)} contacts from meeting")
        return contacts

    def update_relationship_strengths(self):
        """Update relationship strength scores for all contacts."""
        self._load_cache()

        for contact in self._contact_cache.values():
            contact.update_relationship_strength()
            self._save_contact(contact)

        logger.info(f"Updated relationship strengths for {len(self._contact_cache)} contacts")

    def find_stale_relationships(
        self,
        vip_threshold: int = 30,
        regular_threshold: int = 60,
        vip_only: bool = False
    ) -> List[Contact]:
        """
        Find contacts with stale relationships.

        Args:
            vip_threshold: Days threshold for VIP contacts
            regular_threshold: Days threshold for regular contacts
            vip_only: Whether to only check VIP contacts

        Returns:
            List[Contact]: List of contacts with stale relationships
        """
        self._load_cache()

        stale_contacts = []

        for contact in self._contact_cache.values():
            # Skip non-VIP if vip_only is True
            if vip_only and not contact.vip:
                continue

            if contact.is_stale(vip_threshold, regular_threshold):
                stale_contacts.append(contact)

        # Sort by relationship strength (strongest first - these are most important to maintain)
        stale_contacts.sort(key=lambda c: c.relationship_strength, reverse=True)

        logger.info(f"Found {len(stale_contacts)} stale relationships")
        return stale_contacts

    def create_follow_up_suggestions(
        self,
        stale_contacts: Optional[List[Contact]] = None,
        max_suggestions: int = 5
    ) -> List[ProactiveSuggestion]:
        """
        Create proactive follow-up suggestions for stale relationships.

        Args:
            stale_contacts: Optional list of stale contacts (will find if not provided)
            max_suggestions: Maximum number of suggestions to create

        Returns:
            List[ProactiveSuggestion]: Created suggestions
        """
        if stale_contacts is None:
            stale_contacts = self.find_stale_relationships(vip_only=True)

        suggestions = []

        for contact in stale_contacts[:max_suggestions]:
            # Create relationship maintenance suggestion
            suggestion = ProactiveSuggestion.create_relationship_maintenance(
                contact_id=contact.contact_id,
                contact_name=contact.name,
                days_since_contact=contact.days_since_last_contact(),
                last_conversation_topic=None  # Would extract from conversation history
            )

            # Save suggestion to /Needs_Action/
            filename = suggestion.get_filename()
            file_path = self.needs_action_dir / filename

            body = suggestion.to_markdown_body()
            suggestion.save_to_file(file_path, body=body)

            suggestions.append(suggestion)
            logger.info(f"Created follow-up suggestion for {contact.name}")

        return suggestions

    def promote_to_vip(self, contact_id: str, reason: Optional[str] = None) -> bool:
        """
        Promote a contact to VIP status.

        Args:
            contact_id: Contact ID
            reason: Reason for VIP promotion

        Returns:
            bool: True if successful
        """
        self._load_cache()

        contact = self._contact_cache.get(contact_id)
        if not contact:
            logger.error(f"Contact not found: {contact_id}")
            return False

        contact.promote_to_vip(reason)
        self._save_contact(contact, encrypt_vip=True)  # Encrypt VIP data

        logger.info(f"Promoted {contact.name} to VIP")
        return True

    def auto_promote_to_vip(self, strength_threshold: int = 200):
        """
        Automatically promote contacts to VIP based on relationship strength.

        Args:
            strength_threshold: Minimum relationship strength for auto-promotion
        """
        self._load_cache()

        promoted_count = 0

        for contact in self._contact_cache.values():
            if not contact.vip and contact.relationship_strength >= strength_threshold:
                contact.promote_to_vip(
                    reason=f"Auto-promoted (relationship strength: {contact.relationship_strength})"
                )
                self._save_contact(contact, encrypt_vip=True)
                promoted_count += 1

        logger.info(f"Auto-promoted {promoted_count} contacts to VIP")

    def extract_important_dates(self, text: str) -> List[Dict[str, str]]:
        """
        Extract important dates from text (birthdays, anniversaries, etc.).

        Args:
            text: Text to extract dates from

        Returns:
            List[Dict]: List of date dicts with 'date' and 'event' keys
        """
        important_dates = []

        # Patterns for date mentions
        patterns = [
            # "birthday on June 15"
            (r"birthday\s+(?:on|is)\s+(\w+\s+\d{1,2})", "Birthday"),
            # "work anniversary on September 1"
            (r"(?:work\s+)?anniversary\s+(?:on|is)\s+(\w+\s+\d{1,2})", "Work Anniversary"),
            # "joined on 2020-05-15"
            (r"joined\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})", "Join Date"),
        ]

        for pattern, event_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)

                # Try to parse and normalize date
                try:
                    # Handle "Month Day" format
                    if re.match(r"\w+\s+\d{1,2}", date_str):
                        # Assume current or next year
                        current_year = datetime.now().year
                        date_str = f"{current_year}-{date_str}"

                    # Would need more sophisticated parsing here
                    # For now, just store the extracted string
                    important_dates.append({
                        "date": date_str,
                        "event": event_type
                    })
                except Exception as e:
                    logger.debug(f"Could not parse date '{date_str}': {e}")

        return important_dates

    def get_contact(self, contact_id: str, decrypt: bool = False) -> Optional[Contact]:
        """
        Get contact by ID.

        Args:
            contact_id: Contact ID
            decrypt: Whether to decrypt encrypted fields

        Returns:
            Contact: Contact instance, or None if not found
        """
        if not decrypt:
            # Use cache
            self._load_cache()
            return self._contact_cache.get(contact_id)

        # Load from file with decryption
        file_path = self.contacts_dir / f"{contact_id}.md"
        if not file_path.exists():
            return None

        try:
            contact, _ = Contact.load_from_file(file_path, decrypt=True)
            return contact
        except Exception as e:
            logger.error(f"Error loading contact {contact_id}: {e}")
            return None

    def search_contacts(
        self,
        query: str,
        search_fields: Optional[List[str]] = None
    ) -> List[Contact]:
        """
        Search contacts by query string.

        Args:
            query: Search query
            search_fields: Fields to search (name, email, organization, tags)

        Returns:
            List[Contact]: Matching contacts
        """
        self._load_cache()

        if search_fields is None:
            search_fields = ["name", "email", "organization", "tags"]

        query_lower = query.lower()
        matching_contacts = []

        for contact in self._contact_cache.values():
            for field in search_fields:
                value = getattr(contact, field, None)

                if value is None:
                    continue

                # Handle list fields (tags)
                if isinstance(value, list):
                    if any(query_lower in str(item).lower() for item in value):
                        matching_contacts.append(contact)
                        break
                # Handle string fields
                elif query_lower in str(value).lower():
                    matching_contacts.append(contact)
                    break

        return matching_contacts

    def get_top_contacts(self, limit: int = 10, by: str = "strength") -> List[Contact]:
        """
        Get top contacts by relationship strength or interaction count.

        Args:
            limit: Maximum number of contacts to return
            by: Sort criteria ("strength" or "interactions")

        Returns:
            List[Contact]: Top contacts
        """
        self._load_cache()

        contacts = list(self._contact_cache.values())

        if by == "strength":
            contacts.sort(key=lambda c: c.relationship_strength, reverse=True)
        elif by == "interactions":
            contacts.sort(key=lambda c: c.interaction_count, reverse=True)
        else:
            raise ValueError(f"Invalid sort criteria: {by}")

        return contacts[:limit]

    def get_contacts_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about contacts.

        Returns:
            Dict: Summary statistics
        """
        self._load_cache()

        contacts = list(self._contact_cache.values())

        vip_contacts = [c for c in contacts if c.vip]
        stale_contacts = self.find_stale_relationships()

        # Calculate average relationship strength
        total_strength = sum(c.relationship_strength for c in contacts)
        avg_strength = total_strength / len(contacts) if contacts else 0

        return {
            "total_contacts": len(contacts),
            "vip_contacts": len(vip_contacts),
            "stale_relationships": len(stale_contacts),
            "avg_relationship_strength": round(avg_strength, 1),
            "total_interactions": sum(c.interaction_count for c in contacts),
            "top_contact": contacts[0].name if contacts else None
        }


# Helper functions

def create_contact_from_email(
    vault_path: str | Path,
    name: str,
    email: str,
    context: Optional[str] = None
) -> Contact:
    """
    Helper to create contact from email interaction.

    Args:
        vault_path: Path to vault root
        name: Contact name
        email: Contact email
        context: Interaction context

    Returns:
        Contact: Created or updated contact
    """
    service = ContactService(vault_path=vault_path)
    return service.create_or_update_from_email(name, email, context=context)


if __name__ == "__main__":
    # Test runner
    import sys

    if len(sys.argv) < 2:
        print("Usage: python contact_service.py <vault_path>")
        sys.exit(1)

    vault_path = sys.argv[1]

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create service
    service = ContactService(vault_path=vault_path)

    # Get summary
    summary = service.get_contacts_summary()

    print("\n=== CRM Summary ===")
    print(f"Total Contacts: {summary['total_contacts']}")
    print(f"VIP Contacts: {summary['vip_contacts']}")
    print(f"Stale Relationships: {summary['stale_relationships']}")
    print(f"Average Relationship Strength: {summary['avg_relationship_strength']}")
    print(f"Total Interactions: {summary['total_interactions']}")
