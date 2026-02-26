#!/usr/bin/env python3
"""
WhatsAppMessage Model - Silver Tier US3

Represents an incoming WhatsApp Business message with sender info, content,
media attachments, and priority detection.

Contract: specs/002-silver-tier-upgrade/contracts/whatsapp-message-schema.json
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
import yaml
import re


class MessagePriority(str, Enum):
    """Message priority based on sender contact."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MessageStatus(str, Enum):
    """Message processing status."""
    NEW = "new"
    PROCESSED = "processed"
    REPLIED = "replied"
    ARCHIVED = "archived"


class MediaType(str, Enum):
    """WhatsApp media attachment types."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    VOICE = "voice"
    STICKER = "sticker"


@dataclass
class MediaAttachment:
    """Media attachment from WhatsApp message."""
    media_id: str
    media_type: MediaType
    mime_type: str
    file_size: int  # bytes
    url: Optional[str] = None  # MCP server provides download URL
    local_path: Optional[str] = None  # Path after download to /Inbox/
    caption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        data = {
            'media_id': self.media_id,
            'media_type': self.media_type.value if isinstance(self.media_type, MediaType) else self.media_type,
            'mime_type': self.mime_type,
            'file_size': self.file_size
        }
        if self.url:
            data['url'] = self.url
        if self.local_path:
            data['local_path'] = self.local_path
        if self.caption:
            data['caption'] = self.caption
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaAttachment':
        """Create from dictionary."""
        if isinstance(data.get('media_type'), str):
            data['media_type'] = MediaType(data['media_type'])
        return cls(**data)


@dataclass
class WhatsAppMessage:
    """
    WhatsApp Business message entity.

    Represents an incoming message from WhatsApp Business API.
    Created by WhatsAppWatcher, stored in /Needs_Action/ folder.
    """

    message_id: str  # Unique WhatsApp message ID (format: wamid.XXX)
    sender_phone: str  # E.164 format (+[country][number])
    sender_name: Optional[str]  # Contact name if available
    message_content: str  # Text content
    timestamp: str  # ISO 8601 timestamp when message was sent
    priority: MessagePriority = MessagePriority.MEDIUM
    status: MessageStatus = MessageStatus.NEW
    media_attachments: List[MediaAttachment] = field(default_factory=list)
    created_at: Optional[str] = None  # When entity was created in vault
    processed_at: Optional[str] = None  # When message was processed
    conversation_id: Optional[str] = None  # WhatsApp conversation ID
    reply_context: Optional[Dict[str, Any]] = None  # Context for replying

    @classmethod
    def create(
        cls,
        message_id: str,
        sender_phone: str,
        message_content: str,
        timestamp: Optional[str] = None,
        sender_name: Optional[str] = None,
        media_attachments: Optional[List[Dict[str, Any]]] = None,
        priority: Optional[MessagePriority] = None,
        conversation_id: Optional[str] = None
    ) -> 'WhatsAppMessage':
        """
        Create a new WhatsAppMessage instance.

        Args:
            message_id: WhatsApp message ID
            sender_phone: Sender phone in E.164 format
            message_content: Message text
            timestamp: Message timestamp (ISO 8601), defaults to now
            sender_name: Optional sender name
            media_attachments: List of media attachment dicts
            priority: Message priority (defaults to MEDIUM)
            conversation_id: WhatsApp conversation ID

        Returns:
            WhatsAppMessage instance
        """
        # Validate phone format
        is_valid, error_msg = cls.validate_phone_format(sender_phone)
        if not is_valid:
            raise ValueError(f"Invalid phone format: {error_msg}")

        # Default timestamp to now
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Parse media attachments
        attachments = []
        if media_attachments:
            for media_data in media_attachments:
                attachments.append(MediaAttachment.from_dict(media_data))

        # Default priority
        if priority is None:
            priority = MessagePriority.MEDIUM

        # Create message
        created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        return cls(
            message_id=message_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            message_content=message_content,
            timestamp=timestamp,
            priority=priority,
            status=MessageStatus.NEW,
            media_attachments=attachments,
            created_at=created_at,
            conversation_id=conversation_id
        )

    @staticmethod
    def validate_phone_format(phone: str) -> tuple[bool, Optional[str]]:
        """
        Validate phone number is in E.164 format.

        E.164 format: +[country code][subscriber number]
        - Must start with +
        - Country code: 1-3 digits
        - Subscriber number: up to 15 digits total (including country code)
        - No spaces, dashes, or other characters

        Examples:
            Valid: +14155552671, +442071838750, +551155256325
            Invalid: 4155552671, +1-415-555-2671, +1 415 555 2671

        Args:
            phone: Phone number to validate

        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
        """
        # E.164 pattern: + followed by 1-15 digits
        pattern = r'^\+[1-9]\d{1,14}$'

        if not phone:
            return False, "Phone number is empty"

        if not phone.startswith('+'):
            return False, "Phone number must start with '+' (E.164 format)"

        if not re.match(pattern, phone):
            return False, "Invalid E.164 format (expected: +[country][number], digits only)"

        # Check total length (max 15 digits excluding +)
        digits = phone[1:]  # Remove +
        if len(digits) > 15:
            return False, f"Phone number too long ({len(digits)} digits, max 15)"

        return True, None

    def to_yaml_frontmatter(self) -> Dict[str, Any]:
        """
        Convert to YAML frontmatter for Markdown file.

        Returns:
            Dictionary for YAML frontmatter
        """
        frontmatter = {
            'type': 'whatsapp_message',
            'message_id': self.message_id,
            'sender_phone': self.sender_phone,
            'timestamp': self.timestamp,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at
        }

        if self.sender_name:
            frontmatter['sender_name'] = self.sender_name

        if self.media_attachments:
            frontmatter['media_attachments'] = [
                media.to_dict() for media in self.media_attachments
            ]

        if self.processed_at:
            frontmatter['processed_at'] = self.processed_at

        if self.conversation_id:
            frontmatter['conversation_id'] = self.conversation_id

        if self.reply_context:
            frontmatter['reply_context'] = self.reply_context

        return frontmatter

    @classmethod
    def from_yaml_frontmatter(cls, frontmatter: Dict[str, Any], body: str) -> 'WhatsAppMessage':
        """
        Create WhatsAppMessage from YAML frontmatter and body.

        Args:
            frontmatter: Parsed YAML frontmatter
            body: Message content (Markdown body)

        Returns:
            WhatsAppMessage instance
        """
        # Parse enums
        priority = MessagePriority(frontmatter.get('priority', 'medium'))
        status = MessageStatus(frontmatter.get('status', 'new'))

        # Parse media attachments
        attachments = []
        if 'media_attachments' in frontmatter:
            for media_data in frontmatter['media_attachments']:
                attachments.append(MediaAttachment.from_dict(media_data))

        return cls(
            message_id=frontmatter['message_id'],
            sender_phone=frontmatter['sender_phone'],
            sender_name=frontmatter.get('sender_name'),
            message_content=body.strip(),
            timestamp=frontmatter['timestamp'],
            priority=priority,
            status=status,
            media_attachments=attachments,
            created_at=frontmatter.get('created_at'),
            processed_at=frontmatter.get('processed_at'),
            conversation_id=frontmatter.get('conversation_id'),
            reply_context=frontmatter.get('reply_context')
        )

    def mark_processed(self):
        """Mark message as processed."""
        self.status = MessageStatus.PROCESSED
        self.processed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def mark_replied(self):
        """Mark message as replied."""
        self.status = MessageStatus.REPLIED
        self.processed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def set_priority(self, priority: MessagePriority):
        """Set message priority."""
        self.priority = priority

    def add_media_attachment(self, media: MediaAttachment):
        """Add media attachment to message."""
        self.media_attachments.append(media)

    def has_media(self) -> bool:
        """Check if message has media attachments."""
        return len(self.media_attachments) > 0

    def get_media_count(self) -> int:
        """Get count of media attachments."""
        return len(self.media_attachments)

    def validate(self):
        """
        Validate message data.

        Raises:
            ValueError: If validation fails
        """
        # Validate phone format
        is_valid, error_msg = self.validate_phone_format(self.sender_phone)
        if not is_valid:
            raise ValueError(f"Invalid sender phone: {error_msg}")

        # Validate message ID
        if not self.message_id:
            raise ValueError("message_id is required")

        # Validate content
        if not self.message_content:
            raise ValueError("message_content cannot be empty")

        # Validate timestamp
        if not self.timestamp:
            raise ValueError("timestamp is required")

        # Validate priority
        if self.priority not in MessagePriority:
            raise ValueError(f"Invalid priority: {self.priority}")

        # Validate status
        if self.status not in MessageStatus:
            raise ValueError(f"Invalid status: {self.status}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message_id': self.message_id,
            'sender_phone': self.sender_phone,
            'sender_name': self.sender_name,
            'message_content': self.message_content,
            'timestamp': self.timestamp,
            'priority': self.priority.value,
            'status': self.status.value,
            'media_attachments': [media.to_dict() for media in self.media_attachments],
            'created_at': self.created_at,
            'processed_at': self.processed_at,
            'conversation_id': self.conversation_id,
            'reply_context': self.reply_context
        }

    def __str__(self) -> str:
        """String representation."""
        media_str = f" ({len(self.media_attachments)} media)" if self.has_media() else ""
        return (
            f"WhatsAppMessage({self.message_id}, from={self.sender_phone}, "
            f"priority={self.priority.value}{media_str})"
        )
