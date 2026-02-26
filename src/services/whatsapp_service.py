#!/usr/bin/env python3
"""
WhatsAppService - Silver Tier US3

Handles WhatsApp Business API message polling, processing, and entity creation.
Polls for new messages, detects priority contacts, downloads media, and creates
WhatsAppMessage entities in /Needs_Action/.

Core workflow:
1. Poll WhatsApp MCP server for new messages every 60 seconds
2. Check sender against priority contacts in Company_Handbook.md
3. Download media attachments (if any) to /Inbox/
4. Create WhatsAppMessage entity in /Needs_Action/
5. Track processed message IDs to prevent duplicates
"""

import os
import time
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone

from src.services.mcp_client import MCPClient, MCPResponse, MCPErrorType
from src.services.vault_service import VaultService
from src.models.whatsapp_message import (
    WhatsAppMessage,
    MessagePriority,
    MediaAttachment,
    MediaType
)


logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service for WhatsApp Business message polling and processing.

    Polls WhatsApp MCP server for new messages, processes them, and creates
    WhatsAppMessage entities in the vault.

    Usage:
        service = WhatsAppService(
            mcp_client=whatsapp_mcp_client,
            vault_service=vault_service,
            priority_contacts=["+14155552671", "+442071838750"]
        )

        # Poll for new messages
        messages = service.poll_messages()

        # Process each message
        for message in messages:
            entity_path = service.create_message_entity(message)
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        vault_service: VaultService,
        priority_contacts: Optional[List[str]] = None
    ):
        """
        Initialize WhatsAppService.

        Args:
            mcp_client: MCP client for WhatsApp Business API
            vault_service: VaultService for file operations
            priority_contacts: List of phone numbers (E.164) to flag as high priority
        """
        self.mcp_client = mcp_client
        self.vault_service = vault_service
        self.priority_contacts = set(priority_contacts) if priority_contacts else set()

        # Track processed message IDs to prevent duplicates
        self.processed_messages: Set[str] = set()
        self._load_processed_ids()

        logger.info(
            f"WhatsAppService initialized with {len(self.priority_contacts)} "
            f"priority contacts"
        )

    def _load_processed_ids(self):
        """
        Load previously processed message IDs from state file.

        State file: vault/Logs/whatsapp_state.json
        Format: {"processed_messages": ["wamid.XXX", "wamid.YYY", ...]}
        """
        state_file = self.vault_service.vault_path / "Logs" / "whatsapp_state.json"

        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_messages = set(state.get('processed_messages', []))
                    logger.info(
                        f"Loaded {len(self.processed_messages)} processed message IDs"
                    )
            except Exception as e:
                logger.error(f"Failed to load WhatsApp state: {e}")
                self.processed_messages = set()
        else:
            logger.debug("No existing WhatsApp state file found")

    def _save_processed_ids(self):
        """Save processed message IDs to state file."""
        state_file = self.vault_service.vault_path / "Logs" / "whatsapp_state.json"

        try:
            # Ensure Logs directory exists
            state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'processed_messages': list(self.processed_messages),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

            logger.debug(f"Saved {len(self.processed_messages)} processed message IDs")

        except Exception as e:
            logger.error(f"Failed to save WhatsApp state: {e}")

    def poll_messages(self) -> List[WhatsAppMessage]:
        """
        Poll WhatsApp MCP server for new messages.

        Fetches unread messages from WhatsApp Business API via MCP server.
        Filters out already-processed messages using message_id tracking.

        Returns:
            List of new WhatsAppMessage instances

        Raises:
            ConnectionError: If MCP server is unreachable
        """
        logger.debug("Polling WhatsApp MCP server for new messages")

        try:
            # Call MCP server /messages endpoint
            response: MCPResponse = self.mcp_client.get("/messages", params={"status": "unread"})

            if not response.success:
                logger.error(f"Failed to poll messages: {response.error}")
                if response.error_type == MCPErrorType.CONNECTION:
                    raise ConnectionError(f"WhatsApp MCP server unreachable: {response.error}")
                return []

            # Parse messages from response
            messages_data = response.data.get('messages', [])
            logger.info(f"Received {len(messages_data)} messages from MCP server")

            # Convert to WhatsAppMessage instances
            new_messages = []
            for msg_data in messages_data:
                message_id = msg_data.get('id')

                # Skip if already processed
                if self.prevent_duplicates(message_id):
                    logger.debug(f"Skipping duplicate message: {message_id}")
                    continue

                # Create WhatsAppMessage
                try:
                    message = self._parse_message(msg_data)
                    new_messages.append(message)
                    logger.info(
                        f"New message from {message.sender_phone}: "
                        f"{message.message_content[:50]}..."
                    )
                except Exception as e:
                    logger.error(f"Failed to parse message {message_id}: {e}")
                    continue

            logger.info(f"Polled {len(new_messages)} new messages")
            return new_messages

        except ConnectionError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error polling messages: {e}")
            return []

    def _parse_message(self, msg_data: Dict[str, Any]) -> WhatsAppMessage:
        """
        Parse message data from MCP server response.

        Args:
            msg_data: Message data from MCP server

        Returns:
            WhatsAppMessage instance
        """
        # Extract required fields
        message_id = msg_data['id']
        sender_phone = msg_data['from']
        message_content = msg_data.get('text', {}).get('body', '')
        timestamp = msg_data.get('timestamp')

        # Extract optional fields
        sender_name = msg_data.get('profile', {}).get('name')
        conversation_id = msg_data.get('conversation_id')

        # Parse media attachments
        media_attachments = []
        if 'media' in msg_data:
            for media_data in msg_data['media']:
                media = self._parse_media_attachment(media_data)
                if media:
                    media_attachments.append(media.to_dict())

        # Detect priority
        priority = self.detect_priority_contacts(sender_phone)

        # Create message
        message = WhatsAppMessage.create(
            message_id=message_id,
            sender_phone=sender_phone,
            message_content=message_content,
            timestamp=timestamp,
            sender_name=sender_name,
            media_attachments=media_attachments,
            priority=priority,
            conversation_id=conversation_id
        )

        # Set reply context for future responses
        message.reply_context = {
            'conversation_id': conversation_id,
            'message_id': message_id,
            'sender_phone': sender_phone
        }

        return message

    def _parse_media_attachment(self, media_data: Dict[str, Any]) -> Optional[MediaAttachment]:
        """
        Parse media attachment from MCP server response.

        Args:
            media_data: Media data from MCP server

        Returns:
            MediaAttachment instance or None if parsing fails
        """
        try:
            media_type_str = media_data.get('type', 'document')
            media_type = MediaType(media_type_str)

            return MediaAttachment(
                media_id=media_data['id'],
                media_type=media_type,
                mime_type=media_data.get('mime_type', 'application/octet-stream'),
                file_size=media_data.get('file_size', 0),
                url=media_data.get('url'),
                caption=media_data.get('caption')
            )
        except Exception as e:
            logger.error(f"Failed to parse media attachment: {e}")
            return None

    def detect_priority_contacts(self, sender_phone: str) -> MessagePriority:
        """
        Detect message priority based on sender phone.

        Checks if sender_phone is in priority_contacts list loaded from
        Company_Handbook.md.

        Args:
            sender_phone: Sender phone number in E.164 format

        Returns:
            MessagePriority (HIGH if in priority list, MEDIUM otherwise)
        """
        if sender_phone in self.priority_contacts:
            logger.info(f"Priority contact detected: {sender_phone}")
            return MessagePriority.HIGH

        return MessagePriority.MEDIUM

    def load_priority_contacts_from_handbook(self) -> List[str]:
        """
        Load priority contacts from Company_Handbook.md.

        Reads the handbook file and extracts whatsapp_priority_contacts YAML section.

        Example in Company_Handbook.md:
        ```yaml
        whatsapp_priority_contacts:
          - phone: "+14155552671"
            name: "CEO - John Smith"
          - phone: "+442071838750"
            name: "CFO - Jane Doe"
        ```

        Returns:
            List of priority phone numbers
        """
        handbook_path = self.vault_service.vault_path / "Company_Handbook.md"

        if not handbook_path.exists():
            logger.warning("Company_Handbook.md not found - no priority contacts loaded")
            return []

        try:
            frontmatter, body = self.vault_service.read_markdown_with_frontmatter(handbook_path)

            # Check for priority contacts in frontmatter
            priority_list = frontmatter.get('whatsapp_priority_contacts', [])

            if not priority_list:
                logger.debug("No whatsapp_priority_contacts found in handbook")
                return []

            # Extract phone numbers
            phones = [contact['phone'] for contact in priority_list if 'phone' in contact]
            logger.info(f"Loaded {len(phones)} priority contacts from handbook")

            # Update internal priority contacts set
            self.priority_contacts = set(phones)

            return phones

        except Exception as e:
            logger.error(f"Failed to load priority contacts from handbook: {e}")
            return []

    def download_media(self, media: MediaAttachment) -> Optional[str]:
        """
        Download media attachment from WhatsApp MCP server.

        Downloads media to /Inbox/ folder and updates media.local_path.

        Args:
            media: MediaAttachment to download

        Returns:
            Local file path if successful, None otherwise
        """
        if not media.url:
            logger.warning(f"No URL provided for media {media.media_id}")
            return None

        try:
            # Call MCP server /download endpoint
            response: MCPResponse = self.mcp_client.get(
                f"/media/{media.media_id}/download"
            )

            if not response.success:
                logger.error(f"Failed to download media {media.media_id}: {response.error}")
                return None

            # Get file content from response
            file_content = response.data.get('content')  # Base64 encoded
            if not file_content:
                logger.error(f"No content in download response for {media.media_id}")
                return None

            # Decode base64 content
            import base64
            file_bytes = base64.b64decode(file_content)

            # Determine filename
            timestamp = int(datetime.now().timestamp())
            extension = self._get_extension_for_mime(media.mime_type)
            filename = f"whatsapp_{media.media_id}_{timestamp}{extension}"

            # Write to /Inbox/ folder
            inbox_folder = self.vault_service.vault_path / "Inbox"
            inbox_folder.mkdir(parents=True, exist_ok=True)

            local_path = inbox_folder / filename

            with open(local_path, 'wb') as f:
                f.write(file_bytes)

            logger.info(
                f"Downloaded media {media.media_id} to {local_path} "
                f"({len(file_bytes)} bytes)"
            )

            # Update media local_path
            media.local_path = str(local_path)

            return str(local_path)

        except Exception as e:
            logger.exception(f"Failed to download media {media.media_id}: {e}")
            return None

    def _get_extension_for_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/3gpp': '.3gp',
            'audio/aac': '.aac',
            'audio/mpeg': '.mp3',
            'audio/ogg': '.ogg',
            'application/pdf': '.pdf',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
        }
        return mime_map.get(mime_type, '.bin')

    def create_message_entity(self, message: WhatsAppMessage) -> Path:
        """
        Create WhatsAppMessage entity file in /Needs_Action/.

        Generates WHATSAPP_[message_id].md file with YAML frontmatter and body.

        Args:
            message: WhatsAppMessage instance

        Returns:
            Path to created entity file
        """
        # Download media attachments (if any)
        if message.has_media():
            logger.info(f"Downloading {message.get_media_count()} media attachments")
            for media in message.media_attachments:
                local_path = self.download_media(media)
                if local_path:
                    logger.debug(f"Media downloaded: {local_path}")

        # Generate frontmatter
        frontmatter = message.to_yaml_frontmatter()

        # Generate body
        body_lines = [
            f"# WhatsApp Message from {message.sender_name or message.sender_phone}",
            "",
            f"**Received**: {message.timestamp}",
            f"**Priority**: {message.priority.value}",
            ""
        ]

        if message.has_media():
            body_lines.append(f"**Media Attachments**: {message.get_media_count()}")
            body_lines.append("")
            for i, media in enumerate(message.media_attachments, 1):
                body_lines.append(
                    f"{i}. {media.media_type.value} - {media.mime_type} "
                    f"({media.file_size} bytes)"
                )
                if media.local_path:
                    body_lines.append(f"   Path: `{media.local_path}`")
                if media.caption:
                    body_lines.append(f"   Caption: {media.caption}")
            body_lines.append("")

        body_lines.append("## Message")
        body_lines.append("")
        body_lines.append(message.message_content)
        body_lines.append("")

        body = "\n".join(body_lines)

        # Write entity file
        # Use short message_id for filename (last 8 chars)
        short_id = message.message_id.split('.')[-1][:8] if '.' in message.message_id else message.message_id[:8]
        filename = f"WHATSAPP_{short_id}.md"
        file_path = self.vault_service.vault_path / "Needs_Action" / filename

        self.vault_service.write_markdown_with_frontmatter(
            file_path,
            frontmatter,
            body
        )

        logger.info(f"Created WhatsApp message entity: {filename}")

        # Mark as processed
        self.processed_messages.add(message.message_id)
        self._save_processed_ids()

        return file_path

    def prevent_duplicates(self, message_id: str) -> bool:
        """
        Check if message has already been processed.

        Args:
            message_id: WhatsApp message ID

        Returns:
            True if message was already processed, False if new
        """
        return message_id in self.processed_messages

    def get_processed_count(self) -> int:
        """Get count of processed messages."""
        return len(self.processed_messages)

    def clear_old_processed_ids(self, days: int = 30):
        """
        Clear processed message IDs older than specified days.

        This prevents the processed set from growing indefinitely.
        WhatsApp message IDs contain timestamps, so we can parse them.

        Args:
            days: Number of days to retain processed IDs
        """
        # Implementation would parse message IDs and filter by timestamp
        # For now, this is a placeholder for future optimization
        logger.debug(f"Clearing processed IDs older than {days} days (not implemented)")
