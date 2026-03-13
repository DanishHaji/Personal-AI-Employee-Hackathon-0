"""
ClaimManager for Personal AI Employee - Platinum Tier

Handles task claim management for Cloud-Local work-zone specialization.

Core functionality:
- Advisory file-based locks for task ownership
- Work-zone routing (Cloud vs Local capabilities)
- Task delegation between zones
- Claim expiry management (15-minute TTL)

Constitutional Compliance:
- Local-First Privacy (Principle I): Secrets never leave local zone
- Security & Credential Management (Principle III): All claims logged
"""

import os
import fnmatch
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import yaml
import json


# Custom Exceptions
class TaskAlreadyClaimedError(Exception):
    """Task is claimed by another zone."""
    def __init__(self, task_id: str, claimed_by: str, expires_at: datetime):
        self.task_id = task_id
        self.claimed_by = claimed_by
        self.expires_at = expires_at
        super().__init__(f"Task {task_id} already claimed by {claimed_by} until {expires_at}")


class TaskNotFoundError(Exception):
    """Task file doesn't exist."""
    pass


class InvalidZoneError(Exception):
    """Zone is not 'cloud' or 'local'."""
    pass


class ClaimNotFoundError(Exception):
    """Claim ID not found."""
    pass


class UnauthorizedReleaseError(Exception):
    """Zone doesn't own the claim."""
    pass


@dataclass
class Claim:
    """Represents a task claim (advisory lock)."""

    claim_id: str
    task_id: str
    task_file: str
    claimed_by: str  # "cloud" or "local"
    claimed_at: str  # ISO format datetime
    expires_at: str  # ISO format datetime (claimed_at + 15 minutes)
    zone: str  # "cloud" or "local"
    action_type: str
    status: str = "active"  # "active", "released", "expired", "violated"
    released_at: Optional[str] = None
    released_by: Optional[str] = None


@dataclass
class RoutingRule:
    """Routing rule for work-zone delegation."""

    pattern: str  # e.g., "EMAIL_*", "WHATSAPP_*"
    action: str  # e.g., "reply_draft", "send_message"
    zone: str  # "cloud", "local", "any"
    requires_approval: bool


class ClaimManager:
    """Service for task claim management and work-zone routing."""

    def __init__(
        self,
        vault_path: str | Path,
        instance: str = "local",
        claim_ttl_minutes: int = 15
    ):
        """
        Initialize ClaimManager.

        Args:
            vault_path: Path to vault root
            instance: Instance identifier ("cloud" or "local")
            claim_ttl_minutes: Claim time-to-live in minutes (default: 15)
        """
        self.vault_path = Path(vault_path).resolve()
        self.instance = instance
        self.claim_ttl_minutes = claim_ttl_minutes
        self.logger = logging.getLogger(f"claim_manager.{instance}")

        # Validate vault path
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")

        # Ensure required directories exist
        self.claims_dir = self.vault_path / "Claims"
        self.claims_dir.mkdir(exist_ok=True)

        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.needs_local_dir = self.vault_path / "Needs_Local"
        self.cloud_drafts_dir = self.vault_path / "Cloud_Drafts"

        # Create directories if they don't exist
        for dir_path in [self.needs_action_dir, self.needs_local_dir, self.cloud_drafts_dir]:
            dir_path.mkdir(exist_ok=True)

        # Log directory
        self.logs_dir = self.vault_path / "Logs"
        self.logs_dir.mkdir(exist_ok=True)
        self.claim_log_path = self.logs_dir / "claims.jsonl"

        # Load routing rules from Company_Handbook.md
        self.routing_rules = self._load_routing_rules()

        self.logger.info(f"ClaimManager initialized: vault={self.vault_path}, instance={self.instance}")

    def claim_task(self, task_id: str, zone: str, task_file: str = "", action_type: str = "") -> Claim:
        """
        Claim ownership of a task for the specified work zone.

        Args:
            task_id: Task identifier (e.g., "EMAIL_20260304_152150")
            zone: Work zone claiming the task ("cloud" or "local")
            task_file: Path to task file (relative to vault)
            action_type: Type of action (e.g., "email_reply")

        Returns:
            Claim object

        Raises:
            TaskAlreadyClaimedError: Task claimed by another zone
            InvalidZoneError: Zone is not "cloud" or "local"
        """
        # Validate zone
        if zone not in ["cloud", "local"]:
            raise InvalidZoneError(f"Invalid zone: {zone}. Must be 'cloud' or 'local'")

        # Check existing claim
        existing_claim = self.check_claim(task_id)

        if existing_claim:
            # If claimed by same zone, return existing claim
            if existing_claim.claimed_by == zone:
                self.logger.debug(f"Task {task_id} already claimed by {zone}, returning existing claim")
                return existing_claim

            # Conflict resolution (Platinum Tier US4 T127-T128)
            # If claimed by different zone, check for simultaneous claim conflict
            conflict_resolved = self._resolve_claim_conflict(task_id, zone, existing_claim)

            if conflict_resolved:
                # Current zone won conflict resolution
                self.logger.info(f"Claim conflict resolved in favor of {zone} for task {task_id}")
                # existing_claim was updated to release, continue to create new claim
            else:
                # Existing claim wins, raise error
                expires_at = datetime.fromisoformat(existing_claim.expires_at)
                raise TaskAlreadyClaimedError(task_id, existing_claim.claimed_by, expires_at)

        # Create new claim
        claim_id = f"CLAIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task_id}"
        claimed_at = datetime.now()
        expires_at = claimed_at + timedelta(minutes=self.claim_ttl_minutes)

        claim = Claim(
            claim_id=claim_id,
            task_id=task_id,
            task_file=task_file,
            claimed_by=zone,
            claimed_at=claimed_at.isoformat(),
            expires_at=expires_at.isoformat(),
            zone=zone,
            action_type=action_type,
            status="active"
        )

        # Write claim file
        self._write_claim_file(claim)

        # Log claim event
        self._log_claim_event({
            "event": "claim_created",
            "claim_id": claim_id,
            "task_id": task_id,
            "claimed_by": zone,
            "expires_at": expires_at.isoformat(),
            "timestamp": datetime.now().isoformat()
        })

        self.logger.info(f"Task claimed: {task_id} by {zone}, expires at {expires_at.isoformat()}")

        return claim

    def release_claim(self, claim_id: str, zone: str) -> None:
        """
        Release a task claim when processing is complete.

        Args:
            claim_id: Claim identifier
            zone: Work zone releasing the claim (must match claim owner)

        Raises:
            ClaimNotFoundError: Invalid claim ID
            UnauthorizedReleaseError: Zone doesn't own the claim
        """
        # Load claim
        claim = self._load_claim(claim_id)

        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")

        # Verify zone owns the claim
        if claim.claimed_by != zone:
            raise UnauthorizedReleaseError(
                f"Zone {zone} cannot release claim owned by {claim.claimed_by}"
            )

        # Update claim status
        claim.status = "released"
        claim.released_at = datetime.now().isoformat()
        claim.released_by = zone

        # Log release event
        self._log_claim_event({
            "event": "claim_released",
            "claim_id": claim_id,
            "task_id": claim.task_id,
            "released_by": zone,
            "timestamp": datetime.now().isoformat()
        })

        # Delete claim file (released claims not persisted)
        claim_file = self.claims_dir / f"{claim.task_id}.claim.md"
        if claim_file.exists():
            claim_file.unlink()

        self.logger.info(f"Claim released: {claim_id} by {zone}")

    def check_claim(self, task_id: str) -> Optional[Claim]:
        """
        Check if a task is currently claimed.

        Args:
            task_id: Task identifier

        Returns:
            Claim object if claimed and not expired, None otherwise
        """
        claim_file = self.claims_dir / f"{task_id}.claim.md"

        if not claim_file.exists():
            return None

        # Load claim
        try:
            with open(claim_file, "r") as f:
                content = f.read()

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    frontmatter = yaml.safe_load(parts[1])
                    claim = Claim(**frontmatter)

                    # Check if expired
                    expires_at = datetime.fromisoformat(claim.expires_at)
                    if datetime.now() > expires_at:
                        # Auto-expire
                        self._expire_claim(claim)
                        return None

                    return claim

        except Exception as e:
            self.logger.error(f"Failed to load claim {task_id}: {e}")

        return None

    def auto_expire_claims(self) -> int:
        """
        Background task to expire stale claims (TTL exceeded).

        Returns:
            Number of claims expired
        """
        expired_count = 0

        # Scan all claim files
        for claim_file in self.claims_dir.glob("*.claim.md"):
            try:
                with open(claim_file, "r") as f:
                    content = f.read()

                # Parse YAML frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        claim = Claim(**frontmatter)

                        # Check if expired
                        expires_at = datetime.fromisoformat(claim.expires_at)
                        if datetime.now() > expires_at:
                            self._expire_claim(claim)
                            expired_count += 1

            except Exception as e:
                self.logger.error(f"Failed to check claim {claim_file.name}: {e}")

        if expired_count > 0:
            self.logger.info(f"Expired {expired_count} stale claims")

        return expired_count

    def route_task(self, task_id: str, task_file: str, action_type: str) -> str:
        """
        Determine which work zone should process a task based on routing rules.

        Args:
            task_id: Task identifier
            task_file: Path to task file in vault
            action_type: Type of action (e.g., "email_reply", "whatsapp_send")

        Returns:
            Work zone - "cloud", "local", or "any"
        """
        # Match against routing rules
        for rule in self.routing_rules:
            # Check if task_id matches pattern
            if fnmatch.fnmatch(task_id, rule.pattern):
                # Check if action matches
                if rule.action == action_type or rule.action == "*":
                    self.logger.debug(
                        f"Task {task_id} routed to {rule.zone} (pattern={rule.pattern}, action={action_type})"
                    )
                    return rule.zone

        # Default: any zone can process
        self.logger.debug(f"Task {task_id} can be processed by any zone (no matching rule)")
        return "any"

    def delegate_to_local(self, task_id: str, reason: str, task_file: Optional[str] = None) -> None:
        """
        Delegate a task from Cloud to Local zone (requires local-only capabilities).

        Args:
            task_id: Task identifier
            reason: Reason for delegation (e.g., "whatsapp_session_required")
            task_file: Optional specific task file path
        """
        # Find task file
        if not task_file:
            task_file = self.needs_action_dir / f"{task_id}.md"
        else:
            task_file = self.vault_path / task_file

        if not task_file.exists():
            raise TaskNotFoundError(f"Task file not found: {task_file}")

        # Read task file
        with open(task_file, "r") as f:
            content = f.read()

        # Parse and update YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2]

                # Add delegation metadata
                frontmatter["delegation"] = {
                    "created_by": self.instance,
                    "requires_zone": "local",
                    "delegated_at": datetime.now().isoformat(),
                    "reason": reason
                }

                # Write updated content
                new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---{body}"

                # Move to Needs_Local/
                new_file = self.needs_local_dir / task_file.name

                with open(new_file, "w") as f:
                    f.write(new_content)

                # Delete original file
                task_file.unlink()

                # Log delegation
                self._log_claim_event({
                    "event": "task_delegated",
                    "task_id": task_id,
                    "delegated_by": self.instance,
                    "delegated_to": "local",
                    "reason": reason,
                    "timestamp": datetime.now().isoformat()
                })

                self.logger.info(f"Task delegated to local: {task_id}, reason={reason}")

    def _resolve_claim_conflict(
        self,
        task_id: str,
        requesting_zone: str,
        existing_claim: Claim
    ) -> bool:
        """
        Resolve simultaneous claim conflict using earliest timestamp wins strategy.

        Platinum Tier US4 T127-T128: Conflict resolution for simultaneous claims.

        Args:
            task_id: Task being claimed
            requesting_zone: Zone requesting the claim
            existing_claim: Existing claim from other zone

        Returns:
            bool: True if requesting zone wins (existing claim should be released),
                  False if existing claim wins (request should be denied)
        """
        # Create temporary claim for comparison
        requesting_timestamp = datetime.now()

        # Parse existing claim timestamp
        existing_timestamp = datetime.fromisoformat(existing_claim.claimed_at)

        # Calculate time difference in seconds
        time_diff = abs((requesting_timestamp - existing_timestamp).total_seconds())

        # If claims are within 5 seconds of each other, it's a simultaneous conflict
        SIMULTANEITY_THRESHOLD_SECONDS = 5

        if time_diff <= SIMULTANEITY_THRESHOLD_SECONDS:
            self.logger.warning(
                f"Simultaneous claim conflict detected for task {task_id}: "
                f"{requesting_zone} vs {existing_claim.claimed_by} "
                f"(time diff: {time_diff:.2f}s)"
            )

            # Strategy: Earliest timestamp wins (T128)
            if requesting_timestamp < existing_timestamp:
                # Requesting zone wins - force release existing claim
                self.logger.info(
                    f"Conflict resolution: {requesting_zone} wins (earlier timestamp) "
                    f"for task {task_id}"
                )

                # Update existing claim to released
                existing_claim.status = "conflict_resolved"
                existing_claim.released_at = datetime.now().isoformat()
                existing_claim.released_by = "system_conflict_resolution"

                # Write updated claim
                self._write_claim_file(existing_claim)

                # Log conflict resolution
                self._log_claim_event({
                    "event": "claim_conflict_resolved",
                    "task_id": task_id,
                    "winner": requesting_zone,
                    "loser": existing_claim.claimed_by,
                    "resolution_strategy": "earliest_timestamp_wins",
                    "time_diff_seconds": time_diff,
                    "requesting_timestamp": requesting_timestamp.isoformat(),
                    "existing_timestamp": existing_timestamp,
                    "timestamp": datetime.now().isoformat()
                })

                return True  # Requesting zone wins

            else:
                # Existing claim wins - deny request
                self.logger.info(
                    f"Conflict resolution: {existing_claim.claimed_by} wins (earlier timestamp) "
                    f"for task {task_id}"
                )

                # Log conflict resolution
                self._log_claim_event({
                    "event": "claim_conflict_resolved",
                    "task_id": task_id,
                    "winner": existing_claim.claimed_by,
                    "loser": requesting_zone,
                    "resolution_strategy": "earliest_timestamp_wins",
                    "time_diff_seconds": time_diff,
                    "requesting_timestamp": requesting_timestamp.isoformat(),
                    "existing_timestamp": existing_timestamp,
                    "timestamp": datetime.now().isoformat()
                })

                return False  # Existing claim wins

        else:
            # Not a simultaneous conflict - existing claim is clearly first
            return False

    def _write_claim_file(self, claim: Claim) -> None:
        """Write claim to file in Claims/ directory."""
        claim_file = self.claims_dir / f"{claim.task_id}.claim.md"

        content = f"""---
{yaml.dump(asdict(claim), default_flow_style=False)}---

# Claim: {claim.task_id}

This task is currently claimed by the **{claim.claimed_by}** instance.

- **Claim ID**: {claim.claim_id}
- **Claimed At**: {claim.claimed_at}
- **Expires At**: {claim.expires_at}
- **Action Type**: {claim.action_type}
- **Status**: {claim.status}

**Note**: This is an advisory lock. The claim will expire automatically after {self.claim_ttl_minutes} minutes.
"""

        with open(claim_file, "w") as f:
            f.write(content)

    def _load_claim(self, claim_id: str) -> Optional[Claim]:
        """Load claim by claim_id from Claims/ directory."""
        # Search for claim file with matching claim_id
        for claim_file in self.claims_dir.glob("*.claim.md"):
            try:
                with open(claim_file, "r") as f:
                    content = f.read()

                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        if frontmatter.get("claim_id") == claim_id:
                            return Claim(**frontmatter)

            except Exception as e:
                self.logger.error(f"Failed to load claim from {claim_file.name}: {e}")

        return None

    def _expire_claim(self, claim: Claim) -> None:
        """Expire a claim and delete its file."""
        claim.status = "expired"

        # Log expiry
        self._log_claim_event({
            "event": "claim_expired",
            "claim_id": claim.claim_id,
            "task_id": claim.task_id,
            "claimed_by": claim.claimed_by,
            "timestamp": datetime.now().isoformat()
        })

        # Delete claim file
        claim_file = self.claims_dir / f"{claim.task_id}.claim.md"
        if claim_file.exists():
            claim_file.unlink()

        self.logger.debug(f"Claim expired: {claim.claim_id}")

    def _log_claim_event(self, event: Dict[str, Any]) -> None:
        """Log claim event to claims.jsonl."""
        try:
            with open(self.claim_log_path, "a") as f:
                json.dump(event, f)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to log claim event: {e}")

    def _load_routing_rules(self) -> List[RoutingRule]:
        """Load routing rules from Company_Handbook.md."""
        handbook_path = self.vault_path / "Company_Handbook.md"

        if not handbook_path.exists():
            self.logger.warning("Company_Handbook.md not found, using default rules")
            return self._get_default_routing_rules()

        try:
            with open(handbook_path, "r") as f:
                content = f.read()

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    frontmatter = yaml.safe_load(parts[1])

                    # Extract routing_rules
                    rules_data = frontmatter.get("routing_rules", [])

                    rules = []
                    for rule_data in rules_data:
                        rules.append(RoutingRule(
                            pattern=rule_data["pattern"],
                            action=rule_data["action"],
                            zone=rule_data["zone"],
                            requires_approval=rule_data["requires_approval"]
                        ))

                    self.logger.info(f"Loaded {len(rules)} routing rules from Company_Handbook.md")
                    return rules

        except Exception as e:
            self.logger.error(f"Failed to load routing rules: {e}")

        return self._get_default_routing_rules()

    def _get_default_routing_rules(self) -> List[RoutingRule]:
        """Get default routing rules if Company_Handbook.md unavailable."""
        return [
            RoutingRule(pattern="EMAIL_*", action="reply_draft", zone="cloud", requires_approval=True),
            RoutingRule(pattern="EMAIL_*", action="send", zone="local", requires_approval=False),
            RoutingRule(pattern="WHATSAPP_*", action="send_message", zone="local", requires_approval=False),
            RoutingRule(pattern="SOCIAL_*", action="draft_post", zone="cloud", requires_approval=True),
            RoutingRule(pattern="SOCIAL_*", action="publish", zone="local", requires_approval=False),
            RoutingRule(pattern="PAYMENT_*", action="execute", zone="local", requires_approval=True),
        ]


# CLI Interface for manual claim operations
if __name__ == "__main__":
    import argparse
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Claim Manager - Task claim management and work-zone routing")
    parser.add_argument(
        "command",
        choices=["claim", "release", "check", "expire", "route", "delegate"],
        help="Command to execute"
    )
    parser.add_argument("--task-id", help="Task identifier")
    parser.add_argument("--claim-id", help="Claim identifier")
    parser.add_argument("--zone", default="local", help="Work zone (cloud or local)")
    parser.add_argument("--action-type", help="Action type for routing")
    parser.add_argument("--reason", help="Delegation reason")
    parser.add_argument("--vault-path", default=".", help="Path to vault directory")

    args = parser.parse_args()

    # Initialize service
    try:
        service = ClaimManager(vault_path=args.vault_path, instance=args.zone)

        if args.command == "claim":
            if not args.task_id:
                print("Error: --task-id required for claim command")
                sys.exit(1)

            try:
                claim = service.claim_task(
                    task_id=args.task_id,
                    zone=args.zone,
                    action_type=args.action_type or ""
                )
                print(f"\nTask claimed: {claim.task_id}")
                print(f"  Claim ID: {claim.claim_id}")
                print(f"  Claimed by: {claim.claimed_by}")
                print(f"  Expires at: {claim.expires_at}")
                sys.exit(0)

            except TaskAlreadyClaimedError as e:
                print(f"\nError: {str(e)}")
                sys.exit(1)

        elif args.command == "release":
            if not args.claim_id:
                print("Error: --claim-id required for release command")
                sys.exit(1)

            service.release_claim(claim_id=args.claim_id, zone=args.zone)
            print(f"\nClaim released: {args.claim_id}")
            sys.exit(0)

        elif args.command == "check":
            if not args.task_id:
                print("Error: --task-id required for check command")
                sys.exit(1)

            claim = service.check_claim(task_id=args.task_id)
            if claim:
                print(f"\nTask claimed:")
                print(f"  Claim ID: {claim.claim_id}")
                print(f"  Claimed by: {claim.claimed_by}")
                print(f"  Expires at: {claim.expires_at}")
                print(f"  Status: {claim.status}")
            else:
                print(f"\nTask unclaimed: {args.task_id}")
            sys.exit(0)

        elif args.command == "expire":
            expired = service.auto_expire_claims()
            print(f"\nExpired {expired} stale claims")
            sys.exit(0)

        elif args.command == "route":
            if not args.task_id or not args.action_type:
                print("Error: --task-id and --action-type required for route command")
                sys.exit(1)

            zone = service.route_task(
                task_id=args.task_id,
                task_file="",
                action_type=args.action_type
            )
            print(f"\nTask should be routed to: {zone}")
            sys.exit(0)

        elif args.command == "delegate":
            if not args.task_id or not args.reason:
                print("Error: --task-id and --reason required for delegate command")
                sys.exit(1)

            service.delegate_to_local(task_id=args.task_id, reason=args.reason)
            print(f"\nTask delegated to local: {args.task_id}")
            sys.exit(0)

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)
