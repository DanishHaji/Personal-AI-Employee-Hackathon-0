"""
Unit tests for DocumentService - Gold Tier US3

Tests document generation, template rendering, and versioning.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from src.models.document import Document, DocumentVersion
from src.services.document_service import DocumentService, DocumentGenerationParams


class TestDocumentModel:
    """Test Document model creation and validation."""

    def test_create_document(self):
        """Test creating a valid document."""
        doc = Document(
            document_id="DOC_test_001",
            title="Test Document",
            document_type="status_report",
            template_used="weekly-status.md.j2"
        )

        assert doc.document_id == "DOC_test_001"
        assert doc.title == "Test Document"
        assert doc.document_type == "status_report"
        assert doc.template_used == "weekly-status.md.j2"
        assert doc.version == 1
        assert doc.created_by == "ai"
        assert doc.status == "draft"
        assert doc.type == "document"

    def test_document_validation_invalid_type(self):
        """Test document creation with invalid document_type."""
        with pytest.raises(ValueError, match="document_type must be one of"):
            Document(
                document_id="DOC_test_002",
                title="Test",
                document_type="invalid_type",
                template_used="test.md.j2"
            )

    def test_document_validation_invalid_status(self):
        """Test document creation with invalid status."""
        with pytest.raises(ValueError, match="status must be draft, final, or archived"):
            Document(
                document_id="DOC_test_003",
                title="Test",
                document_type="status_report",
                template_used="test.md.j2",
                status="invalid_status"
            )

    def test_document_validation_invalid_version(self):
        """Test document creation with invalid version."""
        with pytest.raises(ValueError, match="version must be >= 1"):
            Document(
                document_id="DOC_test_004",
                title="Test",
                document_type="status_report",
                template_used="test.md.j2",
                version=0
            )

    def test_create_new_version(self):
        """Test creating a new version of a document."""
        doc = Document(
            document_id="DOC_test_005",
            title="Test Document",
            document_type="status_report",
            template_used="weekly-status.md.j2",
            version=1
        )

        new_doc = doc.create_new_version()

        assert new_doc.version == 2
        assert new_doc.document_id == "DOC_test_005_v2"
        assert len(new_doc.previous_versions) == 1
        assert new_doc.previous_versions[0].version == 1
        assert new_doc.status == "draft"

    def test_get_file_path(self):
        """Test getting file path for document."""
        doc = Document(
            document_id="DOC_test_006",
            title="Weekly Status Report",
            document_type="status_report",
            template_used="weekly-status.md.j2",
            folder="Documents/Status Reports"
        )

        file_path = doc.get_file_path("/vault")
        assert "/vault/Documents/Status Reports/Weekly_Status_Report.md" in file_path

    def test_to_frontmatter(self):
        """Test converting document to frontmatter dict."""
        doc = Document(
            document_id="DOC_test_007",
            title="Test Document",
            document_type="status_report",
            template_used="weekly-status.md.j2",
            tags=["test", "weekly"]
        )

        fm = doc.to_frontmatter()

        assert fm["document_id"] == "DOC_test_007"
        assert fm["title"] == "Test Document"
        assert fm["document_type"] == "status_report"
        assert "test" in fm["tags"]
        assert "weekly" in fm["tags"]


class TestDocumentService:
    """Test DocumentService functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def temp_templates(self):
        """Create temporary template directory."""
        temp_dir = tempfile.mkdtemp()
        template_dir = Path(temp_dir) / "templates"
        template_dir.mkdir()

        # Create test template
        test_template = template_dir / "test-template.md.j2"
        test_template.write_text("""# {{ title }}

Generated: {{ generated_at | datetime_format("%Y-%m-%d") }}

Total actions: {{ metrics.total_actions }}
""")

        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_audit_service(self):
        """Create mock audit service."""
        service = Mock()
        service.query_logs.return_value = [
            {
                "timestamp": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None).isoformat(),
                "action": "email_send",
                "details": "Sent email to john@example.com",
                "outcome": "success",
                "execution_time": 0.5
            },
            {
                "timestamp": (datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None) - timedelta(hours=1)).isoformat(),
                "action": "calendar_event",
                "details": "Created meeting",
                "outcome": "success",
                "execution_time": 0.3
            }
        ]
        service.log_action = Mock()
        return service

    def test_service_initialization(self, temp_vault, temp_templates):
        """Test DocumentService initialization."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates")
        )

        assert service.vault_path == Path(temp_vault)
        assert service.template_dir.exists()

    def test_build_context_with_metrics(self, temp_vault, temp_templates, mock_audit_service):
        """Test building template context with metrics."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates"),
            audit_service=mock_audit_service
        )

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        params = DocumentGenerationParams(
            start_date=now - timedelta(days=7),
            end_date=now,
            include_metrics=True,
            include_activities=True,
            include_decisions=False
        )

        context = service.build_context("status_report", params)

        assert "generated_at" in context
        assert "document_type" in context
        assert context["document_type"] == "status_report"
        assert "metrics" in context
        assert context["metrics"]["total_actions"] == 2
        assert "activities" in context
        assert len(context["activities"]) == 2

    def test_render_document(self, temp_vault, temp_templates, mock_audit_service):
        """Test rendering a document from template."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates"),
            audit_service=mock_audit_service
        )

        context = {
            "title": "Test Report",
            "generated_at": datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None),
            "metrics": {"total_actions": 42}
        }

        doc = service.render_document(
            template_name="test-template.md.j2",
            context=context,
            document_id="DOC_test_render_001",
            title="Test Report",
            document_type="status_report"
        )

        assert doc.document_id == "DOC_test_render_001"
        assert doc.title == "Test Report"
        assert doc.document_type == "status_report"
        assert hasattr(doc, '_rendered_content')
        assert "Total actions: 42" in doc._rendered_content

    def test_save_document(self, temp_vault, temp_templates):
        """Test saving document to vault."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates")
        )

        doc = Document(
            document_id="DOC_test_save_001",
            title="Test Document",
            document_type="status_report",
            template_used="test.md.j2",
            folder="Documents"
        )

        content = "# Test Document\n\nThis is test content."
        file_path = service.save_document(doc, content)

        assert file_path.exists()
        assert file_path.read_text(encoding='utf-8').count("# Test Document") >= 1
        assert "document_id: DOC_test_save_001" in file_path.read_text(encoding='utf-8')

    def test_create_new_version(self, temp_vault, temp_templates):
        """Test creating new document version."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates")
        )

        doc = Document(
            document_id="DOC_test_version_001",
            title="Test Document",
            document_type="status_report",
            template_used="test.md.j2",
            folder="Documents",
            version=1
        )

        new_content = "# Updated Test Document\n\nVersion 2 content."
        new_doc, file_path = service.create_new_version(doc, new_content)

        assert new_doc.version == 2
        assert new_doc.document_id == "DOC_test_version_001_v2"
        assert len(new_doc.previous_versions) == 1
        assert file_path.exists()

    def test_generate_weekly_status(self, temp_vault, mock_audit_service):
        """Test generating weekly status report."""
        # Create templates directory
        template_dir = Path(temp_vault) / ".specify" / "templates" / "documents"
        template_dir.mkdir(parents=True)

        # Create test template
        test_template = template_dir / "weekly-status.md.j2"
        test_template.write_text("""# Weekly Status

Total actions: {{ metrics.total_actions }}
Success rate: {{ metrics.success_rate }}%
""")

        service = DocumentService(
            vault_path=temp_vault,
            audit_service=mock_audit_service
        )

        week_start = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        doc, file_path = service.generate_weekly_status(week_start=week_start)

        assert doc.document_type == "status_report"
        assert "weekly" in doc.document_id.lower()
        assert file_path.exists()
        content = file_path.read_text(encoding='utf-8')
        assert "Weekly Status" in content
        assert "Total Actions" in content  # Capital A in actual template

    def test_generate_meeting_notes(self, temp_vault):
        """Test generating meeting notes."""
        # Create templates directory
        template_dir = Path(temp_vault) / ".specify" / "templates" / "documents"
        template_dir.mkdir(parents=True)

        # Create test template
        test_template = template_dir / "meeting-notes.md.j2"
        test_template.write_text("""# {{ meeting_title }}

Date: {{ meeting_date | datetime_format("%Y-%m-%d") }}

Attendees:
{% for attendee in attendees %}
- {{ attendee }}
{% endfor %}
""")

        service = DocumentService(vault_path=temp_vault)

        meeting_date = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        doc, file_path = service.generate_meeting_notes(
            meeting_title="Q2 Planning Meeting",
            meeting_date=meeting_date,
            attendees=["john@example.com", "jane@example.com"],
            agenda="Discuss Q2 objectives"
        )

        assert doc.document_type == "meeting_notes"
        assert "meeting" in doc.document_id.lower()
        assert file_path.exists()
        content = file_path.read_text(encoding='utf-8')
        assert "Q2 Planning Meeting" in content
        assert "john@example.com" in content

    def test_generate_monthly_summary(self, temp_vault, mock_audit_service):
        """Test generating monthly summary."""
        # Create templates directory
        template_dir = Path(temp_vault) / ".specify" / "templates" / "documents"
        template_dir.mkdir(parents=True)

        # Create test template
        test_template = template_dir / "monthly-summary.md.j2"
        test_template.write_text("""# Monthly Summary

Month: {{ start_date | date_format("%B %Y") }}
Total actions: {{ metrics.total_actions }}
""")

        service = DocumentService(
            vault_path=temp_vault,
            audit_service=mock_audit_service
        )

        month = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None).replace(day=1)
        doc, file_path = service.generate_monthly_summary(month=month)

        assert doc.document_type == "monthly_summary"
        assert "monthly" in doc.document_id.lower()
        assert file_path.exists()
        content = file_path.read_text(encoding='utf-8')
        assert "Monthly Summary" in content

    def test_custom_filters(self, temp_vault, temp_templates):
        """Test custom Jinja2 filters."""
        service = DocumentService(
            vault_path=temp_vault,
            template_dir=str(Path(temp_templates) / "templates")
        )

        # Test datetime_format filter
        dt = datetime(2026, 3, 1, 14, 30, 0)
        result = service._datetime_format(dt, "%Y-%m-%d")
        assert result == "2026-03-01"

        # Test duration_format filter
        assert "30.0m" in service._duration_format(1800)
        assert "2.0h" in service._duration_format(7200)
        assert "5.0s" in service._duration_format(5)


class TestDocumentGenerationParams:
    """Test DocumentGenerationParams."""

    def test_default_params(self):
        """Test default parameter values."""
        params = DocumentGenerationParams()

        assert params.start_date is None
        assert params.end_date is None
        assert params.include_metrics is True
        assert params.include_activities is True
        assert params.include_decisions is True
        assert params.custom_sections is None

    def test_custom_params(self):
        """Test custom parameter values."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        params = DocumentGenerationParams(
            start_date=now - timedelta(days=7),
            end_date=now,
            include_metrics=False,
            custom_sections={"budget": "$10,000"}
        )

        assert params.start_date == now - timedelta(days=7)
        assert params.end_date == now
        assert params.include_metrics is False
        assert params.custom_sections["budget"] == "$10,000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
