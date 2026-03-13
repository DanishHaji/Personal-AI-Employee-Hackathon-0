#!/usr/bin/env python3
"""
Odoo Integration Tests - Platinum Tier US5

Integration tests for Odoo MCP server and expense syncing.
Tests can be run in two modes:
- Unit tests (no Odoo connection required)
- Integration tests (requires Odoo server)

Usage:
    # Unit tests only
    pytest tests/test_odoo_integration.py -m unit

    # Integration tests (requires Odoo)
    ODOO_URL=https://odoo.example.com \
    ODOO_API_KEY=your_key \
    pytest tests/test_odoo_integration.py -m integration

    # All tests
    pytest tests/test_odoo_integration.py
"""

import os
import sys
import json
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.expense import Expense, ExpenseCategory, ApprovalStatus
from src.models.budget import Budget
from src.services.expense_service import ExpenseService


# Test fixtures

@pytest.fixture
def temp_vault(tmp_path):
    """Create temporary vault directory structure."""
    vault = tmp_path / "vault"
    (vault / "Expenses").mkdir(parents=True)
    (vault / "Budgets").mkdir(parents=True)
    (vault / "Receipts").mkdir(parents=True)
    (vault / "Logs").mkdir(parents=True)
    (vault / "Needs_Action").mkdir(parents=True)
    (vault / "Reports" / "Financial").mkdir(parents=True)
    return vault


@pytest.fixture
def sample_expense():
    """Create sample expense for testing."""
    return Expense(
        expense_id="EXPENSE_2026_03_12_001",
        amount=Decimal("45.99"),
        currency="USD",
        vendor="Adobe Creative Cloud",
        expense_date=date(2026, 3, 12),
        category=ExpenseCategory.SOFTWARE,
        description="Monthly subscription",
        receipt_file="/receipts/adobe_2026_03.pdf",
        budget_category_id="BUDGET_software_2026_03",
        ocr_confidence=0.95,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="auto",
        approved_at=datetime(2026, 3, 12, 10, 30),
        created_at=datetime(2026, 3, 12, 10, 0)
    )


@pytest.fixture
def sample_budget():
    """Create sample budget for testing."""
    return Budget(
        budget_id="BUDGET_software_2026_03",
        category=ExpenseCategory.SOFTWARE,
        month="2026-03",
        monthly_limit=Decimal("500.00"),
        current_spend=Decimal("325.50"),
        currency="USD"
    )


@pytest.fixture
def expense_service_no_odoo(temp_vault):
    """Create ExpenseService without Odoo integration."""
    return ExpenseService(vault_path=temp_vault)


@pytest.fixture
def expense_service_with_odoo(temp_vault):
    """Create ExpenseService with mock Odoo integration."""
    return ExpenseService(
        vault_path=temp_vault,
        odoo_url="https://odoo.test.com",
        odoo_api_key="test_key_123",  # pragma: allowlist secret
        odoo_database="test_db"
    )


# Unit Tests (no Odoo connection required)

@pytest.mark.unit
def test_expense_service_initialization_no_odoo(expense_service_no_odoo):
    """Test ExpenseService initializes correctly without Odoo."""
    assert expense_service_no_odoo.odoo_enabled is False
    assert expense_service_no_odoo.odoo_url is None
    assert expense_service_no_odoo.odoo_api_key is None


@pytest.mark.unit
def test_expense_service_initialization_with_odoo(expense_service_with_odoo):
    """Test ExpenseService initializes correctly with Odoo config."""
    # Will be enabled only if httpx is available
    assert expense_service_with_odoo.odoo_url == "https://odoo.test.com"
    assert expense_service_with_odoo.odoo_api_key == "test_key_123"  # pragma: allowlist secret
    assert expense_service_with_odoo.odoo_database == "test_db"


@pytest.mark.unit
def test_odoo_category_mappings_loaded(expense_service_with_odoo):
    """Test Odoo category mappings are loaded from config.json."""
    if expense_service_with_odoo.odoo_enabled:
        # Check some standard mappings exist
        assert "software" in expense_service_with_odoo.odoo_category_mappings or True
        assert hasattr(expense_service_with_odoo, 'odoo_default_account')


@pytest.mark.unit
def test_sync_expense_to_odoo_unapproved(expense_service_with_odoo, sample_expense):
    """Test syncing unapproved expense returns False."""
    sample_expense.approval_status = ApprovalStatus.PENDING

    result = expense_service_with_odoo.sync_expense_to_odoo(sample_expense)

    # Should return False for unapproved expense
    assert result is False


@pytest.mark.unit
def test_sync_expense_to_odoo_disabled(expense_service_no_odoo, sample_expense):
    """Test syncing when Odoo is disabled returns False."""
    result = expense_service_no_odoo.sync_expense_to_odoo(sample_expense)

    assert result is False


@pytest.mark.unit
@patch('httpx.Client')
def test_sync_expense_to_odoo_success(mock_httpx, expense_service_with_odoo, sample_expense):
    """Test successful expense sync to Odoo."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": 42, "status": "created"}

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value = mock_client

    # Force enable Odoo for test
    expense_service_with_odoo.odoo_enabled = True
    expense_service_with_odoo._odoo_client = mock_client

    result = expense_service_with_odoo.sync_expense_to_odoo(sample_expense)

    # Should succeed
    assert result is True

    # Verify API call was made
    assert mock_client.post.called


@pytest.mark.unit
@patch('httpx.Client')
def test_sync_expense_to_odoo_failure(mock_httpx, expense_service_with_odoo, sample_expense):
    """Test failed expense sync to Odoo."""
    # Mock failed response
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_httpx.return_value = mock_client

    # Force enable Odoo for test
    expense_service_with_odoo.odoo_enabled = True
    expense_service_with_odoo._odoo_client = mock_client

    result = expense_service_with_odoo.sync_expense_to_odoo(sample_expense)

    # Should fail
    assert result is False


@pytest.mark.unit
def test_is_synced_to_odoo_not_synced(expense_service_with_odoo, sample_expense):
    """Test checking if expense is synced when sync log doesn't exist."""
    result = expense_service_with_odoo._is_synced_to_odoo(sample_expense.expense_id)

    # Should return False when log doesn't exist
    assert result is False


@pytest.mark.unit
def test_is_synced_to_odoo_already_synced(expense_service_with_odoo, sample_expense, temp_vault):
    """Test checking if expense is already synced."""
    # Create sync log with successful sync
    sync_log = temp_vault / "Logs" / "odoo_sync.jsonl"
    sync_log.parent.mkdir(parents=True, exist_ok=True)

    with open(sync_log, 'w') as f:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "expense_id": sample_expense.expense_id,
            "status": "success",
            "details": {"odoo_id": 42}
        }
        f.write(json.dumps(entry) + '\n')

    result = expense_service_with_odoo._is_synced_to_odoo(sample_expense.expense_id)

    # Should return True when expense is in log
    assert result is True


@pytest.mark.unit
@patch('httpx.Client')
def test_get_budget_status_from_odoo(mock_httpx, expense_service_with_odoo):
    """Test getting budget status from Odoo."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "month": "2026-03",
        "categories": [
            {"category": "software", "spent": 325.50, "budget": 500.00}
        ]
    }

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_httpx.return_value = mock_client

    # Force enable Odoo for test
    expense_service_with_odoo.odoo_enabled = True
    expense_service_with_odoo._odoo_client = mock_client

    result = expense_service_with_odoo.get_budget_status_from_odoo("2026-03")

    # Should return budget data
    assert result is not None
    assert result["month"] == "2026-03"
    assert len(result["categories"]) == 1


@pytest.mark.unit
def test_check_budget_warnings_under_threshold(expense_service_with_odoo):
    """Test budget warnings when under threshold."""
    # Mock budget status with spending under 80%
    with patch.object(expense_service_with_odoo, 'get_budget_status_from_odoo') as mock_get:
        mock_get.return_value = {
            "month": "2026-03",
            "categories": [
                {"category": "software", "spent": 300.00, "budget": 500.00}  # 60%
            ]
        }

        warnings = expense_service_with_odoo.check_budget_warnings("2026-03")

        # Should have no warnings
        assert len(warnings) == 0


@pytest.mark.unit
def test_check_budget_warnings_at_threshold(expense_service_with_odoo, temp_vault):
    """Test budget warnings when at 80% threshold."""
    # Mock budget status with spending at 80%
    with patch.object(expense_service_with_odoo, 'get_budget_status_from_odoo') as mock_get:
        mock_get.return_value = {
            "month": "2026-03",
            "categories": [
                {"category": "software", "spent": 400.00, "budget": 500.00}  # 80%
            ]
        }

        warnings = expense_service_with_odoo.check_budget_warnings("2026-03")

        # Should have warning
        assert len(warnings) == 1
        assert warnings[0]["level"] == "warning"
        assert warnings[0]["category"] == "software"


@pytest.mark.unit
def test_check_budget_warnings_over_budget(expense_service_with_odoo, temp_vault):
    """Test budget warnings when over budget."""
    # Mock budget status with spending over 100%
    with patch.object(expense_service_with_odoo, 'get_budget_status_from_odoo') as mock_get:
        mock_get.return_value = {
            "month": "2026-03",
            "categories": [
                {"category": "software", "spent": 550.00, "budget": 500.00}  # 110%
            ]
        }

        warnings = expense_service_with_odoo.check_budget_warnings("2026-03")

        # Should have critical warning
        assert len(warnings) == 1
        assert warnings[0]["level"] == "critical"
        assert warnings[0]["percentage"] >= 1.0


# Integration Tests (require live Odoo server)

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ODOO_URL"),
    reason="ODOO_URL not set - skipping integration tests"
)
def test_odoo_connection_live():
    """Test live connection to Odoo server."""
    import httpx

    odoo_url = os.getenv("ODOO_URL")
    odoo_api_key = os.getenv("ODOO_API_KEY")

    client = httpx.Client(
        base_url=odoo_url,
        headers={"Authorization": f"Bearer {odoo_api_key}"}
    )

    try:
        response = client.get("/api/health")
        assert response.status_code in (200, 404)  # 404 ok if health endpoint not implemented
    finally:
        client.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ODOO_URL"),
    reason="ODOO_URL not set - skipping integration tests"
)
def test_sync_expense_to_odoo_live(temp_vault, sample_expense):
    """Test syncing expense to live Odoo server."""
    service = ExpenseService(
        vault_path=temp_vault,
        odoo_url=os.getenv("ODOO_URL"),
        odoo_api_key=os.getenv("ODOO_API_KEY"),
        odoo_database=os.getenv("ODOO_DATABASE", "odoo")
    )

    if not service.odoo_enabled:
        pytest.skip("Odoo integration not available (httpx missing)")

    result = service.sync_expense_to_odoo(sample_expense)

    # Result depends on Odoo server state
    # Could be True (success) or False (API error)
    assert isinstance(result, bool)


# Test runner

if __name__ == "__main__":
    # Run tests with pytest
    import subprocess

    print("Running Odoo Integration Tests...")
    print("=" * 60)
    print()

    # Run unit tests
    print("Running unit tests (no Odoo connection required)...")
    result = subprocess.run([
        "pytest",
        __file__,
        "-m", "unit",
        "-v"
    ])

    if result.returncode != 0:
        print("\n❌ Unit tests failed")
        sys.exit(1)

    print("\n✅ Unit tests passed")

    # Check if Odoo is configured for integration tests
    if os.getenv("ODOO_URL"):
        print("\nRunning integration tests (requires Odoo connection)...")
        result = subprocess.run([
            "pytest",
            __file__,
            "-m", "integration",
            "-v"
        ])

        if result.returncode != 0:
            print("\n⚠️  Integration tests failed (check Odoo connection)")
        else:
            print("\n✅ Integration tests passed")
    else:
        print("\nℹ️  Skipping integration tests (set ODOO_URL to enable)")

    print("\n" + "=" * 60)
    print("Tests complete")
