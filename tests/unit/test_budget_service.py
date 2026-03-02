"""
Unit tests for BudgetService - Gold Tier US8

Tests budget tracking, threshold alerts, and validation.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal
import tempfile
import shutil

from src.models.budget import Budget, BudgetFile, ExpenseCategory
from src.models.expense import Expense, ApprovalStatus
from src.services.budget_service import BudgetService


class TestBudgetModel:
    """Test Budget model creation and validation."""

    def test_create_budget(self):
        """Test creating a valid budget."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            currency="USD"
        )

        assert budget.budget_id == "BUDGET_software_2026_03"
        assert budget.category == ExpenseCategory.SOFTWARE
        assert budget.monthly_limit == Decimal("500.00")
        assert budget.current_spend == Decimal("0.00")

    def test_budget_validation_invalid_id(self):
        """Test budget creation with invalid ID."""
        with pytest.raises(ValueError, match="must start with 'BUDGET_'"):
            Budget(
                budget_id="INVALID_001",
                category=ExpenseCategory.SOFTWARE,
                month="2026-03",
                monthly_limit=Decimal("500.00"),
                currency="USD"
            )

    def test_budget_validation_invalid_month(self):
        """Test budget creation with invalid month format."""
        with pytest.raises(ValueError, match="must be in YYYY-MM format"):
            Budget(
                budget_id="BUDGET_software_2026_03",
                category=ExpenseCategory.SOFTWARE,
                month="2026/03",  # Invalid format
                monthly_limit=Decimal("500.00"),
                currency="USD"
            )

    def test_budget_validation_negative_limit(self):
        """Test budget creation with negative limit."""
        with pytest.raises(ValueError, match="monthly_limit must be positive"):
            Budget(
                budget_id="BUDGET_software_2026_03",
                category=ExpenseCategory.SOFTWARE,
                month="2026-03",
                monthly_limit=Decimal("-500.00"),
                currency="USD"
            )

    def test_budget_get_spend_percentage(self):
        """Test spend percentage calculation."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("250.00"),
            currency="USD"
        )

        pct = budget.get_spend_percentage()
        assert pct == 0.5  # 50%

    def test_budget_get_remaining_budget(self):
        """Test remaining budget calculation."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("250.00"),
            currency="USD"
        )

        remaining = budget.get_remaining_budget()
        assert remaining == Decimal("250.00")

    def test_budget_is_overspent(self):
        """Test overspend detection."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("600.00"),
            currency="USD"
        )

        assert budget.is_overspent() is True

    def test_budget_should_send_alert_threshold(self):
        """Test alert threshold detection."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("410.00"),  # 82% - above 80% threshold
            currency="USD",
            alert_threshold=0.80
        )

        assert budget.should_send_alert() is True

    def test_budget_should_send_alert_already_sent(self):
        """Test alert not sent twice."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("410.00"),
            currency="USD",
            alert_threshold=0.80,
            alert_sent=True  # Already sent
        )

        assert budget.should_send_alert() is False

    def test_budget_add_expense(self):
        """Test adding expense to budget."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("100.00"),
            currency="USD"
        )

        new_spend = budget.add_expense(Decimal("50.00"))

        assert budget.current_spend == Decimal("150.00")
        assert new_spend == Decimal("150.00")

    def test_budget_generate_id(self):
        """Test budget ID generation."""
        budget_id = Budget.generate_id(ExpenseCategory.SOFTWARE, "2026-03")
        assert budget_id == "BUDGET_software_2026_03"

    def test_budget_to_dict(self):
        """Test budget serialization to dict."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("250.00"),
            currency="USD"
        )

        data = budget.to_dict()

        assert data["budget_id"] == "BUDGET_software_2026_03"
        assert data["category"] == "software"
        assert data["monthly_limit"] == 500.00
        assert data["current_spend"] == 250.00

    def test_budget_from_dict(self):
        """Test budget deserialization from dict."""
        data = {
            "budget_id": "BUDGET_software_2026_03",
            "category": "software",
            "month": "2026-03",
            "monthly_limit": 500.00,
            "current_spend": 250.00,
            "currency": "USD",
            "alerts_enabled": True,
            "alert_threshold": 0.80,
            "alert_sent": False,
            "rollover_enabled": False
        }

        budget = Budget.from_dict(data)

        assert budget.budget_id == "BUDGET_software_2026_03"
        assert budget.category == ExpenseCategory.SOFTWARE
        assert budget.monthly_limit == Decimal("500.00")


class TestBudgetService:
    """Test BudgetService functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def budget_service(self, temp_vault):
        """Create BudgetService instance."""
        return BudgetService(vault_path=temp_vault)

    def test_create_budget(self, budget_service):
        """Test creating a new budget."""
        budget = budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        assert budget.budget_id == "BUDGET_software_2026_03"
        assert budget.monthly_limit == Decimal("500.00")

    def test_update_existing_budget(self, budget_service, temp_vault):
        """Test updating an existing budget."""
        # Create initial budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Update it
        updated = budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("600.00")
        )

        assert updated.monthly_limit == Decimal("600.00")

    def test_get_budget(self, budget_service):
        """Test retrieving a budget."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Retrieve it
        budget = budget_service.get_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03"
        )

        assert budget is not None
        assert budget.monthly_limit == Decimal("500.00")

    def test_get_all_budgets(self, budget_service):
        """Test retrieving all budgets for a month."""
        # Create multiple budgets
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )
        budget_service.create_or_update_budget(
            category=ExpenseCategory.TRAVEL,
            month="2026-03",
            monthly_limit=Decimal("1000.00")
        )

        # Retrieve all
        budgets = budget_service.get_all_budgets("2026-03")

        assert len(budgets) == 2

    def test_add_expense_to_budget(self, budget_service, temp_vault):
        """Test adding expense to budget."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Create expense
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("100.00"),
            currency="USD",
            vendor="Test Vendor",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.APPROVED,
            created_at=datetime.now()
        )

        # Add to budget
        updated_budget = budget_service.add_expense_to_budget(
            expense=expense,
            send_alerts=False
        )

        assert updated_budget.current_spend == Decimal("100.00")

    def test_budget_alert_threshold(self, budget_service, temp_vault):
        """Test budget threshold alert creation."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            alert_threshold=0.80
        )

        # Create expense that triggers threshold
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("410.00"),  # 82% of budget
            currency="USD",
            vendor="Test Vendor",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.APPROVED,
            created_at=datetime.now()
        )

        # Add to budget (should create alert)
        budget_service.add_expense_to_budget(
            expense=expense,
            send_alerts=True
        )

        # Check for alert file
        needs_action_dir = temp_vault / "Needs_Action"
        alert_files = list(needs_action_dir.glob("BUDGET_ALERT_software_*.md"))

        assert len(alert_files) > 0

    def test_budget_overspent_alert(self, budget_service, temp_vault):
        """Test budget overspent alert creation."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Create expense that exceeds budget
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("600.00"),  # Exceeds budget
            currency="USD",
            vendor="Test Vendor",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.APPROVED,
            created_at=datetime.now()
        )

        # Add to budget (should create overspent alert)
        budget_service.add_expense_to_budget(
            expense=expense,
            send_alerts=True
        )

        # Check for alert file
        needs_action_dir = temp_vault / "Needs_Action"
        alert_files = list(needs_action_dir.glob("BUDGET_ALERT_software_*.md"))

        assert len(alert_files) > 0

    def test_validate_expense_against_budget_valid(self, budget_service):
        """Test expense validation - within budget."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Create expense
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("100.00"),
            currency="USD",
            vendor="Test Vendor",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.PENDING,
            created_at=datetime.now()
        )

        # Validate
        result = budget_service.validate_expense_against_budget(expense)

        assert result["valid"] is True
        assert result["reason"] == "Within budget"

    def test_validate_expense_against_budget_exceeds(self, budget_service):
        """Test expense validation - exceeds budget."""
        # Create budget
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )

        # Create expense that exceeds budget
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("600.00"),
            currency="USD",
            vendor="Test Vendor",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.PENDING,
            created_at=datetime.now()
        )

        # Validate
        result = budget_service.validate_expense_against_budget(expense)

        assert result["valid"] is False
        assert "exceed budget" in result["reason"]

    def test_get_budget_report(self, budget_service):
        """Test budget report generation."""
        # Create budgets
        budget_service.create_or_update_budget(
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00")
        )
        budget_service.create_or_update_budget(
            category=ExpenseCategory.TRAVEL,
            month="2026-03",
            monthly_limit=Decimal("1000.00")
        )

        # Add some expenses
        expense1 = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("200.00"),
            currency="USD",
            vendor="Vendor 1",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.APPROVED,
            created_at=datetime.now()
        )
        budget_service.add_expense_to_budget(expense1, send_alerts=False)

        # Get report
        report = budget_service.get_budget_report("2026-03")

        assert report["month"] == "2026-03"
        assert report["total_budget"] == 1500.00  # 500 + 1000
        assert report["total_spent"] == 200.00
        assert len(report["categories"]) == 2

    def test_initialize_month_budgets(self, budget_service):
        """Test default budget initialization."""
        budgets = budget_service.initialize_month_budgets("2026-03")

        assert len(budgets) == 8  # All 8 categories
        assert all(b.month == "2026-03" for b in budgets)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
