"""
Document Model - Gold Tier US3

Represents a generated document with version tracking and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from src.models.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class DocumentVersion:
    """Represents a previous version of a document."""
    version: int
    timestamp: datetime
    document_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "document_id": self.document_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentVersion":
        """Create from dictionary."""
        return cls(
            version=data["version"],
            timestamp=datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00')),
            document_id=data["document_id"]
        )


@dataclass
class Document(BaseModel):
    """
    Generated document with version tracking.

    Attributes:
        document_id: Unique identifier (DOC_xxx format)
        title: Document title
        document_type: Type (meeting_notes, status_report, etc.)
        template_used: Template filename used for generation
        folder: Folder path in vault
        tags: Document tags for organization
        generation_source: Source of data (audit_logs, meeting_notes, etc.)
        generation_params: Parameters used during generation
        created_at: Creation timestamp
        created_by: Creator (ai or user)
        last_modified: Last modification timestamp
        version: Document version number
        previous_versions: History of previous versions
        status: Document status (draft, final, archived)
        encryption_status: Whether sensitive fields are encrypted
    """

    document_id: str
    title: str
    document_type: str
    template_used: str
    version: int = 1
    created_by: str = "ai"
    status: str = "draft"

    # Optional fields
    folder: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    generation_source: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    previous_versions: List[DocumentVersion] = field(default_factory=list)
    encryption_status: bool = False

    def __post_init__(self):
        """Initialize timestamps and validate."""
        # Set type identifier
        object.__setattr__(self, 'type', 'document')

        # Set timestamps if not provided
        if self.created_at is None:
            object.__setattr__(self, 'created_at', datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None))
        if self.last_modified is None:
            object.__setattr__(self, 'last_modified', self.created_at)

        # Validate document_type
        valid_types = [
            "meeting_notes", "status_report", "monthly_summary",
            "proposal", "memo", "analysis", "other"
        ]
        if self.document_type not in valid_types:
            raise ValueError(f"document_type must be one of {valid_types}")

        # Validate status
        if self.status not in ["draft", "final", "archived"]:
            raise ValueError("status must be draft, final, or archived")

        # Validate created_by
        if self.created_by not in ["ai", "user"]:
            raise ValueError("created_by must be ai or user")

        # Validate version
        if self.version < 1:
            raise ValueError("version must be >= 1")

    @classmethod
    def get_schema_name(cls) -> Optional[str]:
        """Return JSON Schema filename for validation."""
        return "document-schema.json"

    def create_new_version(self) -> "Document":
        """
        Create a new version of this document.

        Returns:
            Document: New document with incremented version
        """
        # Add current version to history
        current_version = DocumentVersion(
            version=self.version,
            timestamp=self.last_modified or self.created_at,
            document_id=self.document_id
        )

        # Create new document with incremented version
        new_doc = Document(
            document_id=f"{self.document_id}_v{self.version + 1}",
            title=self.title,
            document_type=self.document_type,
            template_used=self.template_used,
            folder=self.folder,
            tags=self.tags.copy(),
            generation_source=self.generation_source,
            generation_params=self.generation_params.copy() if self.generation_params else None,
            created_by=self.created_by,
            version=self.version + 1,
            previous_versions=self.previous_versions + [current_version],
            status="draft",
            encryption_status=self.encryption_status
        )

        return new_doc

    def to_frontmatter(self, encrypt: bool = False) -> Dict[str, Any]:
        """
        Convert to YAML frontmatter dictionary.

        Args:
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Dict with document data
        """
        data = super().to_frontmatter(encrypt=encrypt)

        # Convert datetime objects to ISO strings
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.last_modified:
            data["last_modified"] = self.last_modified.isoformat()

        # Convert previous versions to dicts
        if self.previous_versions:
            data["previous_versions"] = [v.to_dict() for v in self.previous_versions]

        return data

    @classmethod
    def from_frontmatter(cls, data: Dict[str, Any]) -> "Document":
        """
        Create Document from frontmatter dictionary.

        Args:
            data: Dictionary from YAML frontmatter

        Returns:
            Document instance
        """
        # Parse datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        if isinstance(data.get("last_modified"), str):
            data["last_modified"] = datetime.fromisoformat(data["last_modified"].replace('Z', '+00:00'))

        # Parse previous versions
        if data.get("previous_versions"):
            data["previous_versions"] = [
                DocumentVersion.from_dict(v) for v in data["previous_versions"]
            ]

        # Remove BaseModel fields before creating instance
        data.pop("ENCRYPTED_FIELDS", None)
        data.pop("type", None)

        return cls(**data)

    def get_file_path(self, vault_path: str) -> str:
        """
        Get the file path for this document in the vault.

        Args:
            vault_path: Path to Obsidian vault

        Returns:
            str: Full file path (e.g., /vault/Documents/Status Reports/doc.md)
        """
        from pathlib import Path

        base_path = Path(vault_path)

        if self.folder:
            folder_path = base_path / self.folder
        else:
            folder_path = base_path / "Documents"

        # Create safe filename from title
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in self.title)
        safe_title = safe_title.replace(' ', '_')

        filename = f"{safe_title}.md"
        return str(folder_path / filename)

    def to_markdown(self, content: str, encrypt: bool = False) -> str:
        """
        Convert to markdown file with frontmatter.

        Args:
            content: Document content (body)
            encrypt: Whether to encrypt sensitive fields

        Returns:
            str: Full markdown document with YAML frontmatter
        """
        import yaml

        frontmatter = self.to_frontmatter(encrypt=encrypt)

        # Build markdown
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        markdown = f"---\n{yaml_str}---\n\n{content}"

        return markdown
