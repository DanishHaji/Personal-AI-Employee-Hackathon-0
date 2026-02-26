"""
VaultService for Personal AI Employee - Bronze Tier MVP

Handles reading/writing markdown files with YAML frontmatter in the Obsidian vault.
Provides file operations for Email, FileDrop, and other entities.

Core functionality:
- Read markdown files with frontmatter parsing
- Write markdown files with frontmatter serialization
- Move files between vault folders
- Count files in directories
- Atomic file operations
"""

import re
from pathlib import Path
from typing import Dict, Any, Tuple, List
import yaml


class VaultService:
    """Service for Obsidian vault file operations."""

    def __init__(self, vault_path: str | Path):
        """
        Initialize VaultService with vault path.

        Args:
            vault_path: Absolute path to Obsidian vault root
        """
        self.vault_path = Path(vault_path).resolve()

        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")

    def read_markdown_with_frontmatter(
        self, file_path: str | Path
    ) -> Tuple[Dict[str, Any], str]:
        """
        Read markdown file and parse YAML frontmatter.

        Format expected:
        ---
        key: value
        ---

        Body content here

        Args:
            file_path: Path to markdown file (absolute or relative to vault)

        Returns:
            Tuple[dict, str]: (frontmatter dict, body content)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If frontmatter is malformed
        """
        file_path = self._resolve_path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter using regex
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)

        if not match:
            # No frontmatter found, return empty dict and full content as body
            return {}, content

        frontmatter_text = match.group(1)
        body = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            if frontmatter is None:
                frontmatter = {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter in {file_path}: {e}")

        return frontmatter, body

    def write_markdown_with_frontmatter(
        self,
        file_path: str | Path,
        frontmatter: Dict[str, Any],
        body: str
    ) -> None:
        """
        Write markdown file with YAML frontmatter.

        Uses atomic write pattern (write to temp, then rename) to avoid corruption.

        Args:
            file_path: Path to markdown file (absolute or relative to vault)
            frontmatter: Dictionary to serialize as YAML frontmatter
            body: Markdown body content

        Raises:
            ValueError: If frontmatter cannot be serialized
        """
        file_path = self._resolve_path(file_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize frontmatter
        try:
            frontmatter_yaml = yaml.dump(
                frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Cannot serialize frontmatter: {e}")

        # Construct full content
        content = f"---\n{frontmatter_yaml.strip()}\n---\n\n{body}"

        # Atomic write: write to temp file, then rename
        temp_path = file_path.with_suffix('.tmp')
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(file_path)  # Atomic on most filesystems
        except Exception as e:
            # Cleanup temp file if write failed
            if temp_path.exists():
                temp_path.unlink()
            raise e

    def write_markdown(self, file_path: str | Path, content: str) -> None:
        """
        Write plain markdown file (overwrite mode).

        Args:
            file_path: Path to markdown file (absolute or relative to vault)
            content: Complete markdown content to write
        """
        file_path = self._resolve_path(file_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        temp_path = file_path.with_suffix('.tmp')
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(file_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise e

    def move_file(
        self,
        source_path: str | Path,
        dest_folder: str | Path,
        new_name: str | None = None
    ) -> Path:
        """
        Move file from source to destination folder.

        Args:
            source_path: Source file path (absolute or relative to vault)
            dest_folder: Destination folder name (e.g., "Done", "Plans")
            new_name: Optional new filename, uses original name if None

        Returns:
            Path: New file path after move

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        source_path = self._resolve_path(source_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Resolve destination folder (relative to vault root)
        dest_folder_path = self.vault_path / dest_folder
        dest_folder_path.mkdir(parents=True, exist_ok=True)

        # Determine destination filename
        filename = new_name if new_name else source_path.name
        dest_path = dest_folder_path / filename

        # Move file (rename is atomic)
        source_path.rename(dest_path)

        return dest_path

    def count_files(self, folder: str | Path, pattern: str = "*.md") -> int:
        """
        Count files in a vault folder matching pattern.

        Args:
            folder: Folder name or path (relative to vault)
            pattern: Glob pattern (default: "*.md")

        Returns:
            int: Number of matching files
        """
        folder_path = self.vault_path / folder

        if not folder_path.exists():
            return 0

        return len(list(folder_path.glob(pattern)))

    def list_files(
        self,
        folder: str | Path,
        pattern: str = "*.md",
        sort_by_mtime: bool = True
    ) -> List[Path]:
        """
        List files in a vault folder matching pattern.

        Args:
            folder: Folder name or path (relative to vault)
            pattern: Glob pattern (default: "*.md")
            sort_by_mtime: Sort by modification time (newest first)

        Returns:
            List[Path]: List of file paths
        """
        folder_path = self.vault_path / folder

        if not folder_path.exists():
            return []

        files = list(folder_path.glob(pattern))

        if sort_by_mtime:
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return files

    def file_exists(self, file_path: str | Path) -> bool:
        """
        Check if file exists in vault.

        Args:
            file_path: File path (absolute or relative to vault)

        Returns:
            bool: True if file exists
        """
        file_path = self._resolve_path(file_path)
        return file_path.exists()

    def get_vault_path(self) -> Path:
        """
        Get absolute path to vault root.

        Returns:
            Path: Vault root path
        """
        return self.vault_path

    def _resolve_path(self, file_path: str | Path) -> Path:
        """
        Resolve file path to absolute path.

        If path is relative, treats it as relative to vault root.
        If path is absolute, returns as-is.

        Args:
            file_path: File path

        Returns:
            Path: Absolute file path
        """
        path = Path(file_path)

        if path.is_absolute():
            return path

        # Relative path, resolve against vault root
        return (self.vault_path / path).resolve()

    def ensure_folder_structure(self) -> None:
        """
        Ensure all required vault folders exist.

        Creates folders per FR-001 if missing:
        - Inbox, Needs_Action, Plans, Pending_Approval, Approved, Done, Logs, Quarantine
        """
        folders = [
            "Inbox",
            "Needs_Action",
            "Plans",
            "Pending_Approval",
            "Approved",
            "Done",
            "Logs",
            "Quarantine",
        ]

        for folder in folders:
            folder_path = self.vault_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)

    # ========================================
    # Silver Tier Entity Methods
    # ========================================

    def write_whatsapp_message(
        self,
        message_id: str,
        frontmatter: Dict[str, Any],
        body: str,
        folder: str = "Needs_Action"
    ) -> Path:
        """
        Write WhatsAppMessage entity to vault.

        Args:
            message_id: Unique WhatsApp message ID
            frontmatter: Message metadata (sender_phone, sender_name, timestamp, priority, etc.)
            body: Message content
            folder: Destination folder (default: Needs_Action)

        Returns:
            Path: Path to created file
        """
        filename = f"WHATSAPP_{message_id}.md"
        file_path = self.vault_path / folder / filename

        self.write_markdown_with_frontmatter(file_path, frontmatter, body)

        return file_path

    def write_social_media_post(
        self,
        post_id: str,
        frontmatter: Dict[str, Any],
        body: str,
        folder: str = "Approved"
    ) -> Path:
        """
        Write SocialMediaPost entity to vault.

        Args:
            post_id: Unique post ID (format: POST_[platform]_[timestamp])
            frontmatter: Post metadata (platforms, status, scheduled_time, platform_results, etc.)
            body: Post content
            folder: Destination folder (default: Approved)

        Returns:
            Path: Path to created file
        """
        filename = f"{post_id}.md"
        file_path = self.vault_path / folder / filename

        self.write_markdown_with_frontmatter(file_path, frontmatter, body)

        return file_path

    def write_scheduled_task(
        self,
        task_id: str,
        frontmatter: Dict[str, Any],
        body: str
    ) -> Path:
        """
        Write or update ScheduledTask in Company_Handbook.md.

        Note: Scheduled tasks are stored in Company_Handbook.md, not as separate files.
        This method updates the handbook file with task definition.

        Args:
            task_id: Unique task ID
            frontmatter: Task metadata (task_name, schedule_pattern, recurrence_rule, etc.)
            body: Task description and instructions

        Returns:
            Path: Path to Company_Handbook.md
        """
        handbook_path = self.vault_path / "Company_Handbook.md"

        # Read existing handbook
        if handbook_path.exists():
            existing_frontmatter, existing_body = self.read_markdown_with_frontmatter(
                handbook_path
            )
        else:
            existing_frontmatter = {}
            existing_body = ""

        # Add or update scheduled_tasks section
        if 'scheduled_tasks' not in existing_frontmatter:
            existing_frontmatter['scheduled_tasks'] = []

        # Find existing task or add new one
        tasks = existing_frontmatter['scheduled_tasks']
        task_found = False

        for i, task in enumerate(tasks):
            if task.get('task_id') == task_id:
                tasks[i] = frontmatter
                task_found = True
                break

        if not task_found:
            tasks.append(frontmatter)

        # Write updated handbook
        self.write_markdown_with_frontmatter(
            handbook_path,
            existing_frontmatter,
            existing_body
        )

        return handbook_path

    def write_execution_log(
        self,
        log_entry: Dict[str, Any],
        date_str: str | None = None
    ) -> Path:
        """
        Append execution log entry to daily log file.

        Args:
            log_entry: Log entry dictionary (log_id, timestamp, action_type, result, etc.)
            date_str: Date string (YYYY-MM-DD) for log file, uses today if None

        Returns:
            Path: Path to log file
        """
        from datetime import datetime
        import json

        # Determine log file name
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        log_file = self.vault_path / "Logs" / f"{date_str}.json"

        # Ensure Logs directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Append log entry (newline-delimited JSON format)
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')

        return log_file

    def list_approved_plans(self) -> List[Tuple[Path, Dict[str, Any]]]:
        """
        List all plans in /Approved/ folder with their frontmatter.

        Returns:
            List[Tuple[Path, Dict]]: List of (file_path, frontmatter) tuples
        """
        approved_files = self.list_files("Approved", "*.md")
        plans = []

        for file_path in approved_files:
            try:
                frontmatter, _ = self.read_markdown_with_frontmatter(file_path)
                plans.append((file_path, frontmatter))
            except Exception as e:
                # Skip files that can't be read
                print(f"Warning: Could not read {file_path}: {e}")

        return plans

    def get_entity_count(self, folder: str, entity_prefix: str = "") -> int:
        """
        Count entities in a folder by prefix.

        Args:
            folder: Folder name (e.g., "Needs_Action", "Done")
            entity_prefix: Optional prefix to filter (e.g., "WHATSAPP_", "POST_")

        Returns:
            int: Count of matching entities
        """
        if entity_prefix:
            pattern = f"{entity_prefix}*.md"
        else:
            pattern = "*.md"

        return self.count_files(folder, pattern)
