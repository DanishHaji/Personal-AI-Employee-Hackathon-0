"""
GmailService for Personal AI Employee - Bronze Tier MVP

Handles Gmail API authentication and query operations.
Implements OAuth2 flow per research.md Section 2.

Features:
- OAuth2 authentication with token refresh
- Query emails by labels and keywords
- Fetch email metadata and snippets
- Rate limit handling with exponential backoff

Requirements:
- Gmail API enabled in Google Cloud Console
- credentials.json file with OAuth2 client ID/secret
- Gmail API scope: gmail.readonly (read-only access)
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time


# Gmail API scope - read-only per Bronze Tier requirements
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailService:
    """Service for Gmail API operations with OAuth2 authentication."""

    def __init__(
        self,
        credentials_path: str | Path,
        token_path: str | Path
    ):
        """
        Initialize GmailService with credential paths.

        Args:
            credentials_path: Path to credentials.json (OAuth2 client credentials)
            token_path: Path to token.json (saved user token)

        Raises:
            FileNotFoundError: If credentials_path doesn't exist
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)

        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail credentials not found: {self.credentials_path}\n"
                f"Download credentials.json from Google Cloud Console"
            )

        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """
        Authenticate with Gmail API using OAuth2 flow.

        Flow per research.md Section 2:
        1. Check if token.json exists and is valid
        2. If expired, refresh using refresh_token
        3. If no token, run OAuth2 flow and save token
        4. Build Gmail API service
        """
        creds = None

        # Load existing token if available
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired token
                print("[GmailService] Refreshing expired token...")
                creds.refresh(Request())
            else:
                # Run OAuth2 flow for first-time authentication
                print("[GmailService] Starting OAuth2 authentication flow...")
                print("[GmailService] Browser will open for authorization")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                print("[GmailService] Authentication successful!")

            # Save token for future use
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            print(f"[GmailService] Token saved to {self.token_path}")

        # Build Gmail API service
        self.service = build('gmail', 'v1', credentials=creds)
        print("[GmailService] Gmail API service initialized")

    def query_emails(
        self,
        query: str,
        max_results: int = 10,
        include_spam_trash: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Query emails using Gmail search syntax.

        Args:
            query: Gmail query string (e.g., "is:unread is:important")
            max_results: Maximum number of results to return (default: 10)
            include_spam_trash: Include spam/trash folders (default: False)

        Returns:
            List[dict]: List of email metadata dictionaries with keys:
                - id: Gmail message ID
                - threadId: Thread ID
                - snippet: Email snippet
                - from: Sender email
                - subject: Email subject
                - date: Received timestamp
                - labels: List of label names

        Raises:
            HttpError: If Gmail API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized. Call _authenticate() first.")

        try:
            # Query messages with exponential backoff
            results = self._api_call_with_retry(
                lambda: self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results,
                    includeSpamTrash=include_spam_trash
                ).execute()
            )

            messages = results.get('messages', [])

            # Fetch full metadata for each message
            detailed_messages = []
            for msg in messages:
                msg_id = msg['id']
                detailed_msg = self.get_email_metadata(msg_id)
                if detailed_msg:
                    detailed_messages.append(detailed_msg)

            return detailed_messages

        except HttpError as error:
            print(f"[GmailService] API error: {error}")
            raise

    def get_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full metadata for a specific email.

        Args:
            message_id: Gmail message ID

        Returns:
            dict: Email metadata with keys:
                - id: Gmail message ID
                - threadId: Thread ID
                - snippet: Email snippet (first ~200 chars)
                - from: Sender email
                - subject: Email subject
                - date: Received timestamp (datetime)
                - labels: List of label names
                - has_important: Boolean indicating IMPORTANT label

        Raises:
            HttpError: If Gmail API request fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            # Fetch message with metadata format
            message = self._api_call_with_retry(
                lambda: self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
            )

            # Extract headers
            headers = {
                h['name']: h['value']
                for h in message.get('payload', {}).get('headers', [])
            }

            # Parse date (Gmail returns RFC 2822 format)
            date_str = headers.get('Date', '')
            try:
                # Parse RFC 2822 date to datetime
                from email.utils import parsedate_to_datetime
                received_dt = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                # Fallback to current time if parse fails
                received_dt = datetime.now()

            # Extract labels
            label_ids = message.get('labelIds', [])
            has_important = 'IMPORTANT' in label_ids

            return {
                'id': message_id,
                'threadId': message.get('threadId'),
                'snippet': message.get('snippet', ''),
                'from': headers.get('From', ''),
                'subject': headers.get('Subject', ''),
                'date': received_dt,
                'labels': label_ids,
                'has_important': has_important,
            }

        except HttpError as error:
            print(f"[GmailService] Error fetching message {message_id}: {error}")
            return None

    def query_important_emails(
        self,
        urgent_keywords: List[str],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query unread emails that are important or contain urgent keywords.

        Implements FR-004 query logic per research.md Section 2.

        Args:
            urgent_keywords: List of urgent keywords (e.g., ["urgent", "asap", "invoice"])
            max_results: Maximum results (default: 10)

        Returns:
            List[dict]: List of important/urgent email metadata
        """
        # Build query: unread AND (important OR urgent keywords)
        keyword_queries = " OR ".join([f"subject:{kw}" for kw in urgent_keywords])
        query = f"is:unread (is:important OR {keyword_queries})"

        return self.query_emails(query, max_results)

    def _api_call_with_retry(
        self,
        api_call: callable,
        max_retries: int = 4
    ) -> Any:
        """
        Execute Gmail API call with exponential backoff for rate limits.

        Implements FR-008 rate limit handling per research.md Section 2.

        Backoff schedule: 1s, 2s, 4s, 8s

        Args:
            api_call: Callable that executes the API request
            max_retries: Maximum retry attempts (default: 4)

        Returns:
            API response

        Raises:
            HttpError: If all retries exhausted
        """
        for attempt in range(max_retries):
            try:
                return api_call()

            except HttpError as error:
                # Check if it's a rate limit error (429)
                if error.resp.status == 429:
                    if attempt < max_retries - 1:
                        delay = 2 ** attempt  # Exponential: 1, 2, 4, 8 seconds
                        print(
                            f"[GmailService] Rate limited (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        print("[GmailService] Max retries exceeded")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    raise

        # Should not reach here, but just in case
        raise RuntimeError("Max retries exceeded without successful response")

    def test_connection(self) -> bool:
        """
        Test Gmail API connection by fetching user profile.

        Returns:
            bool: True if connection successful

        Raises:
            HttpError: If connection fails
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")

        try:
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'unknown')
            print(f"[GmailService] Connected to Gmail as: {email}")
            return True

        except HttpError as error:
            print(f"[GmailService] Connection test failed: {error}")
            raise


def authenticate_gmail_cli(
    credentials_path: str,
    token_path: str
) -> None:
    """
    CLI utility for first-time Gmail authentication.

    Usage:
        python src/watchers/gmail_watcher.py --auth-only

    Args:
        credentials_path: Path to credentials.json
        token_path: Path to save token.json
    """
    print("=" * 60)
    print("Gmail API Authentication")
    print("=" * 60)
    print()

    service = GmailService(credentials_path, token_path)
    service.test_connection()

    print()
    print("✅ Authentication successful!")
    print(f"Token saved to: {token_path}")
    print()
    print("You can now start the Gmail Watcher:")
    print("  pm2 start src/watchers/gmail_watcher.py --name gmail-watcher --interpreter python3")
    print()
