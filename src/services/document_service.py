"""
Document Service - Gold Tier US3

Handles document generation using Jinja2 templates with audit log data.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import json

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import yaml

from src.models.document import Document, DocumentVersion
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


@dataclass
class DocumentGenerationParams:
    """Parameters for document generation."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_metrics: bool = True
    include_activities: bool = True
    include_decisions: bool = True
    custom_sections: Optional[Dict[str, Any]] = None


class DocumentService:
    """
    Service for generating and managing documents using Jinja2 templates.

    Features:
    - Template-based document generation
    - Context building from audit logs
    - Automatic frontmatter generation
    - Document versioning
    - Vault file management
    """

    def __init__(
        self,
        vault_path: str,
        template_dir: Optional[str] = None,
        audit_service: Optional[AuditService] = None
    ):
        """
        Initialize DocumentService.

        Args:
            vault_path: Path to Obsidian vault
            template_dir: Path to templates directory (default: .specify/templates/documents)
            audit_service: AuditService instance for data retrieval
        """
        self.vault_path = Path(vault_path)

        # Set template directory
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Try .specify/templates/documents first, fall back to templates/documents
            spec_templates = Path(".specify/templates/documents")
            alt_templates = Path("templates/documents")
            if spec_templates.exists():
                self.template_dir = spec_templates
            elif alt_templates.exists():
                self.template_dir = alt_templates
            else:
                raise ValueError(
                    "Template directory not found. Create .specify/templates/documents "
                    "or templates/documents, or specify template_dir parameter."
                )

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters['datetime_format'] = self._datetime_format
        self.env.filters['date_format'] = self._date_format
        self.env.filters['duration'] = self._duration_format

        # Audit service for data retrieval
        self.audit_service = audit_service or AuditService(vault_path=str(self.vault_path))

        logger.info(f"DocumentService initialized with template_dir={self.template_dir}")

    def _datetime_format(self, dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Jinja2 filter for datetime formatting."""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except ValueError:
                return dt
        return dt.strftime(format_str) if isinstance(dt, datetime) else str(dt)

    def _date_format(self, dt: datetime, format_str: str = "%Y-%m-%d") -> str:
        """Jinja2 filter for date formatting."""
        return self._datetime_format(dt, format_str)

    def _duration_format(self, seconds: float) -> str:
        """Jinja2 filter for duration formatting."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def build_context(
        self,
        document_type: str,
        params: DocumentGenerationParams
    ) -> Dict[str, Any]:
        """
        Build template context from audit logs and parameters.

        Args:
            document_type: Type of document (meeting_notes, status_report, etc.)
            params: Generation parameters

        Returns:
            Dict with template context data
        """
        context: Dict[str, Any] = {
            "generated_at": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None),
            "document_type": document_type
        }

        # Add date range
        if params.start_date:
            context["start_date"] = params.start_date
        if params.end_date:
            context["end_date"] = params.end_date

        # Load audit logs for the time period
        if params.start_date and params.end_date:
            logs = self._load_audit_logs(params.start_date, params.end_date)

            if params.include_activities:
                context["activities"] = self._extract_activities(logs)

            if params.include_metrics:
                context["metrics"] = self._calculate_metrics(logs)

            if params.include_decisions:
                context["decisions"] = self._extract_decisions(logs)

        # Add custom sections
        if params.custom_sections:
            context.update(params.custom_sections)

        return context

    def _load_audit_logs(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Load audit logs for the specified date range."""
        logs = []

        try:
            # Query audit logs within date range
            all_logs = self.audit_service.query_logs(
                start_time=start_date,
                end_time=end_date
            )
            logs = all_logs
            logger.info(f"Loaded {len(logs)} audit logs from {start_date} to {end_date}")
        except Exception as e:
            logger.warning(f"Failed to load audit logs: {e}")

        return logs

    def _extract_activities(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract activities from audit logs."""
        activities = []

        for log in logs:
            activity = {
                "timestamp": log.get("timestamp"),
                "action": log.get("action"),
                "details": log.get("details", ""),
                "outcome": log.get("outcome", "")
            }
            activities.append(activity)

        return activities

    def _calculate_metrics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics from audit logs."""
        metrics = {
            "total_actions": len(logs),
            "actions_by_type": {},
            "success_rate": 0.0,
            "avg_execution_time": 0.0
        }

        # Count actions by type
        for log in logs:
            action_type = log.get("action", "unknown")
            metrics["actions_by_type"][action_type] = metrics["actions_by_type"].get(action_type, 0) + 1

        # Calculate success rate
        successful = sum(1 for log in logs if log.get("outcome") == "success")
        if logs:
            metrics["success_rate"] = successful / len(logs) * 100

        # Calculate average execution time
        execution_times = [
            log.get("execution_time", 0) for log in logs
            if "execution_time" in log
        ]
        if execution_times:
            metrics["avg_execution_time"] = sum(execution_times) / len(execution_times)

        return metrics

    def _extract_decisions(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract decision points from audit logs."""
        decisions = []

        for log in logs:
            # Look for trust evaluation decisions
            if log.get("action") in ["trust_evaluation", "approval_required"]:
                decision = {
                    "timestamp": log.get("timestamp"),
                    "decision_type": log.get("action"),
                    "outcome": log.get("outcome"),
                    "rationale": log.get("details", "")
                }
                decisions.append(decision)

        return decisions

    def render_document(
        self,
        template_name: str,
        context: Dict[str, Any],
        document_id: str,
        title: str,
        document_type: str,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Document:
        """
        Render a document using a template and context.

        Args:
            template_name: Template filename (e.g., "weekly-status.md.j2")
            context: Template context data
            document_id: Unique document identifier
            title: Document title
            document_type: Type of document
            folder: Vault folder path
            tags: Document tags

        Returns:
            Document instance with rendered content

        Raises:
            TemplateNotFound: If template doesn't exist
        """
        try:
            # Load template
            template = self.env.get_template(template_name)

            # Render content
            content = template.render(**context)

            # Create Document instance
            doc = Document(
                document_id=document_id,
                title=title,
                document_type=document_type,
                template_used=template_name,
                folder=folder,
                tags=tags or [],
                generation_source="audit_logs",
                generation_params={
                    "start_date": context.get("start_date").isoformat() if context.get("start_date") else None,
                    "end_date": context.get("end_date").isoformat() if context.get("end_date") else None,
                },
                created_by="ai",
                status="draft"
            )

            # Store rendered content in a temporary attribute (not persisted)
            # This will be used when saving to file
            object.__setattr__(doc, '_rendered_content', content)

            logger.info(f"Rendered document {document_id} using template {template_name}")
            return doc

        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to render document: {e}")
            raise

    def save_document(
        self,
        doc: Document,
        content: Optional[str] = None,
        encrypt: bool = False
    ) -> Path:
        """
        Save document to vault with frontmatter.

        Args:
            doc: Document instance
            content: Document content (if not using _rendered_content)
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Path to saved file
        """
        # Get file path
        file_path = Path(doc.get_file_path(str(self.vault_path)))

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Get content (either from parameter or _rendered_content attribute)
        if content is None:
            content = getattr(doc, '_rendered_content', '')

        # Convert to markdown with frontmatter
        markdown = doc.to_markdown(content, encrypt=encrypt)

        # Write file
        file_path.write_text(markdown, encoding='utf-8')

        logger.info(f"Saved document to {file_path}")
        return file_path

    def create_new_version(
        self,
        doc: Document,
        content: str,
        encrypt: bool = False
    ) -> tuple[Document, Path]:
        """
        Create a new version of an existing document.

        Args:
            doc: Existing document
            content: New content
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Tuple of (new_document, file_path)
        """
        # Create new version
        new_doc = doc.create_new_version()

        # Store content
        object.__setattr__(new_doc, '_rendered_content', content)

        # Update status to draft
        object.__setattr__(new_doc, 'status', 'draft')
        object.__setattr__(new_doc, 'last_modified', datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None))

        # Save to file
        file_path = self.save_document(new_doc, content, encrypt)

        logger.info(f"Created version {new_doc.version} of document {doc.document_id}")
        return new_doc, file_path

    def generate_weekly_status(
        self,
        week_start: Optional[datetime] = None,
        encrypt: bool = False
    ) -> tuple[Document, Path]:
        """
        Generate a weekly status report.

        Args:
            week_start: Start of week (default: last Monday)
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Tuple of (document, file_path)
        """
        # Default to last Monday if not specified
        if week_start is None:
            today = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=7)

        # Build context
        params = DocumentGenerationParams(
            start_date=week_start,
            end_date=week_end,
            include_metrics=True,
            include_activities=True,
            include_decisions=True
        )
        context = self.build_context("status_report", params)

        # Generate document ID
        doc_id = f"DOC_weekly_status_{week_start.strftime('%Y_%m_%d')}"
        title = f"Weekly Status Report - Week of {week_start.strftime('%B %d, %Y')}"

        # Render document
        doc = self.render_document(
            template_name="weekly-status.md.j2",
            context=context,
            document_id=doc_id,
            title=title,
            document_type="status_report",
            folder="Documents/Status Reports",
            tags=["weekly", "status", f"{week_start.year}-Q{(week_start.month-1)//3+1}"]
        )

        # Save document
        file_path = self.save_document(doc, encrypt=encrypt)

        return doc, file_path

    def generate_meeting_notes(
        self,
        meeting_title: str,
        meeting_date: datetime,
        attendees: List[str],
        agenda: Optional[str] = None,
        encrypt: bool = False
    ) -> tuple[Document, Path]:
        """
        Generate meeting notes document.

        Args:
            meeting_title: Title of the meeting
            meeting_date: Date of the meeting
            attendees: List of attendee names/emails
            agenda: Meeting agenda
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Tuple of (document, file_path)
        """
        # Build context
        context = {
            "meeting_title": meeting_title,
            "meeting_date": meeting_date,
            "attendees": attendees,
            "agenda": agenda,
            "generated_at": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        }

        # Generate document ID
        safe_title = "".join(c if c.isalnum() else '_' for c in meeting_title)
        doc_id = f"DOC_meeting_{safe_title}_{meeting_date.strftime('%Y_%m_%d')}"
        title = f"Meeting Notes: {meeting_title}"

        # Render document
        doc = self.render_document(
            template_name="meeting-notes.md.j2",
            context=context,
            document_id=doc_id,
            title=title,
            document_type="meeting_notes",
            folder="Documents/Meetings",
            tags=["meeting", meeting_date.strftime("%Y-%m")]
        )

        # Save document
        file_path = self.save_document(doc, encrypt=encrypt)

        return doc, file_path

    def generate_monthly_summary(
        self,
        month: Optional[datetime] = None,
        encrypt: bool = False
    ) -> tuple[Document, Path]:
        """
        Generate a monthly summary report.

        Args:
            month: Month to summarize (default: last month)
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Tuple of (document, file_path)
        """
        # Default to last month if not specified
        if month is None:
            today = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
            month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        # Get month boundaries
        month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month.month == 12:
            month_end = month.replace(year=month.year+1, month=1, day=1)
        else:
            month_end = month.replace(month=month.month+1, day=1)

        # Build context
        params = DocumentGenerationParams(
            start_date=month_start,
            end_date=month_end,
            include_metrics=True,
            include_activities=True,
            include_decisions=True
        )
        context = self.build_context("monthly_summary", params)

        # Generate document ID
        doc_id = f"DOC_monthly_summary_{month.strftime('%Y_%m')}"
        title = f"Monthly Summary - {month.strftime('%B %Y')}"

        # Render document
        doc = self.render_document(
            template_name="monthly-summary.md.j2",
            context=context,
            document_id=doc_id,
            title=title,
            document_type="monthly_summary",
            folder="Documents/Summaries",
            tags=["monthly", "summary", f"{month.year}-Q{(month.month-1)//3+1}"]
        )

        # Save document
        file_path = self.save_document(doc, encrypt=encrypt)

        return doc, file_path
