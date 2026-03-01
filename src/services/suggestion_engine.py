"""
Suggestion Engine Service for Personal AI Employee - Gold Tier

AI-initiated task suggestions based on patterns, context, and relationships.

Features:
- Follow-up detection (unanswered important emails)
- Incomplete task chain detection (scheduled meeting but no agenda)
- Recurring pattern detection (monthly expense reports)
- Suggestion volume limits (max 3 per category per day)
- Opt-in/opt-out category management
- Feedback learning from dismissed suggestions

Usage:
    engine = SuggestionEngine(vault_path="/path/to/vault")

    # Run pattern detection
    suggestions = engine.run_detection()

    # Create suggestion in /Needs_Action/
    engine.create_suggestion(suggestion)

    # Process user feedback
    engine.process_feedback(suggestion_id, "rejected", "Not relevant")
"""

import json
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from collections import defaultdict

from src.models.proactive_suggestion import ProactiveSuggestion, load_suggestions_from_directory
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Proactive suggestion engine for AI-initiated task recommendations.

    Analyzes audit logs, email history, calendar events, and contact data to
    identify patterns requiring follow-up actions, reminders, or relationship
    maintenance.
    """

    # Default configuration
    DEFAULT_CONFIG = {
        "follow_up_threshold_days": 3,  # Days before suggesting follow-up
        "vip_contact_threshold_days": 30,  # Days before VIP relationship is stale
        "regular_contact_threshold_days": 60,  # Days for regular contacts
        "max_suggestions_per_category": 3,  # Daily limit per category
        "min_confidence_threshold": 0.60,  # Minimum confidence to create suggestion
        "enabled_categories": [  # Categories enabled by default
            "follow_up",
            "reminder",
            "relationship_maintenance",
            "task_chain"
        ]
    }

    def __init__(self, vault_path: str | Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SuggestionEngine.

        Args:
            vault_path: Absolute path to Obsidian vault root
            config: Optional configuration overrides
        """
        self.vault_path = Path(vault_path).resolve()
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.contacts_dir = self.vault_path / "Contacts"
        self.calendar_dir = self.vault_path / "Calendar"

        # Load configuration
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._load_preferences()

        # Initialize audit service
        self.audit_service = AuditService(vault_path)

        # Feedback tracking
        self.feedback_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._load_feedback_history()

        # Ensure directories exist
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

    def _load_preferences(self):
        """
        Load suggestion preferences from Company_Handbook.md.

        Preferences include:
        - enabled_categories: Categories user wants suggestions for
        - disabled_categories: Categories user has opted out of
        - follow_up_threshold_days: Custom threshold for follow-ups
        - vip_contact_threshold_days: Custom threshold for VIP relationships
        """
        handbook_path = self.vault_path / "Company_Handbook.md"

        if not handbook_path.exists():
            logger.warning(f"Company_Handbook.md not found at {handbook_path}")
            return

        try:
            with open(handbook_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            if not content.startswith('---'):
                return

            parts = content.split('---', 2)
            if len(parts) < 3:
                return

            frontmatter = yaml.safe_load(parts[1])

            # Load suggestion preferences
            suggestion_prefs = frontmatter.get('suggestion_preferences', {})

            if 'enabled_categories' in suggestion_prefs:
                self.config['enabled_categories'] = suggestion_prefs['enabled_categories']

            if 'follow_up_threshold_days' in suggestion_prefs:
                self.config['follow_up_threshold_days'] = suggestion_prefs['follow_up_threshold_days']

            if 'vip_contact_threshold_days' in suggestion_prefs:
                self.config['vip_contact_threshold_days'] = suggestion_prefs['vip_contact_threshold_days']

            if 'max_suggestions_per_category' in suggestion_prefs:
                self.config['max_suggestions_per_category'] = suggestion_prefs['max_suggestions_per_category']

            logger.info(f"Loaded suggestion preferences: {self.config}")

        except Exception as e:
            logger.error(f"Error loading preferences from Company_Handbook.md: {e}")

    def _load_feedback_history(self):
        """Load feedback history for learning from dismissed suggestions."""
        feedback_file = self.vault_path / "Insights" / "suggestion_feedback.json"

        if not feedback_file.exists():
            return

        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                self.feedback_history = json.load(f)
                logger.info(f"Loaded {len(self.feedback_history)} feedback entries")
        except Exception as e:
            logger.error(f"Error loading feedback history: {e}")

    def _save_feedback_history(self):
        """Save feedback history to persistent storage."""
        feedback_file = self.vault_path / "Insights" / "suggestion_feedback.json"
        feedback_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_history, f, indent=2, default=str)
            logger.info("Saved feedback history")
        except Exception as e:
            logger.error(f"Error saving feedback history: {e}")

    def _is_category_enabled(self, category: str) -> bool:
        """
        Check if a suggestion category is enabled.

        Args:
            category: Suggestion category

        Returns:
            bool: True if category is enabled
        """
        return category in self.config['enabled_categories']

    def _get_daily_suggestion_count(self, category: str) -> int:
        """
        Get count of suggestions created today for a category.

        Args:
            category: Suggestion category

        Returns:
            int: Number of suggestions created today
        """
        today = datetime.now().date()
        suggestions = load_suggestions_from_directory(self.needs_action_dir)

        count = sum(
            1 for s in suggestions
            if s.category == category and s.created_at.date() == today
        )

        return count

    def _check_volume_limit(self, category: str) -> bool:
        """
        Check if suggestion volume limit has been reached for category today.

        Args:
            category: Suggestion category

        Returns:
            bool: True if under limit, False if limit reached
        """
        max_per_category = self.config['max_suggestions_per_category']
        current_count = self._get_daily_suggestion_count(category)

        if current_count >= max_per_category:
            logger.info(f"Volume limit reached for {category}: {current_count}/{max_per_category}")
            return False

        return True

    def _calculate_learned_confidence(
        self,
        category: str,
        context_keywords: List[str]
    ) -> float:
        """
        Calculate confidence adjustment based on past feedback.

        Args:
            category: Suggestion category
            context_keywords: Keywords from suggestion context

        Returns:
            float: Confidence adjustment factor (0.8-1.2)
        """
        # Get feedback for this category
        category_feedback = self.feedback_history.get(category, [])

        if not category_feedback:
            return 1.0  # No adjustment

        # Count accepted vs rejected with similar context
        accepted = 0
        rejected = 0

        for feedback in category_feedback:
            feedback_keywords = feedback.get('context_keywords', [])

            # Check for keyword overlap
            overlap = set(context_keywords) & set(feedback_keywords)
            if not overlap:
                continue

            if feedback.get('response') == 'accepted':
                accepted += 1
            elif feedback.get('response') == 'rejected':
                rejected += 1

        total = accepted + rejected
        if total == 0:
            return 1.0

        # Calculate adjustment (0.8 to 1.2 range)
        acceptance_rate = accepted / total
        adjustment = 0.8 + (acceptance_rate * 0.4)

        return adjustment

    def detect_follow_ups(self) -> List[ProactiveSuggestion]:
        """
        Detect emails sent that haven't received a reply within threshold.

        Returns:
            List[ProactiveSuggestion]: Follow-up suggestions
        """
        if not self._is_category_enabled("follow_up"):
            return []

        if not self._check_volume_limit("follow_up"):
            return []

        suggestions = []
        threshold_days = self.config['follow_up_threshold_days']

        # Query sent emails from last 14 days
        sent_emails = self.audit_service.query_logs(
            days=14,
            action_type="email_send",
            result="success"
        )

        # Get received emails (for reply detection)
        received_emails = self.audit_service.query_logs(
            days=14,
            action_type="email_detected"
        )

        # Build map of received emails by sender
        received_by_sender = defaultdict(list)
        for email in received_emails:
            sender = email.get("target", "").split()[0]  # Extract email from "name <email>"
            received_by_sender[sender].append(email)

        # Check sent emails for missing replies
        for sent_email in sent_emails:
            recipient = sent_email.get("target", "")
            if not recipient:
                continue

            # Extract email address
            if '<' in recipient:
                recipient_email = recipient.split('<')[1].split('>')[0]
            else:
                recipient_email = recipient.split()[0]

            # Check if marked as important
            parameters = sent_email.get("parameters", {})
            if not parameters.get("important", False):
                continue

            # Calculate days since sent
            timestamp_str = sent_email.get("timestamp")
            if not timestamp_str:
                continue

            sent_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            days_since = (datetime.now() - sent_date).days

            # Check if enough days have passed
            if days_since < threshold_days:
                continue

            # Check if we received a reply
            replies = received_by_sender.get(recipient_email, [])
            has_reply = any(
                datetime.fromisoformat(r["timestamp"].replace('Z', '+00:00')) > sent_date
                for r in replies
            )

            if has_reply:
                continue

            # Create follow-up suggestion
            subject = parameters.get("subject", "your email")
            email_id = sent_email.get("id", "EMAIL_unknown")

            # Extract context keywords for learning
            context_keywords = [word.lower() for word in subject.split() if len(word) > 4]

            # Calculate confidence with learning adjustment
            base_confidence = min(0.95, 0.60 + (days_since * 0.10))
            learned_adjustment = self._calculate_learned_confidence("follow_up", context_keywords)
            confidence = min(0.99, base_confidence * learned_adjustment)

            # Check minimum confidence threshold
            if confidence < self.config['min_confidence_threshold']:
                continue

            suggestion = ProactiveSuggestion.create_follow_up(
                email_id=email_id,
                contact_email=recipient_email,
                original_subject=subject,
                days_since_sent=days_since,
                draft_message=None  # TODO: Generate with AI
            )

            # Override confidence with learned value
            suggestion.confidence_score = confidence

            suggestions.append(suggestion)

            # Check volume limit
            if not self._check_volume_limit("follow_up"):
                break

        return suggestions

    def detect_incomplete_task_chains(self) -> List[ProactiveSuggestion]:
        """
        Detect incomplete task chains (e.g., meeting scheduled but no agenda sent).

        Returns:
            List[ProactiveSuggestion]: Task chain suggestions
        """
        if not self._is_category_enabled("task_chain"):
            return []

        if not self._check_volume_limit("task_chain"):
            return []

        suggestions = []

        # Load calendar events
        calendar_file = self.calendar_dir / "events.json"
        if not calendar_file.exists():
            return suggestions

        try:
            with open(calendar_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
                events = events_data.get("events", [])
        except Exception as e:
            logger.error(f"Error loading calendar events: {e}")
            return suggestions

        # Check upcoming meetings for missing agendas
        now = datetime.now()
        for event in events:
            start_time_str = event.get("start_time")
            if not start_time_str:
                continue

            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))

            # Check meetings in next 48 hours
            hours_until = (start_time - now).total_seconds() / 3600
            if hours_until < 0 or hours_until > 48:
                continue

            # Check if agenda is missing
            agenda = event.get("agenda")
            if agenda and len(agenda.strip()) > 10:
                continue

            # Check if created by AI (suggests we should help)
            if event.get("created_by") != "ai":
                continue

            # Create task chain suggestion
            event_id = event.get("event_id", "CAL_unknown")
            title = event.get("title", "Meeting")

            suggestion = ProactiveSuggestion.create_task_chain(
                incomplete_task="Create meeting agenda",
                blocking_task=f"Prepare for '{title}' meeting",
                related_entities=[event_id],
                context=f"Meeting '{title}' scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} but no agenda has been set"
            )

            suggestions.append(suggestion)

            # Check volume limit
            if not self._check_volume_limit("task_chain"):
                break

        return suggestions

    def detect_recurring_patterns(self) -> List[ProactiveSuggestion]:
        """
        Detect recurring patterns that need reminders (e.g., monthly expense reports).

        Returns:
            List[ProactiveSuggestion]: Recurring pattern reminders
        """
        if not self._is_category_enabled("reminder"):
            return []

        if not self._check_volume_limit("reminder"):
            return []

        suggestions = []

        # Define known recurring patterns
        recurring_patterns = [
            {
                "task_name": "Monthly Expense Report",
                "day_of_month": 5,
                "days_before_reminder": 2,
                "context": "Monthly expense report is typically due on the 5th of each month",
                "related_entities": ["BUDGET_monthly"]
            },
            {
                "task_name": "Weekly Status Update",
                "day_of_week": 4,  # Friday
                "hours_before_reminder": 24,
                "context": "Weekly status update is typically sent on Friday afternoon",
                "related_entities": ["DOC_status_weekly"]
            }
        ]

        now = datetime.now()

        for pattern in recurring_patterns:
            task_name = pattern["task_name"]

            # Check monthly patterns
            if "day_of_month" in pattern:
                due_day = pattern["day_of_month"]
                days_before = pattern["days_before_reminder"]

                # Calculate due date for this month
                due_date = datetime(now.year, now.month, due_day)

                # If already passed this month, use next month
                if due_date < now:
                    if now.month == 12:
                        due_date = datetime(now.year + 1, 1, due_day)
                    else:
                        due_date = datetime(now.year, now.month + 1, due_day)

                # Check if we're within reminder window
                days_until = (due_date - now).days
                if days_until > days_before or days_until < 0:
                    continue

                suggestion = ProactiveSuggestion.create_reminder(
                    task_name=task_name,
                    due_date=due_date,
                    related_entities=pattern["related_entities"],
                    context=pattern["context"]
                )

                suggestions.append(suggestion)

            # Check weekly patterns
            elif "day_of_week" in pattern:
                due_day_of_week = pattern["day_of_week"]
                hours_before = pattern.get("hours_before_reminder", 24)

                # Calculate next occurrence
                days_ahead = (due_day_of_week - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week

                due_date = now + timedelta(days=days_ahead)
                due_date = due_date.replace(hour=17, minute=0, second=0, microsecond=0)

                # Check if we're within reminder window
                hours_until = (due_date - now).total_seconds() / 3600
                if hours_until > hours_before or hours_until < 0:
                    continue

                suggestion = ProactiveSuggestion.create_reminder(
                    task_name=task_name,
                    due_date=due_date,
                    related_entities=pattern["related_entities"],
                    context=pattern["context"]
                )

                suggestions.append(suggestion)

            # Check volume limit
            if not self._check_volume_limit("reminder"):
                break

        return suggestions

    def detect_stale_relationships(self) -> List[ProactiveSuggestion]:
        """
        Detect VIP contacts that haven't been contacted in threshold days.

        Returns:
            List[ProactiveSuggestion]: Relationship maintenance suggestions
        """
        if not self._is_category_enabled("relationship_maintenance"):
            return []

        if not self._check_volume_limit("relationship_maintenance"):
            return []

        suggestions = []

        # Check if Contacts directory exists
        if not self.contacts_dir.exists():
            return suggestions

        # Load contact files
        for contact_file in self.contacts_dir.glob("CONTACT_*.md"):
            try:
                with open(contact_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse frontmatter
                if not content.startswith('---'):
                    continue

                parts = content.split('---', 2)
                if len(parts) < 3:
                    continue

                frontmatter = yaml.safe_load(parts[1])

                # Check if VIP contact
                is_vip = frontmatter.get('vip', False)
                threshold = self.config['vip_contact_threshold_days'] if is_vip else self.config['regular_contact_threshold_days']

                # Get last contact date
                last_contact_value = frontmatter.get('last_contact_date')
                if not last_contact_value:
                    continue

                # Handle both datetime objects and strings
                if isinstance(last_contact_value, datetime):
                    last_contact = last_contact_value
                elif isinstance(last_contact_value, str):
                    # Parse ISO format datetime string
                    last_contact = datetime.fromisoformat(last_contact_value.replace('Z', '+00:00'))
                else:
                    logger.warning(f"Invalid last_contact_date type: {type(last_contact_value)}")
                    continue

                days_since = (datetime.now() - last_contact).days

                # Check if stale
                if days_since < threshold:
                    continue

                # Extract contact info
                contact_id = frontmatter.get('contact_id', 'CONTACT_unknown')
                contact_name = frontmatter.get('name', 'Unknown')

                # Get last conversation topic from body (simplified)
                body = parts[2].strip()
                last_topic = None
                if "## Conversation History" in body:
                    # Extract most recent topic (simplified parsing)
                    lines = body.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith('### 202') and i + 3 < len(lines):
                            # Get topics from next few lines
                            last_topic = lines[i + 3].replace('- Topics:', '').strip()
                            break

                suggestion = ProactiveSuggestion.create_relationship_maintenance(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    days_since_contact=days_since,
                    last_conversation_topic=last_topic
                )

                suggestions.append(suggestion)

                # Check volume limit
                if not self._check_volume_limit("relationship_maintenance"):
                    break

            except Exception as e:
                logger.error(f"Error processing contact file {contact_file}: {e}")
                continue

        return suggestions

    def run_detection(self) -> List[ProactiveSuggestion]:
        """
        Run all pattern detection methods and return suggestions.

        Returns:
            List[ProactiveSuggestion]: All detected suggestions
        """
        all_suggestions = []

        logger.info("Running proactive suggestion detection...")

        # Run detectors
        all_suggestions.extend(self.detect_follow_ups())
        all_suggestions.extend(self.detect_incomplete_task_chains())
        all_suggestions.extend(self.detect_recurring_patterns())
        all_suggestions.extend(self.detect_stale_relationships())

        logger.info(f"Detected {len(all_suggestions)} proactive suggestions")

        return all_suggestions

    def create_suggestion(self, suggestion: ProactiveSuggestion) -> Path:
        """
        Create suggestion file in /Needs_Action/ directory.

        Args:
            suggestion: Suggestion instance to create

        Returns:
            Path: Path to created suggestion file
        """
        filename = suggestion.get_filename()
        file_path = self.needs_action_dir / filename

        # Generate markdown body
        body = suggestion.to_markdown_body()

        # Save to file
        suggestion.save_to_file(file_path, body=body)

        logger.info(f"Created suggestion: {file_path}")

        return file_path

    def process_feedback(
        self,
        suggestion_id: str,
        response: Literal["accepted", "rejected", "modified"],
        feedback: Optional[str] = None
    ):
        """
        Process user feedback on a suggestion for learning.

        Args:
            suggestion_id: Suggestion ID
            response: User response (accepted, rejected, modified)
            feedback: Optional feedback text
        """
        # Find suggestion file
        suggestion_file = self.needs_action_dir / f"{suggestion_id}.md"

        if not suggestion_file.exists():
            logger.warning(f"Suggestion file not found: {suggestion_file}")
            return

        try:
            # Load suggestion
            suggestion, _ = ProactiveSuggestion.load_from_file(suggestion_file)

            # Update feedback in model
            if response == "accepted":
                suggestion.mark_accepted(feedback)
            elif response == "rejected":
                suggestion.mark_rejected(feedback)
            elif response == "modified":
                suggestion.mark_modified(feedback)

            # Save updated suggestion
            body = suggestion.to_markdown_body()
            suggestion.save_to_file(suggestion_file, body=body)

            # Record feedback for learning
            context_keywords = [word.lower() for word in suggestion.context.split() if len(word) > 4]

            feedback_entry = {
                "suggestion_id": suggestion_id,
                "category": suggestion.category,
                "response": response,
                "confidence": suggestion.confidence_score,
                "context_keywords": context_keywords[:10],  # Limit to 10 keywords
                "timestamp": datetime.now().isoformat(),
                "feedback_text": feedback
            }

            self.feedback_history[suggestion.category].append(feedback_entry)

            # Save feedback history
            self._save_feedback_history()

            logger.info(f"Processed feedback for {suggestion_id}: {response}")

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")


def run_suggestion_engine(vault_path: str | Path):
    """
    Standalone function to run suggestion engine (for scheduled tasks).

    Args:
        vault_path: Path to vault root
    """
    engine = SuggestionEngine(vault_path)

    # Run detection
    suggestions = engine.run_detection()

    # Create suggestion files
    for suggestion in suggestions:
        engine.create_suggestion(suggestion)

    logger.info(f"Suggestion engine complete: {len(suggestions)} suggestions created")


if __name__ == "__main__":
    # Test runner
    import sys

    if len(sys.argv) < 2:
        print("Usage: python suggestion_engine.py <vault_path>")
        sys.exit(1)

    vault_path = sys.argv[1]
    run_suggestion_engine(vault_path)
