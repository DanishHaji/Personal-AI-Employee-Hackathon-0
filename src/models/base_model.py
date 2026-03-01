"""
Base Model for Personal AI Employee - Gold Tier

Provides common functionality for all entity models:
- Frontmatter serialization/deserialization
- JSON Schema validation
- Encryption support for sensitive fields
- Markdown file generation

Usage:
    @dataclass
    class Contact(BaseModel):
        contact_id: str
        name: str
        email: str
        encryption_status: bool = False

        ENCRYPTED_FIELDS = ["notes", "phone"]  # Fields to encrypt if encryption_status=True

        def get_schema_name(self) -> str:
            return "contact-schema"

Then use:
    contact = Contact(contact_id="CONTACT_123", name="John", email="john@example.com")
    contact.validate()  # JSON Schema validation
    frontmatter = contact.to_frontmatter()
    markdown = contact.to_markdown()  # With encryption if needed
"""

import json
import logging
import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, ClassVar
from abc import ABC, abstractmethod

try:
    from jsonschema import validate, ValidationError
except ImportError:
    validate = None
    ValidationError = None

from src.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)


@dataclass
class BaseModel(ABC):
    """
    Abstract base model for all Gold Tier entities.

    Provides:
    - to_frontmatter() / from_frontmatter() serialization
    - JSON Schema validation
    - Encryption support for sensitive fields
    - Markdown generation with frontmatter
    """

    # Class-level constants
    ENCRYPTED_FIELDS: ClassVar[List[str]] = []  # Fields to encrypt (override in subclass)
    SCHEMA_DIR: ClassVar[Path] = Path("specs/003-gold-tier-upgrade/contracts")

    # Type identifier
    type: str = field(default="base_entity", init=False)

    def to_frontmatter(self, encrypt: bool = False) -> Dict[str, Any]:
        """
        Convert model to YAML frontmatter dictionary.

        Args:
            encrypt: Whether to encrypt sensitive fields

        Returns:
            dict: Frontmatter data ready for YAML serialization
        """
        # Convert dataclass to dict
        data = asdict(self)

        # Remove internal fields
        data.pop('type', None)

        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        # Encrypt sensitive fields if requested
        if encrypt and hasattr(self, 'encryption_status') and self.encryption_status:
            encryption_service = get_encryption_service()
            for field_name in self.ENCRYPTED_FIELDS:
                if field_name in data and data[field_name] is not None:
                    data = encryption_service.encrypt_dict_field(data, field_name)

        return data

    @classmethod
    def from_frontmatter(cls, frontmatter: Dict[str, Any], decrypt: bool = False) -> "BaseModel":
        """
        Create model instance from YAML frontmatter dictionary.

        Args:
            frontmatter: Dictionary containing entity metadata
            decrypt: Whether to decrypt sensitive fields

        Returns:
            BaseModel: Model instance
        """
        # Decrypt sensitive fields if requested
        if decrypt and frontmatter.get('encryption_status', False):
            encryption_service = get_encryption_service()
            for field_name in cls.ENCRYPTED_FIELDS:
                if field_name in frontmatter and frontmatter[field_name] is not None:
                    frontmatter = encryption_service.decrypt_dict_field(frontmatter, field_name)

        # Convert ISO strings back to datetime objects (if needed)
        for key, value in frontmatter.items():
            if isinstance(value, str) and 'T' in value:
                try:
                    frontmatter[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass  # Not a datetime string

        return cls(**frontmatter)

    def to_markdown(self, body: str = "", encrypt: bool = False) -> str:
        """
        Generate complete Markdown file content with frontmatter and body.

        Args:
            body: Markdown body content
            encrypt: Whether to encrypt sensitive fields in frontmatter

        Returns:
            str: Complete markdown file content
        """
        frontmatter_dict = self.to_frontmatter(encrypt=encrypt)

        frontmatter_yaml = yaml.dump(
            frontmatter_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        markdown_content = f"""---
{frontmatter_yaml.strip()}
---

{body.strip()}
"""
        return markdown_content

    @abstractmethod
    def get_schema_name(self) -> Optional[str]:
        """
        Get JSON Schema filename for validation.

        Returns:
            str: Schema filename (e.g., "trust-rule-schema.json") or None if no schema
        """
        pass

    def validate(self) -> bool:
        """
        Validate model against JSON Schema (if available).

        Returns:
            bool: True if valid

        Raises:
            ValueError: If validation fails or schema not found
        """
        schema_name = self.get_schema_name()

        # If no schema defined, skip validation
        if schema_name is None:
            logger.debug(f"{self.__class__.__name__}: No schema defined, skipping validation")
            return True

        # Check if jsonschema is available
        if validate is None or ValidationError is None:
            logger.warning("jsonschema library not available, skipping validation")
            return True

        # Load schema
        schema_path = self.SCHEMA_DIR / schema_name
        if not schema_path.exists():
            logger.warning(f"Schema not found: {schema_path}, skipping validation")
            return True

        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load schema {schema_path}: {e}")
            raise ValueError(f"Invalid schema file: {schema_name}")

        # Validate
        data = self.to_frontmatter()

        try:
            validate(instance=data, schema=schema)
            logger.debug(f"{self.__class__.__name__} validated successfully against {schema_name}")
            return True
        except ValidationError as e:
            logger.error(f"{self.__class__.__name__} validation failed: {e.message}")
            raise ValueError(f"Validation error: {e.message}")

    def save_to_file(
        self,
        file_path: str | Path,
        body: str = "",
        encrypt: bool = False
    ) -> Path:
        """
        Save model to markdown file.

        Args:
            file_path: Path to save file
            body: Markdown body content
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Path: Path to saved file
        """
        file_path = Path(file_path)

        # Generate markdown content
        markdown_content = self.to_markdown(body=body, encrypt=encrypt)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        logger.info(f"Saved {self.__class__.__name__} to {file_path}")
        return file_path

    @classmethod
    def load_from_file(
        cls,
        file_path: str | Path,
        decrypt: bool = False
    ) -> tuple["BaseModel", str]:
        """
        Load model from markdown file.

        Args:
            file_path: Path to markdown file
            decrypt: Whether to decrypt sensitive fields

        Returns:
            tuple: (model_instance, body_content)
        """
        file_path = Path(file_path)

        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter and body
        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid markdown file format: {file_path}")

        frontmatter_yaml = parts[1]
        body = parts[2].strip()

        # Parse YAML
        frontmatter = yaml.safe_load(frontmatter_yaml)

        # Create model instance
        model_instance = cls.from_frontmatter(frontmatter, decrypt=decrypt)

        return model_instance, body


class SimpleEntity(BaseModel):
    """
    Simple entity without JSON Schema validation.

    Use this for simple entities that don't need complex validation
    (Document, Insight, ProactiveSuggestion, Expense, etc.)
    """

    def get_schema_name(self) -> Optional[str]:
        """No schema validation for simple entities."""
        return None


# Helper functions

def parse_markdown_with_frontmatter(
    file_path: str | Path,
    model_class: type[BaseModel],
    decrypt: bool = False
) -> tuple[BaseModel, str]:
    """
    Parse markdown file and return model instance + body.

    Args:
        file_path: Path to markdown file
        model_class: Model class to instantiate
        decrypt: Whether to decrypt sensitive fields

    Returns:
        tuple: (model_instance, body_content)
    """
    return model_class.load_from_file(file_path, decrypt=decrypt)


def save_entity_to_vault(
    entity: BaseModel,
    vault_path: str | Path,
    subfolder: str,
    filename: str,
    body: str = "",
    encrypt: bool = False
) -> Path:
    """
    Save entity to vault with standard file structure.

    Args:
        entity: Entity instance to save
        vault_path: Path to vault root
        subfolder: Subfolder within vault (e.g., "Contacts", "Expenses")
        filename: Filename (e.g., "CONTACT_john_smith.md")
        body: Markdown body content
        encrypt: Whether to encrypt sensitive fields

    Returns:
        Path: Path to saved file
    """
    vault_path = Path(vault_path)
    file_path = vault_path / subfolder / filename

    return entity.save_to_file(file_path, body=body, encrypt=encrypt)
