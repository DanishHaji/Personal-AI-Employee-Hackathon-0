#!/usr/bin/env python3
"""
SocialMediaService - Silver Tier US2

Handles multi-platform social media posting via MCP servers.
Supports LinkedIn, Facebook, and Twitter with platform-specific validation and threading.

Workflow:
1. Validate content length per platform
2. Post to each platform via MCP client
3. Track per-platform results
4. Handle partial failures (some platforms succeed, others fail)
5. Apply rate limiting per platform
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from src.services.mcp_client import MCPClient, MCPResponse, MCPErrorType
from src.services.rate_limiter import RateLimiter, Platform as RateLimitPlatform
from src.models.social_media_post import (
    SocialMediaPost,
    Platform,
    PostStatus,
    PlatformResult,
    PlatformResultStatus,
    PLATFORM_LIMITS
)


logger = logging.getLogger(__name__)


class SocialMediaService:
    """
    Service for posting to multiple social media platforms via MCP servers.

    Handles platform-specific logic including:
    - Content validation (character limits)
    - Twitter threading for long content
    - Multi-platform posting with result tracking
    - Partial failure handling
    - Rate limiting per platform

    Usage:
        service = SocialMediaService(
            mcp_clients={
                'linkedin': linkedin_client,
                'facebook': facebook_client,
                'twitter': twitter_client
            },
            rate_limiter=rate_limiter
        )

        post = SocialMediaPost.create(
            platforms=['linkedin', 'twitter'],
            content='Hello world!'
        )

        success, results = service.post_multi_platform(post)
    """

    def __init__(
        self,
        mcp_clients: Dict[str, MCPClient],
        rate_limiter: RateLimiter
    ):
        """
        Initialize SocialMediaService.

        Args:
            mcp_clients: Dictionary of MCP clients by platform name
            rate_limiter: RateLimiter instance for quota management
        """
        self.mcp_clients = mcp_clients
        self.rate_limiter = rate_limiter

        logger.info(
            f"SocialMediaService initialized "
            f"(platforms: {', '.join(mcp_clients.keys())})"
        )

    def validate_platform_limits(
        self,
        post: SocialMediaPost
    ) -> Tuple[bool, Dict[Platform, str]]:
        """
        Validate content length against platform limits.

        Args:
            post: SocialMediaPost to validate

        Returns:
            Tuple[bool, Dict]: (all_valid, error_messages_by_platform)
        """
        errors = {}
        validation_results = post.validate_content_length()

        for platform, is_valid in validation_results.items():
            if not is_valid:
                limit = PLATFORM_LIMITS[platform]
                actual = len(post.content)
                errors[platform] = (
                    f"Content too long for {platform.value}: "
                    f"{actual} chars (limit: {limit})"
                )

        all_valid = len(errors) == 0

        if not all_valid:
            logger.warning(
                f"Content validation failed for post {post.post_id}: "
                f"{', '.join(errors.keys())}"
            )

        return all_valid, errors

    def post_to_linkedin(
        self,
        post: SocialMediaPost
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Post content to LinkedIn via MCP client.

        Args:
            post: SocialMediaPost with content to post

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]:
                (success, response_data, error_message)
        """
        # Check rate limit
        if not self.rate_limiter.can_perform(RateLimitPlatform.LINKEDIN):
            wait_time = self.rate_limiter.get_wait_time(RateLimitPlatform.LINKEDIN)
            error = f"Rate limit exceeded - wait {wait_time:.0f}s"
            logger.warning(f"LinkedIn rate limit exceeded for {post.post_id}")
            return False, None, error

        # Get LinkedIn MCP client
        client = self.mcp_clients.get('linkedin')
        if not client:
            error = "LinkedIn MCP client not configured"
            logger.error(error)
            return False, None, error

        # Consume rate limit token
        self.rate_limiter.consume(RateLimitPlatform.LINKEDIN)

        try:
            # Prepare post data
            post_data = {
                'content': post.content
            }

            # Add media attachments if present
            if post.media_attachments:
                post_data['media'] = [
                    {
                        'url': m.url,
                        'type': m.type,
                        'alt_text': m.alt_text
                    }
                    for m in post.media_attachments
                ]

            # Call LinkedIn MCP server
            response = client.post("/share", data=post_data)

            if response.success:
                logger.info(f"Posted to LinkedIn successfully: {post.post_id}")
                return True, response.data, None
            else:
                logger.error(
                    f"LinkedIn post failed for {post.post_id}: {response.error}"
                )
                return False, None, response.error

        except Exception as e:
            error = f"Unexpected error posting to LinkedIn: {str(e)}"
            logger.exception(error)
            return False, None, error

    def post_to_facebook(
        self,
        post: SocialMediaPost
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Post content to Facebook via MCP client.

        Args:
            post: SocialMediaPost with content to post

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]:
                (success, response_data, error_message)
        """
        # Check rate limit
        if not self.rate_limiter.can_perform(RateLimitPlatform.FACEBOOK):
            wait_time = self.rate_limiter.get_wait_time(RateLimitPlatform.FACEBOOK)
            error = f"Rate limit exceeded - wait {wait_time:.0f}s"
            logger.warning(f"Facebook rate limit exceeded for {post.post_id}")
            return False, None, error

        # Get Facebook MCP client
        client = self.mcp_clients.get('facebook')
        if not client:
            error = "Facebook MCP client not configured"
            logger.error(error)
            return False, None, error

        # Consume rate limit token
        self.rate_limiter.consume(RateLimitPlatform.FACEBOOK)

        try:
            # Prepare post data
            post_data = {
                'message': post.content
            }

            # Add media attachments if present
            if post.media_attachments:
                post_data['attachments'] = [
                    {
                        'url': m.url,
                        'type': m.type
                    }
                    for m in post.media_attachments
                ]

            # Call Facebook MCP server
            response = client.post("/post", data=post_data)

            if response.success:
                logger.info(f"Posted to Facebook successfully: {post.post_id}")
                return True, response.data, None
            else:
                logger.error(
                    f"Facebook post failed for {post.post_id}: {response.error}"
                )
                return False, None, response.error

        except Exception as e:
            error = f"Unexpected error posting to Facebook: {str(e)}"
            logger.exception(error)
            return False, None, error

    def post_to_twitter(
        self,
        post: SocialMediaPost
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Post content to Twitter via MCP client.

        Handles threading automatically for content >280 characters.

        Args:
            post: SocialMediaPost with content to post

        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]:
                (success, response_data, error_message)
        """
        # Check rate limit
        if not self.rate_limiter.can_perform(RateLimitPlatform.TWITTER):
            wait_time = self.rate_limiter.get_wait_time(RateLimitPlatform.TWITTER)
            error = f"Rate limit exceeded - wait {wait_time:.0f}s"
            logger.warning(f"Twitter rate limit exceeded for {post.post_id}")
            return False, None, error

        # Get Twitter MCP client
        client = self.mcp_clients.get('twitter')
        if not client:
            error = "Twitter MCP client not configured"
            logger.error(error)
            return False, None, error

        # Consume rate limit token
        self.rate_limiter.consume(RateLimitPlatform.TWITTER)

        try:
            # Check if threading is needed
            if post.needs_thread():
                # Split into tweets and post as thread
                tweets = post.split_into_tweets()
                logger.info(
                    f"Posting Twitter thread with {len(tweets)} tweets: {post.post_id}"
                )

                thread_data = {
                    'tweets': tweets
                }

                # Add media to first tweet only
                if post.media_attachments:
                    thread_data['media'] = [
                        {
                            'url': m.url,
                            'type': m.type,
                            'alt_text': m.alt_text
                        }
                        for m in post.media_attachments
                    ]

                # Call Twitter thread endpoint
                response = client.post("/thread", data=thread_data)

            else:
                # Single tweet
                tweet_data = {
                    'text': post.content
                }

                # Add media attachments
                if post.media_attachments:
                    tweet_data['media'] = [
                        {
                            'url': m.url,
                            'type': m.type,
                            'alt_text': m.alt_text
                        }
                        for m in post.media_attachments
                    ]

                # Call Twitter tweet endpoint
                response = client.post("/tweet", data=tweet_data)

            if response.success:
                logger.info(f"Posted to Twitter successfully: {post.post_id}")
                return True, response.data, None
            else:
                logger.error(
                    f"Twitter post failed for {post.post_id}: {response.error}"
                )
                return False, None, response.error

        except Exception as e:
            error = f"Unexpected error posting to Twitter: {str(e)}"
            logger.exception(error)
            return False, None, error

    def post_multi_platform(
        self,
        post: SocialMediaPost
    ) -> Tuple[bool, Dict[Platform, PlatformResult]]:
        """
        Post to multiple platforms sequentially.

        Posts to each platform in order, tracking results independently.
        Handles partial failures (some platforms succeed, others fail).

        Args:
            post: SocialMediaPost to post

        Returns:
            Tuple[bool, Dict]: (all_succeeded, platform_results)
        """
        results = {}
        success_count = 0
        total_platforms = len(post.platforms)

        logger.info(
            f"Posting to {total_platforms} platforms: "
            f"{', '.join(p.value for p in post.platforms)}"
        )

        for platform in post.platforms:
            logger.info(f"Posting to {platform.value}...")

            # Route to platform-specific method
            if platform == Platform.LINKEDIN:
                success, response_data, error = self.post_to_linkedin(post)
            elif platform == Platform.FACEBOOK:
                success, response_data, error = self.post_to_facebook(post)
            elif platform == Platform.TWITTER:
                success, response_data, error = self.post_to_twitter(post)
            else:
                success = False
                response_data = None
                error = f"Unsupported platform: {platform.value}"

            # Store result
            if success:
                results[platform] = PlatformResult(
                    platform=platform.value,
                    status=PlatformResultStatus.SUCCESS,
                    post_url=response_data.get('post_url') if response_data else None,
                    post_id=response_data.get('post_id') if response_data else None,
                    posted_at=datetime.now().isoformat()
                )
                success_count += 1
            else:
                results[platform] = PlatformResult(
                    platform=platform.value,
                    status=PlatformResultStatus.FAILED,
                    error=error,
                    posted_at=datetime.now().isoformat()
                )

            # Update post with platform result
            post.update_platform_result(
                platform,
                results[platform].status,
                post_url=results[platform].post_url,
                post_id=results[platform].post_id,
                error=results[platform].error
            )

        # Determine overall success
        all_succeeded = success_count == total_platforms

        if all_succeeded:
            logger.info(
                f"Multi-platform post successful: {post.post_id} "
                f"({success_count}/{total_platforms} platforms)"
            )
        elif success_count > 0:
            logger.warning(
                f"Partial multi-platform post: {post.post_id} "
                f"({success_count}/{total_platforms} platforms succeeded)"
            )
        else:
            logger.error(
                f"Multi-platform post failed: {post.post_id} "
                f"(0/{total_platforms} platforms succeeded)"
            )

        return all_succeeded, results

    def handle_partial_failure(
        self,
        post: SocialMediaPost
    ) -> str:
        """
        Generate error summary for partial failures.

        Args:
            post: SocialMediaPost with mixed results

        Returns:
            Human-readable error summary
        """
        if post.status != PostStatus.PARTIAL:
            return ""

        success_platforms = []
        failed_platforms = []

        for platform_name, result in post.platform_results.items():
            if result.status == PlatformResultStatus.SUCCESS:
                success_platforms.append(platform_name)
            else:
                failed_platforms.append(f"{platform_name} ({result.error})")

        error_summary = (
            f"Partial failure: Posted successfully to {', '.join(success_platforms)} "
            f"but failed on {', '.join(failed_platforms)}"
        )

        return error_summary


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    from src.services.rate_limiter import RateLimiter

    # Initialize services
    rate_limiter = RateLimiter(state_file="./Logs/rate_limit_state.json")

    # Create mock MCP clients (DRY_RUN mode)
    mcp_clients = {
        'linkedin': MCPClient(
            server_url="http://localhost:3002/linkedin",
            dry_run=True
        ),
        'facebook': MCPClient(
            server_url="http://localhost:3003/facebook",
            dry_run=True
        ),
        'twitter': MCPClient(
            server_url="http://localhost:3004/twitter",
            dry_run=True
        )
    }

    # Create service
    service = SocialMediaService(
        mcp_clients=mcp_clients,
        rate_limiter=rate_limiter
    )

    # Create test post
    post = SocialMediaPost.create(
        platforms=['linkedin', 'twitter'],
        content="Test post from AI Employee! This is a multi-platform announcement."
    )

    print("\n=== SocialMediaService Example ===")
    print(f"Post ID: {post.post_id}")
    print(f"Platforms: {[p.value for p in post.platforms]}")

    # Validate content
    is_valid, errors = service.validate_platform_limits(post)
    print(f"Content valid: {is_valid}")

    # Post to platforms
    success, results = service.post_multi_platform(post)
    print(f"\nPosting result: {'Success' if success else 'Failed'}")
    print(f"Post status: {post.status.value}")

    for platform, result in results.items():
        print(f"  {platform.value}: {result.status.value}")
