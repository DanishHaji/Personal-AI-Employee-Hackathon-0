#!/usr/bin/env python3
"""
SocialMediaPost Model - Silver Tier US2

Represents a multi-platform social media post for LinkedIn, Facebook, and Twitter.
Tracks per-platform results, content validation, and scheduled posting.

Contract: specs/002-silver-tier-upgrade/contracts/social-post-plan-schema.json
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
import yaml


class Platform(str, Enum):
    """Supported social media platforms."""
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    TWITTER = "twitter"


class PostStatus(str, Enum):
    """Post lifecycle status."""
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    FAILED = "failed"
    PARTIAL = "partial"  # Some platforms succeeded, others failed


class PlatformResultStatus(str, Enum):
    """Per-platform execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


# Platform character limits
PLATFORM_LIMITS = {
    Platform.LINKEDIN: 3000,
    Platform.FACEBOOK: 63206,
    Platform.TWITTER: 280
}


@dataclass
class PlatformResult:
    """Result of posting to a single platform."""
    platform: str
    status: PlatformResultStatus
    post_url: Optional[str] = None
    post_id: Optional[str] = None
    error: Optional[str] = None
    posted_at: Optional[str] = None  # ISO 8601 timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        data = {
            'platform': self.platform,
            'status': self.status.value if isinstance(self.status, PlatformResultStatus) else self.status
        }
        if self.post_url:
            data['post_url'] = self.post_url
        if self.post_id:
            data['post_id'] = self.post_id
        if self.error:
            data['error'] = self.error
        if self.posted_at:
            data['posted_at'] = self.posted_at
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlatformResult':
        """Create from dictionary."""
        if isinstance(data.get('status'), str):
            data['status'] = PlatformResultStatus(data['status'])
        return cls(**data)


@dataclass
class MediaAttachment:
    """Media attachment for social post."""
    url: str
    type: Literal["image", "video", "document"]
    alt_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'url': self.url, 'type': self.type}
        if self.alt_text:
            data['alt_text'] = self.alt_text
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaAttachment':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SocialMediaPost:
    """
    Multi-platform social media post.

    Stores post content, target platforms, scheduling information, and per-platform
    execution results. Supports LinkedIn, Facebook, and Twitter with platform-specific
    validation.
    """

    # Required fields
    post_id: str  # Format: POST_[platform]_[timestamp]
    platforms: List[Platform]
    content: str
    status: PostStatus

    # Optional fields
    media_attachments: List[MediaAttachment] = field(default_factory=list)
    scheduled_time: Optional[str] = None  # ISO 8601 timestamp
    platform_results: Dict[str, PlatformResult] = field(default_factory=dict)
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    posted_at: Optional[str] = None
    error_details: Optional[str] = None

    def __post_init__(self):
        """Post-initialization validation."""
        # Convert string platforms to enums
        if self.platforms and isinstance(self.platforms[0], str):
            self.platforms = [Platform(p) for p in self.platforms]

        # Convert string status to enum
        if isinstance(self.status, str):
            self.status = PostStatus(self.status)

        # Set created_at if not provided
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    @classmethod
    def create(
        cls,
        platforms: List[str],
        content: str,
        media_attachments: Optional[List[Dict[str, Any]]] = None,
        scheduled_time: Optional[str] = None
    ) -> 'SocialMediaPost':
        """
        Create a new SocialMediaPost with auto-generated ID.

        Args:
            platforms: List of platform names (linkedin, facebook, twitter)
            content: Post content text
            media_attachments: Optional list of media attachment dicts
            scheduled_time: Optional ISO 8601 timestamp for scheduled posting

        Returns:
            SocialMediaPost instance

        Raises:
            ValueError: If platforms list is empty or content is invalid
        """
        if not platforms:
            raise ValueError("At least one platform must be specified")

        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # Generate post ID using first platform and timestamp
        timestamp = int(datetime.now(timezone.utc).timestamp())
        post_id = f"POST_{platforms[0]}_{timestamp}"

        # Convert media attachments
        attachments = []
        if media_attachments:
            attachments = [MediaAttachment.from_dict(m) for m in media_attachments]

        return cls(
            post_id=post_id,
            platforms=[Platform(p) for p in platforms],
            content=content.strip(),
            status=PostStatus.DRAFT,
            media_attachments=attachments,
            scheduled_time=scheduled_time
        )

    def validate_content_length(self) -> Dict[Platform, bool]:
        """
        Check if content length is valid for each platform.

        Returns:
            Dict mapping Platform to validation result (True = valid, False = too long)
        """
        results = {}
        content_length = len(self.content)

        for platform in self.platforms:
            limit = PLATFORM_LIMITS[platform]
            results[platform] = content_length <= limit

        return results

    def needs_thread(self) -> bool:
        """
        Check if Twitter content requires threading (>280 characters).

        Returns:
            True if content exceeds Twitter's 280 character limit
        """
        if Platform.TWITTER not in self.platforms:
            return False

        return len(self.content) > PLATFORM_LIMITS[Platform.TWITTER]

    def split_into_tweets(self) -> List[str]:
        """
        Split long content into Twitter-sized chunks for threading.

        Returns:
            List of tweet strings, each ≤280 characters
        """
        if not self.needs_thread():
            return [self.content]

        tweets = []
        words = self.content.split()
        current_tweet = ""

        for word in words:
            # Account for space and thread counter (e.g., " (1/3)")
            test_tweet = f"{current_tweet} {word}".strip()
            thread_suffix = f" ({len(tweets) + 1}/X)"

            if len(test_tweet) + len(thread_suffix) <= PLATFORM_LIMITS[Platform.TWITTER]:
                current_tweet = test_tweet
            else:
                # Current tweet is full, save it and start new one
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = word

        # Add final tweet
        if current_tweet:
            tweets.append(current_tweet)

        # Add thread counters
        total = len(tweets)
        return [f"{tweet} ({i+1}/{total})" for i, tweet in enumerate(tweets)]

    def update_platform_result(
        self,
        platform: Platform,
        status: PlatformResultStatus,
        post_url: Optional[str] = None,
        post_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update execution result for a specific platform.

        Args:
            platform: Platform that was posted to
            status: Result status (success/failed)
            post_url: URL of posted content
            post_id: Platform-specific post ID
            error: Error message if failed
        """
        self.platform_results[platform.value] = PlatformResult(
            platform=platform.value,
            status=status,
            post_url=post_url,
            post_id=post_id,
            error=error,
            posted_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )

        # Update overall status
        self._update_status()

    def _update_status(self):
        """Update overall post status based on platform results."""
        if not self.platform_results:
            return

        success_count = sum(
            1 for r in self.platform_results.values()
            if r.status == PlatformResultStatus.SUCCESS
        )
        failed_count = sum(
            1 for r in self.platform_results.values()
            if r.status == PlatformResultStatus.FAILED
        )
        total_platforms = len(self.platforms)

        if success_count == total_platforms:
            self.status = PostStatus.POSTED
            self.posted_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        elif failed_count == total_platforms:
            self.status = PostStatus.FAILED
        elif success_count > 0:
            self.status = PostStatus.PARTIAL

    def to_yaml_frontmatter(self) -> Dict[str, Any]:
        """
        Convert to dictionary for YAML frontmatter serialization.

        Returns:
            Dictionary suitable for YAML frontmatter
        """
        data = {
            'type': 'social_media_post',
            'post_id': self.post_id,
            'platforms': [p.value for p in self.platforms],
            'status': self.status.value,
            'created_at': self.created_at
        }

        if self.scheduled_time:
            data['scheduled_time'] = self.scheduled_time

        if self.approved_at:
            data['approved_at'] = self.approved_at

        if self.posted_at:
            data['posted_at'] = self.posted_at

        if self.media_attachments:
            data['media_attachments'] = [m.to_dict() for m in self.media_attachments]

        if self.platform_results:
            data['platform_results'] = {
                platform: result.to_dict()
                for platform, result in self.platform_results.items()
            }

        if self.error_details:
            data['error_details'] = self.error_details

        return data

    @classmethod
    def from_yaml_frontmatter(cls, frontmatter: Dict[str, Any], body: str) -> 'SocialMediaPost':
        """
        Create SocialMediaPost from YAML frontmatter and body.

        Args:
            frontmatter: Parsed YAML frontmatter dictionary
            body: Post content body

        Returns:
            SocialMediaPost instance
        """
        # Convert platform_results if present
        platform_results = {}
        if 'platform_results' in frontmatter:
            platform_results = {
                platform: PlatformResult.from_dict(result)
                for platform, result in frontmatter['platform_results'].items()
            }

        # Convert media_attachments if present
        media_attachments = []
        if 'media_attachments' in frontmatter:
            media_attachments = [
                MediaAttachment.from_dict(m)
                for m in frontmatter['media_attachments']
            ]

        return cls(
            post_id=frontmatter['post_id'],
            platforms=[Platform(p) for p in frontmatter['platforms']],
            content=body.strip(),
            status=PostStatus(frontmatter['status']),
            media_attachments=media_attachments,
            scheduled_time=frontmatter.get('scheduled_time'),
            platform_results=platform_results,
            created_at=frontmatter.get('created_at'),
            approved_at=frontmatter.get('approved_at'),
            posted_at=frontmatter.get('posted_at'),
            error_details=frontmatter.get('error_details')
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        platforms_str = ", ".join(p.value for p in self.platforms)
        return (
            f"SocialMediaPost(post_id='{self.post_id}', platforms=[{platforms_str}], "
            f"status={self.status.value}, content_length={len(self.content)})"
        )


# Example usage
if __name__ == "__main__":
    # Example: Create multi-platform post
    post = SocialMediaPost.create(
        platforms=["linkedin", "twitter"],
        content="Excited to announce the launch of our new AI Employee system! "
                "This revolutionary tool helps automate email triage, file processing, "
                "and now social media posting across multiple platforms. #AI #Automation",
        media_attachments=[
            {
                'url': 'https://example.com/screenshot.png',
                'type': 'image',
                'alt_text': 'AI Employee Dashboard Screenshot'
            }
        ]
    )

    print("=== SocialMediaPost Example ===")
    print(f"Post ID: {post.post_id}")
    print(f"Platforms: {[p.value for p in post.platforms]}")
    print(f"Content length: {len(post.content)} chars")
    print(f"Needs thread: {post.needs_thread()}")

    # Validate content length
    print("\n=== Content Validation ===")
    validation = post.validate_content_length()
    for platform, is_valid in validation.items():
        print(f"{platform.value}: {'✓ Valid' if is_valid else '✗ Too long'}")

    # Test Twitter threading
    print("\n=== Twitter Threading ===")
    if post.needs_thread():
        tweets = post.split_into_tweets()
        print(f"Split into {len(tweets)} tweets:")
        for i, tweet in enumerate(tweets, 1):
            print(f"  Tweet {i}: {tweet}")

    # Update result
    print("\n=== Platform Results ===")
    post.update_platform_result(
        Platform.LINKEDIN,
        PlatformResultStatus.SUCCESS,
        post_url="https://linkedin.com/posts/123",
        post_id="urn:li:share:123"
    )
    print(f"LinkedIn result: {post.platform_results['linkedin'].status.value}")
    print(f"Overall status: {post.status.value}")

    # YAML frontmatter
    print("\n=== YAML Frontmatter ===")
    frontmatter = post.to_yaml_frontmatter()
    print(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False))
