#!/usr/bin/env python3
"""
Rate Limiter - Token Bucket Algorithm for Silver Tier

Implements token bucket rate limiting with persistent JSON state to respect API quotas
for Gmail, LinkedIn, Facebook, Twitter, and WhatsApp integrations.

Token Bucket Algorithm:
- Bucket has max capacity (tokens_per_day)
- Tokens refill at constant rate (tokens_per_second)
- Each action consumes 1 token
- If no tokens available, action is blocked

Advantages over fixed window:
- Allows short bursts (use all tokens at once if available)
- Prevents quota exhaustion over long periods
- Smooth rate limiting without sudden resets
"""

import os
import json
import time
import logging
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum


logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms with rate limits."""
    GMAIL = "gmail"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    WHATSAPP = "whatsapp"


# Platform rate limits (per day)
PLATFORM_LIMITS = {
    Platform.GMAIL: 500,      # Gmail API: 500 emails/day
    Platform.LINKEDIN: 100,    # LinkedIn: 100 posts/day
    Platform.FACEBOOK: 200,    # Facebook: 200 posts/day
    Platform.TWITTER: 2400,    # Twitter: 2400 tweets/day
    Platform.WHATSAPP: 1000    # WhatsApp: 1000 messages/day (inbound monitoring)
}


@dataclass
class TokenBucket:
    """Token bucket state for a single platform."""
    platform: str
    capacity: int  # Max tokens (daily limit)
    tokens: float  # Current available tokens
    refill_rate: float  # Tokens per second
    last_refill: float  # Unix timestamp of last refill
    total_consumed: int  # Total tokens consumed (for stats)
    last_reset: float  # Unix timestamp of last daily reset

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TokenBucket':
        """Create from dictionary."""
        return cls(**data)


class RateLimiter:
    """
    Token bucket rate limiter with persistent JSON state.

    Manages rate limits for multiple platforms simultaneously. Each platform
    has its own token bucket that refills at a constant rate.

    Usage:
        limiter = RateLimiter(state_file="./Logs/rate_limit_state.json")

        # Check if action is allowed
        if limiter.can_perform(Platform.GMAIL):
            # Consume a token
            limiter.consume(Platform.GMAIL)
            # ... send email
        else:
            print("Rate limit exceeded, try again later")

        # Get remaining quota
        remaining = limiter.get_remaining(Platform.GMAIL)
        print(f"Remaining emails today: {remaining}")
    """

    def __init__(self, state_file: str = "./Logs/rate_limit_state.json"):
        """
        Initialize rate limiter.

        Args:
            state_file: Path to JSON file for persisting bucket state
        """
        self.state_file = Path(state_file)
        self.buckets: Dict[Platform, TokenBucket] = {}

        # Load existing state or initialize new buckets
        self._load_state()

        logger.info(
            f"RateLimiter initialized with {len(self.buckets)} buckets "
            f"(state file: {self.state_file})"
        )

    def _initialize_bucket(self, platform: Platform) -> TokenBucket:
        """
        Create a new token bucket for a platform.

        Args:
            platform: Platform to create bucket for

        Returns:
            Initialized TokenBucket
        """
        capacity = PLATFORM_LIMITS[platform]
        refill_rate = capacity / 86400  # Tokens per second (86400 seconds in a day)
        now = time.time()

        return TokenBucket(
            platform=platform.value,
            capacity=capacity,
            tokens=float(capacity),  # Start with full bucket
            refill_rate=refill_rate,
            last_refill=now,
            total_consumed=0,
            last_reset=now
        )

    def _load_state(self):
        """Load bucket state from JSON file."""
        if not self.state_file.exists():
            # No state file - initialize all platforms
            logger.info("No existing state file - initializing fresh buckets")
            for platform in Platform:
                self.buckets[platform] = self._initialize_bucket(platform)
            self._save_state()
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # Load each platform's bucket
            for platform in Platform:
                if platform.value in data:
                    bucket_data = data[platform.value]
                    self.buckets[platform] = TokenBucket.from_dict(bucket_data)
                else:
                    # Platform not in state - initialize new bucket
                    self.buckets[platform] = self._initialize_bucket(platform)

            logger.info(f"Loaded rate limiter state from {self.state_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse state file: {e} - reinitializing")
            for platform in Platform:
                self.buckets[platform] = self._initialize_bucket(platform)

        except Exception as e:
            logger.error(f"Error loading state file: {e} - reinitializing")
            for platform in Platform:
                self.buckets[platform] = self._initialize_bucket(platform)

    def _save_state(self):
        """Persist bucket state to JSON file."""
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert buckets to dictionary
            state_data = {
                platform.value: bucket.to_dict()
                for platform, bucket in self.buckets.items()
            }

            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            logger.debug(f"Saved rate limiter state to {self.state_file}")

        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def _refill_bucket(self, platform: Platform):
        """
        Refill tokens in bucket based on elapsed time.

        Args:
            platform: Platform to refill tokens for
        """
        bucket = self.buckets[platform]
        now = time.time()

        # Calculate elapsed time since last refill
        elapsed = now - bucket.last_refill

        # Calculate tokens to add (refill_rate * elapsed_seconds)
        tokens_to_add = bucket.refill_rate * elapsed

        # Add tokens (capped at capacity)
        bucket.tokens = min(bucket.capacity, bucket.tokens + tokens_to_add)
        bucket.last_refill = now

        # Check if a day has passed (daily reset)
        if now - bucket.last_reset >= 86400:
            logger.info(
                f"{platform.value}: Daily reset - consumed {bucket.total_consumed} "
                f"actions in last 24 hours"
            )
            bucket.total_consumed = 0
            bucket.last_reset = now

    def can_perform(self, platform: Platform) -> bool:
        """
        Check if an action can be performed (at least 1 token available).

        Args:
            platform: Platform to check

        Returns:
            True if action can be performed, False if rate limit exceeded
        """
        self._refill_bucket(platform)
        return self.buckets[platform].tokens >= 1.0

    def consume(self, platform: Platform) -> bool:
        """
        Consume a token for performing an action.

        Args:
            platform: Platform performing action on

        Returns:
            True if token consumed successfully, False if no tokens available
        """
        self._refill_bucket(platform)
        bucket = self.buckets[platform]

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            bucket.total_consumed += 1
            self._save_state()
            logger.debug(
                f"{platform.value}: Token consumed "
                f"({bucket.tokens:.1f}/{bucket.capacity} remaining)"
            )
            return True
        else:
            logger.warning(
                f"{platform.value}: Rate limit exceeded "
                f"({bucket.tokens:.1f}/{bucket.capacity} tokens)"
            )
            return False

    def get_remaining(self, platform: Platform) -> int:
        """
        Get number of remaining actions for platform.

        Args:
            platform: Platform to check

        Returns:
            Number of actions that can be performed before hitting rate limit
        """
        self._refill_bucket(platform)
        return int(self.buckets[platform].tokens)

    def get_wait_time(self, platform: Platform) -> float:
        """
        Get estimated wait time (in seconds) before next action is allowed.

        Args:
            platform: Platform to check

        Returns:
            Seconds to wait, or 0 if action can be performed now
        """
        self._refill_bucket(platform)
        bucket = self.buckets[platform]

        if bucket.tokens >= 1.0:
            return 0.0

        # Calculate time needed to refill 1 token
        tokens_needed = 1.0 - bucket.tokens
        wait_time = tokens_needed / bucket.refill_rate

        return wait_time

    def get_stats(self, platform: Platform) -> Dict:
        """
        Get statistics for a platform.

        Args:
            platform: Platform to get stats for

        Returns:
            Dictionary with rate limit statistics
        """
        self._refill_bucket(platform)
        bucket = self.buckets[platform]

        return {
            "platform": platform.value,
            "capacity": bucket.capacity,
            "tokens_remaining": int(bucket.tokens),
            "refill_rate_per_second": bucket.refill_rate,
            "total_consumed_today": bucket.total_consumed,
            "percentage_used": round((bucket.total_consumed / bucket.capacity) * 100, 1),
            "wait_time_seconds": self.get_wait_time(platform),
            "last_reset": datetime.fromtimestamp(
                bucket.last_reset, tz=timezone.utc
            ).isoformat()
        }

    def reset_bucket(self, platform: Platform):
        """
        Manually reset a bucket to full capacity (for testing/admin).

        Args:
            platform: Platform to reset
        """
        logger.warning(f"Manually resetting rate limit bucket for {platform.value}")
        self.buckets[platform] = self._initialize_bucket(platform)
        self._save_state()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Initialize rate limiter
    limiter = RateLimiter(state_file="./Logs/rate_limit_state.json")

    # Check Gmail quota
    print("\n=== Gmail Rate Limit ===")
    print(f"Can send email: {limiter.can_perform(Platform.GMAIL)}")
    print(f"Remaining emails: {limiter.get_remaining(Platform.GMAIL)}")

    # Simulate sending an email
    if limiter.consume(Platform.GMAIL):
        print("Email sent successfully!")
        print(f"Remaining emails: {limiter.get_remaining(Platform.GMAIL)}")

    # Get stats for all platforms
    print("\n=== Rate Limit Statistics ===")
    for platform in Platform:
        stats = limiter.get_stats(platform)
        print(f"\n{stats['platform'].upper()}:")
        print(f"  Capacity: {stats['capacity']}/day")
        print(f"  Remaining: {stats['tokens_remaining']}")
        print(f"  Used today: {stats['total_consumed_today']} ({stats['percentage_used']}%)")
        print(f"  Wait time: {stats['wait_time_seconds']:.1f}s")
