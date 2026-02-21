"""
FileDrop Entity Model for Personal AI Employee - Bronze Tier MVP

Represents files manually dropped into the /Inbox folder.
Implements Entity 2 from data-model.md

Attributes:
    type: Entity type identifier (always "file_drop")
    original_name: Original filename
    file_path: Absolute path to copied file in vault
    size: File size in bytes
    file_type: File extension (with dot, e.g., ".pdf")
    received: Timestamp when file was detected (ISO 8601)
    status: Processing status ("pending", "quarantined", "done")
    quarantined: Whether file was quarantined for safety
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from pathlib import Path
import yaml


# Unsafe file extensions per FR-011 and Contract 2
UNSAFE_EXTENSIONS = {'.exe', '.dmg', '.app', '.bat', '.sh', '.cmd', '.msi', '.dll'}


@dataclass
class FileDrop:
    """FileDrop entity with YAML frontmatter serialization."""

    # Required attributes
    original_name: str
    file_path: str
    size: int
    file_type: str
    received: datetime
    status: Literal["pending", "quarantined", "done"] = "pending"
    quarantined: bool = False

    # Type identifier (constant)
    type: str = field(default="file_drop", init=False)

    def to_frontmatter(self) -> dict:
        """
        Convert FileDrop to YAML frontmatter dictionary.

        Returns:
            dict: Frontmatter data ready for YAML serialization
        """
        return {
            "type": self.type,
            "original_name": self.original_name,
            "file_path": self.file_path,
            "size": self.size,
            "file_type": self.file_type,
            "received": self.received.isoformat(),
            "status": self.status,
            "quarantined": self.quarantined,
        }

    @classmethod
    def from_frontmatter(cls, frontmatter: dict) -> "FileDrop":
        """
        Create FileDrop instance from YAML frontmatter dictionary.

        Args:
            frontmatter: Dictionary containing file metadata

        Returns:
            FileDrop: FileDrop instance
        """
        return cls(
            original_name=frontmatter["original_name"],
            file_path=frontmatter["file_path"],
            size=frontmatter["size"],
            file_type=frontmatter["file_type"],
            received=datetime.fromisoformat(frontmatter["received"]),
            status=frontmatter.get("status", "pending"),
            quarantined=frontmatter.get("quarantined", False),
        )

    def to_markdown(self, vault_path: Path) -> str:
        """
        Generate complete Markdown file content with frontmatter and body.

        Format matches Contract 2 from contracts/file-interfaces.md

        Args:
            vault_path: Path to vault root for relative path calculation

        Returns:
            str: Complete markdown file content
        """
        frontmatter_yaml = yaml.dump(
            self.to_frontmatter(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Calculate relative path for display
        try:
            file_path_obj = Path(self.file_path)
            relative_path = file_path_obj.relative_to(vault_path)
        except ValueError:
            relative_path = Path(self.file_path).name

        # Format file size in human-readable format
        human_size = self._format_file_size()

        # Get file type description
        file_type_desc = self._get_file_type_description()

        # Generate suggested actions
        actions = self._generate_suggested_actions()

        markdown_content = f"""---
{frontmatter_yaml.strip()}
---

## File Information

A new file was dropped into the Inbox for processing.

**Location**: `{relative_path}`
**Size**: {human_size}
**Type**: {file_type_desc}

## Suggested Actions

{actions}
"""
        return markdown_content

    def _format_file_size(self) -> str:
        """
        Format file size in human-readable format.

        Returns:
            str: Formatted file size (e.g., "512.00 KB")
        """
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def _get_file_type_description(self) -> str:
        """
        Get human-readable file type description.

        Returns:
            str: File type description
        """
        type_map = {
            '.pdf': 'PDF Document',
            '.doc': 'Word Document',
            '.docx': 'Word Document',
            '.xls': 'Excel Spreadsheet',
            '.xlsx': 'Excel Spreadsheet',
            '.txt': 'Text File',
            '.jpg': 'JPEG Image',
            '.jpeg': 'JPEG Image',
            '.png': 'PNG Image',
            '.gif': 'GIF Image',
            '.zip': 'ZIP Archive',
            '.csv': 'CSV Data File',
            '.json': 'JSON Data File',
            '.md': 'Markdown Document',
        }
        return type_map.get(self.file_type.lower(), f'{self.file_type.upper()} File')

    def _generate_suggested_actions(self) -> str:
        """
        Generate suggested action checkboxes based on file type.

        Returns:
            str: Checkbox list of suggested actions
        """
        actions = []

        if self.quarantined:
            actions.append("- [ ] ⚠️ Review quarantined file - UNSAFE FILE TYPE")
            actions.append("- [ ] Verify file source and purpose")
            actions.append("- [ ] Delete if suspicious")
        else:
            actions.append("- [ ] Review file content")

            # File type specific actions
            if self.file_type.lower() in ['.pdf', '.doc', '.docx']:
                actions.append("- [ ] Extract key information")
                actions.append("- [ ] File in appropriate folder")
            elif self.file_type.lower() in ['.xls', '.xlsx', '.csv']:
                actions.append("- [ ] Analyze data")
                actions.append("- [ ] Update records if needed")
            elif self.file_type.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                actions.append("- [ ] Review image content")
                actions.append("- [ ] Archive or process as needed")

            actions.append("- [ ] Move to /Done/ when complete")

        return "\n".join(actions)

    def is_unsafe(self) -> bool:
        """
        Check if file type is unsafe per FR-011.

        Returns:
            bool: True if file should be quarantined
        """
        return self.file_type.lower() in UNSAFE_EXTENSIONS

    def validate(self) -> bool:
        """
        Validate FileDrop attributes according to data-model.md rules.

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        # Validate filename
        if not self.original_name or not isinstance(self.original_name, str):
            raise ValueError("original_name must be a non-empty string")

        # Validate file path
        if not self.file_path:
            raise ValueError("file_path must be specified")

        # Validate size (must be > 0 and < 100MB per data-model.md)
        if self.size <= 0:
            raise ValueError(f"File size must be positive: {self.size}")

        if self.size > 100 * 1024 * 1024:  # 100 MB
            raise ValueError(f"File size exceeds 100MB limit: {self.size}")

        # Validate file_type (must start with ".")
        if not self.file_type.startswith("."):
            raise ValueError(f"file_type must start with '.': {self.file_type}")

        # Validate status
        if self.status not in ["pending", "quarantined", "done"]:
            raise ValueError(f"Invalid status: {self.status}")

        return True


def create_filedrop_filename(original_name: str, timestamp: datetime) -> str:
    """
    Generate standardized filename for FileDrop metadata file.

    Format: FILE_{timestamp}_{original_name}.md

    Args:
        original_name: Original filename
        timestamp: When file was detected

    Returns:
        str: Filename for metadata markdown file
    """
    # Format timestamp as YYYYMMDD_HHMMSS
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Remove extension from original name for metadata filename
    name_without_ext = Path(original_name).stem

    return f"FILE_{ts_str}_{name_without_ext}.md"


def create_copied_filename(original_name: str, timestamp: datetime) -> str:
    """
    Generate filename for copied file with timestamp to avoid conflicts.

    Format: {name}_{timestamp}.{ext}

    Args:
        original_name: Original filename
        timestamp: When file was detected

    Returns:
        str: Filename for copied file
    """
    path = Path(original_name)
    name_stem = path.stem
    extension = path.suffix

    # Format timestamp as YYYYMMDD_HHMMSS
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

    return f"{name_stem}_{ts_str}{extension}"
