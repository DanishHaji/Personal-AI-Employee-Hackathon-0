"""
TrustEvaluator Service for Personal AI Employee - Gold Tier US1

Evaluates whether actions can be auto-approved based on configured trust rules.
Core of the trust framework that reduces HITL approval friction.

Workflow:
1. Load trust rules from Company_Handbook.md
2. Match action plan against enabled rules
3. Return auto-approval decision + rule_id
4. Track usage and effectiveness
5. Auto-disable rules if effectiveness < 0.80

Usage:
    trust_evaluator = TrustEvaluator(vault_path="/path/to/vault")

    # Evaluate action plan
    is_trusted, rule_id = trust_evaluator.evaluate(plan_frontmatter)

    # Update effectiveness based on feedback
    trust_evaluator.update_rule_effectiveness(rule_id, user_would_approve=True)

    # Reload rules after manual edits
    trust_evaluator.reload_rules()
"""

import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from src.models.trust_rule import TrustRule

logger = logging.getLogger(__name__)


class TrustEvaluator:
    """
    Trust framework evaluator service.

    Loads trust rules from Company_Handbook.md and evaluates action plans
    against them to determine if auto-approval is allowed.
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize TrustEvaluator.

        Args:
            vault_path: Absolute path to Obsidian vault
        """
        self.vault_path = Path(vault_path).resolve()
        self.handbook_path = self.vault_path / "Company_Handbook.md"

        # Cache of loaded trust rules
        self._rules: List[TrustRule] = []
        self._rules_by_id: Dict[str, TrustRule] = {}

        # Load rules on initialization
        self.reload_rules()

        logger.info(f"TrustEvaluator initialized with {len(self._rules)} rules")

    def reload_rules(self):
        """
        Reload trust rules from Company_Handbook.md.

        Call this after manual edits to the handbook or when rules are updated
        programmatically.
        """
        try:
            self._rules = self._load_rules_from_handbook()
            self._rules_by_id = {rule.rule_id: rule for rule in self._rules}
            logger.info(f"Loaded {len(self._rules)} trust rules from handbook")
        except Exception as e:
            logger.error(f"Failed to load trust rules: {e}")
            # Keep existing rules on failure
            if not self._rules:
                self._rules = []
                self._rules_by_id = {}

    def _load_rules_from_handbook(self) -> List[TrustRule]:
        """
        Load trust rules from Company_Handbook.md YAML frontmatter.

        Returns:
            List[TrustRule]: Parsed trust rules

        Raises:
            IOError: If handbook file not found
            ValueError: If YAML parsing fails
        """
        if not self.handbook_path.exists():
            logger.warning(f"Company Handbook not found: {self.handbook_path}")
            return []

        # Read handbook file
        with open(self.handbook_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse YAML frontmatter
        if not content.startswith('---'):
            raise ValueError("Company Handbook missing YAML frontmatter")

        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError("Company Handbook has invalid frontmatter format")

        frontmatter_yaml = parts[1]
        frontmatter = yaml.safe_load(frontmatter_yaml)

        # Extract trust_rules section
        trust_rules_data = frontmatter.get('trust_rules', [])

        if not isinstance(trust_rules_data, list):
            logger.warning("trust_rules is not a list in Company Handbook")
            return []

        # Parse each rule into TrustRule object
        rules = []
        for rule_data in trust_rules_data:
            try:
                # Convert ISO strings to datetime objects
                if 'created_at' in rule_data and isinstance(rule_data['created_at'], str):
                    rule_data['created_at'] = datetime.fromisoformat(
                        rule_data['created_at'].replace('Z', '+00:00')
                    )
                if 'last_used' in rule_data and isinstance(rule_data['last_used'], str):
                    rule_data['last_used'] = datetime.fromisoformat(
                        rule_data['last_used'].replace('Z', '+00:00')
                    )

                # Create TrustRule instance
                rule = TrustRule(**rule_data)

                # Validate rule
                rule.validate()

                rules.append(rule)

            except Exception as e:
                logger.error(f"Failed to parse trust rule {rule_data.get('rule_id', 'unknown')}: {e}")
                continue

        return rules

    def evaluate(self, plan_frontmatter: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Evaluate whether an action plan can be auto-approved.

        Args:
            plan_frontmatter: Plan frontmatter dict containing:
                - type: Action type (email_send, social_post, etc.)
                - target: Contact (email, phone number)
                - content or body: Content to match against
                - amount: Financial amount (for expense_record)

        Returns:
            Tuple[bool, Optional[str]]: (is_trusted, rule_id or None)
                - is_trusted: True if action should be auto-approved
                - rule_id: ID of matching rule (None if no match)
        """
        action_type = plan_frontmatter.get('type', '').lower()

        if not action_type:
            logger.warning("Plan missing 'type' field, cannot evaluate trust")
            return (False, None)

        # Get enabled rules for this action type
        matching_rules = self._get_matching_rules(action_type)

        if not matching_rules:
            logger.debug(f"No enabled trust rules for action_type: {action_type}")
            return (False, None)

        # Evaluate each rule
        for rule in matching_rules:
            if self._rule_matches_plan(rule, plan_frontmatter):
                # Record usage
                rule.record_usage()
                self._save_rules_to_handbook()

                logger.info(
                    f"Trust rule matched: {rule.rule_id} for {action_type}"
                )
                return (True, rule.rule_id)

        # No matching rules
        logger.debug(f"No trust rules matched for {action_type}")
        return (False, None)

    def _get_matching_rules(self, action_type: str) -> List[TrustRule]:
        """
        Get enabled trust rules for a specific action type, sorted by specificity.

        More specific rules (with more filters) are returned first to ensure
        the most specific matching rule is used.

        Args:
            action_type: Action type to match

        Returns:
            List[TrustRule]: Enabled rules matching action type, sorted by specificity
        """
        matching = [
            rule for rule in self._rules
            if rule.enabled and rule.action_type == action_type
        ]

        # Sort by specificity (most specific first)
        # Rules with more filters are more specific
        def specificity_score(rule: TrustRule) -> int:
            score = 0
            if rule.content_pattern:
                score += 10  # Content pattern is highly specific
            if rule.time_pattern:
                score += 5   # Time pattern is moderately specific
            if rule.max_value is not None:
                score += 5   # Value limit is moderately specific
            if rule.contact_filter:
                score += 1   # Contact filter is baseline specificity
            return score

        matching.sort(key=specificity_score, reverse=True)
        return matching

    def _rule_matches_plan(self, rule: TrustRule, plan: Dict[str, Any]) -> bool:
        """
        Check if a trust rule matches a plan.

        Args:
            rule: TrustRule to evaluate
            plan: Plan frontmatter dict

        Returns:
            bool: True if rule matches all filters
        """
        # Extract plan details
        target = plan.get('target', '')
        content = plan.get('content') or plan.get('body', '')
        amount = plan.get('amount')

        # Check contact filter
        if not rule.matches_contact(target):
            return False

        # Check content pattern
        if not rule.matches_content(content):
            return False

        # Check time pattern
        if not rule.matches_time():
            return False

        # Check value limit
        if not rule.matches_value(amount):
            return False

        # All filters match
        return True

    def update_rule_effectiveness(
        self,
        rule_id: str,
        user_would_approve: bool
    ) -> bool:
        """
        Update trust rule effectiveness based on user feedback.

        Args:
            rule_id: Trust rule ID
            user_would_approve: Whether user would have approved this action

        Returns:
            bool: True if rule still enabled, False if auto-disabled
        """
        rule = self._rules_by_id.get(rule_id)

        if not rule:
            logger.warning(f"Trust rule not found for effectiveness update: {rule_id}")
            return False

        # Update effectiveness score
        rule.update_effectiveness(user_would_approve)

        # Save updated rules
        self._save_rules_to_handbook()

        logger.info(
            f"Updated trust rule effectiveness: {rule_id} -> {rule.effectiveness_score:.3f} "
            f"(enabled: {rule.enabled})"
        )

        return rule.enabled

    def _save_rules_to_handbook(self):
        """
        Save trust rules back to Company_Handbook.md.

        Updates the trust_rules section in YAML frontmatter while preserving
        the rest of the handbook content.
        """
        try:
            # Read current handbook
            with open(self.handbook_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter
            parts = content.split('---', 2)
            if len(parts) < 3:
                logger.error("Cannot save rules: invalid handbook format")
                return

            frontmatter_yaml = parts[1]
            body = parts[2]

            frontmatter = yaml.safe_load(frontmatter_yaml)

            # Update trust_rules section
            frontmatter['trust_rules'] = [
                rule.to_frontmatter() for rule in self._rules
            ]

            # Regenerate YAML
            updated_yaml = yaml.dump(
                frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )

            # Write updated handbook
            updated_content = f"---\n{updated_yaml}---{body}"

            with open(self.handbook_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            logger.debug("Saved updated trust rules to handbook")

        except Exception as e:
            logger.error(f"Failed to save trust rules to handbook: {e}")

    def add_rule(self, rule: TrustRule) -> bool:
        """
        Add a new trust rule.

        Args:
            rule: TrustRule to add

        Returns:
            bool: True if added successfully

        Raises:
            ValueError: If rule_id already exists
        """
        # Validate rule
        rule.validate()

        # Check for duplicate rule_id
        if rule.rule_id in self._rules_by_id:
            raise ValueError(f"Trust rule already exists: {rule.rule_id}")

        # Add to collections
        self._rules.append(rule)
        self._rules_by_id[rule.rule_id] = rule

        # Save to handbook
        self._save_rules_to_handbook()

        logger.info(f"Added trust rule: {rule.rule_id}")
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a trust rule.

        Args:
            rule_id: Trust rule ID to remove

        Returns:
            bool: True if removed successfully
        """
        rule = self._rules_by_id.get(rule_id)

        if not rule:
            logger.warning(f"Trust rule not found for removal: {rule_id}")
            return False

        # Remove from collections
        self._rules.remove(rule)
        del self._rules_by_id[rule_id]

        # Save to handbook
        self._save_rules_to_handbook()

        logger.info(f"Removed trust rule: {rule_id}")
        return True

    def enable_rule(self, rule_id: str) -> bool:
        """
        Enable a trust rule.

        Args:
            rule_id: Trust rule ID to enable

        Returns:
            bool: True if enabled successfully
        """
        rule = self._rules_by_id.get(rule_id)

        if not rule:
            logger.warning(f"Trust rule not found: {rule_id}")
            return False

        rule.enabled = True
        self._save_rules_to_handbook()

        logger.info(f"Enabled trust rule: {rule_id}")
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """
        Disable a trust rule.

        Args:
            rule_id: Trust rule ID to disable

        Returns:
            bool: True if disabled successfully
        """
        rule = self._rules_by_id.get(rule_id)

        if not rule:
            logger.warning(f"Trust rule not found: {rule_id}")
            return False

        rule.enabled = False
        self._save_rules_to_handbook()

        logger.info(f"Disabled trust rule: {rule_id}")
        return True

    def get_rule(self, rule_id: str) -> Optional[TrustRule]:
        """
        Get a trust rule by ID.

        Args:
            rule_id: Trust rule ID

        Returns:
            Optional[TrustRule]: Trust rule or None if not found
        """
        return self._rules_by_id.get(rule_id)

    def get_all_rules(self) -> List[TrustRule]:
        """
        Get all trust rules.

        Returns:
            List[TrustRule]: All trust rules
        """
        return self._rules.copy()

    def get_enabled_rules(self) -> List[TrustRule]:
        """
        Get enabled trust rules.

        Returns:
            List[TrustRule]: Enabled trust rules
        """
        return [rule for rule in self._rules if rule.enabled]

    def get_rules_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about trust rules.

        Returns:
            Dict: Summary statistics
        """
        total = len(self._rules)
        enabled = len(self.get_enabled_rules())
        disabled = total - enabled

        # Count by action type
        by_action_type = {}
        for rule in self._rules:
            action_type = rule.action_type
            if action_type not in by_action_type:
                by_action_type[action_type] = {'total': 0, 'enabled': 0}
            by_action_type[action_type]['total'] += 1
            if rule.enabled:
                by_action_type[action_type]['enabled'] += 1

        # Calculate average effectiveness
        effectiveness_scores = [r.effectiveness_score for r in self._rules if r.usage_count > 0]
        avg_effectiveness = (
            sum(effectiveness_scores) / len(effectiveness_scores)
            if effectiveness_scores else 1.0
        )

        return {
            'total_rules': total,
            'enabled_rules': enabled,
            'disabled_rules': disabled,
            'by_action_type': by_action_type,
            'avg_effectiveness_score': avg_effectiveness,
            'total_usage_count': sum(r.usage_count for r in self._rules)
        }


# Singleton instance for application-wide use
_trust_evaluator_instance: Optional[TrustEvaluator] = None


def get_trust_evaluator(vault_path: Optional[str | Path] = None) -> TrustEvaluator:
    """
    Get singleton TrustEvaluator instance.

    Args:
        vault_path: Vault path (required for first call)

    Returns:
        TrustEvaluator: Shared trust evaluator instance
    """
    global _trust_evaluator_instance

    if _trust_evaluator_instance is None:
        if vault_path is None:
            raise ValueError("vault_path required for first TrustEvaluator initialization")
        _trust_evaluator_instance = TrustEvaluator(vault_path)

    return _trust_evaluator_instance
