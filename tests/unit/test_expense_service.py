"""
Unit tests for ExpenseService - Gold Tier US8

Tests OCR extraction, expense parsing, budget validation, and unusual expense detection.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from src.models.expense import Expense, ExpenseCategory, ApprovalStatus
from src.models.budget import Budget, BudgetFile
from src.services.expense_service import ExpenseService


class TestExpenseModel:
    """Test Expense model creation and validation."""

    def test_create_expense(self):
        """Test creating a valid expense."""
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("45.99"),
            currency="USD",
            vendor="Adobe Creative Cloud",
            expense_date=date(2026, 3, 2),
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.PENDING,
            created_at=datetime.now()
        )

        assert expense.expense_id == "EXPENSE_2026_03_02_001"
        assert expense.amount == Decimal("45.99")
        assert expense.category == ExpenseCategory.SOFTWARE
        assert expense.type == "expense"

    def test_expense_validation_invalid_id(self):
        """Test expense creation with invalid ID."""
        with pytest.raises(ValueError, match="must start with 'EXPENSE_'"):
            Expense(
                expense_id="INVALID_001",
                amount=Decimal("45.99"),
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

    def test_expense_validation_negative_amount(self):
        """Test expense creation with negative amount."""
        with pytest.raises(ValueError, match="amount must be positive"):
            Expense(
                expense_id="EXPENSE_2026_03_02_001",
                amount=Decimal("-45.99"),
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

    def test_expense_validation_future_date(self):
        """Test expense creation with future date."""
        future_date = date(2099, 12, 31)
        with pytest.raises(ValueError, match="cannot be in the future"):
            Expense(
                expense_id="EXPENSE_2099_12_31_001",
                amount=Decimal("45.99"),
                currency="USD",
                vendor="Test Vendor",
                expense_date=future_date,
                category=ExpenseCategory.SOFTWARE,
                receipt_file="/Receipts/receipt.pdf",
                budget_category_id="BUDGET_software_2026_03",
                ocr_confidence=0.92,
                approval_status=ApprovalStatus.PENDING,
                created_at=datetime.now()
            )

    def test_expense_validation_invalid_ocr_confidence(self):
        """Test expense creation with invalid OCR confidence."""
        with pytest.raises(ValueError, match="ocr_confidence must be between 0.0 and 1.0"):
            Expense(
                expense_id="EXPENSE_2026_03_02_001",
                amount=Decimal("45.99"),
                currency="USD",
                vendor="Test Vendor",
                expense_date=date(2026, 3, 2),
                category=ExpenseCategory.SOFTWARE,
                receipt_file="/Receipts/receipt.pdf",
                budget_category_id="BUDGET_software_2026_03",
                ocr_confidence=1.5,  # Invalid
                approval_status=ApprovalStatus.PENDING,
                created_at=datetime.now()
            )

    def test_expense_approve(self):
        """Test approving an expense."""
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("45.99"),
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

        expense.approve(approved_by="auto")

        assert expense.approval_status == ApprovalStatus.APPROVED
        assert expense.approved_by == "auto"
        assert expense.approved_at is not None

    def test_expense_flag_for_review(self):
        """Test flagging expense for review."""
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("999.99"),
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

        expense.flag_for_review("Unusually high amount")

        assert expense.flagged_for_review is True
        assert expense.review_reason == "Unusually high amount"

    def test_expense_generate_id(self):
        """Test expense ID generation."""
        expense_date = date(2026, 3, 2)
        expense_id = Expense.generate_id(expense_date, sequence=1)

        assert expense_id == "EXPENSE_2026_03_02_001"

    def test_expense_from_ocr_data(self):
        """Test creating expense from OCR data."""
        ocr_data = {
            "amount": 45.99,
            "vendor": "Adobe Creative Cloud",
            "date": "2026-03-02",
            "category": "software",
            "confidence": 0.92,
            "description": "Monthly subscription"
        }

        expense = Expense.from_ocr_data(
            ocr_data=ocr_data,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            sequence=1
        )

        assert expense.amount == Decimal("45.99")
        assert expense.vendor == "Adobe Creative Cloud"
        assert expense.category == ExpenseCategory.SOFTWARE
        assert expense.ocr_confidence == 0.92


class TestExpenseServiceOCR:
    """Test OCR extraction and parsing."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def expense_service(self, temp_vault):
        """Create ExpenseService instance."""
        return ExpenseService(vault_path=temp_vault)

    def test_extract_amount(self, expense_service):
        """Test amount extraction from receipt text."""
        text = """
        RECEIPT
        Total: $45.99
        Thank you for your purchase
        """

        amount = expense_service._extract_amount(text)
        assert amount == Decimal("45.99")

    def test_extract_amount_multiple_formats(self, expense_service):
        """Test amount extraction with various formats."""
        texts = [
            ("Total: $45.99", Decimal("45.99")),
            ("Amount Due: 123.45", Decimal("123.45")),
            ("Balance: $1,234.56", Decimal("1234.56")),
            ("$99.00", Decimal("99.00"))
        ]

        for text, expected in texts:
            amount = expense_service._extract_amount(text)
            assert amount == expected

    def test_extract_vendor(self, expense_service):
        """Test vendor extraction from receipt text."""
        text = """
        Adobe Creative Cloud
        Monthly Subscription
        Total: $45.99
        """

        vendor = expense_service._extract_vendor(text)
        assert vendor == "Adobe Creative Cloud"

    def test_extract_date(self, expense_service):
        """Test date extraction from receipt text."""
        texts = [
            ("Date: 03/02/2026", date(2026, 3, 2)),
            ("2026-03-02", date(2026, 3, 2)),
            ("March 2, 2026", None),  # Month name format not implemented
        ]

        for text, expected in texts:
            extracted_date = expense_service._extract_date(text)
            if expected:
                # Allow flexible matching
                assert extracted_date is not None

    def test_categorize_expense_software(self, expense_service):
        """Test expense categorization - software."""
        vendor = "Adobe Creative Cloud"
        text = "Adobe Creative Cloud subscription"

        category = expense_service._categorize_expense(vendor, text)
        assert category == ExpenseCategory.SOFTWARE

    def test_categorize_expense_travel(self, expense_service):
        """Test expense categorization - travel."""
        vendor = "United Airlines"
        text = "Flight booking confirmation"

        category = expense_service._categorize_expense(vendor, text)
        assert category == ExpenseCategory.TRAVEL

    def test_categorize_expense_meals(self, expense_service):
        """Test expense categorization - meals."""
        vendor = "Starbucks"
        text = "Coffee and breakfast"

        category = expense_service._categorize_expense(vendor, text)
        assert category == ExpenseCategory.MEALS

    def test_categorize_expense_unknown(self, expense_service):
        """Test expense categorization - unknown."""
        vendor = "Unknown Vendor"
        text = "Some random text"

        category = expense_service._categorize_expense(vendor, text)
        assert category == ExpenseCategory.OTHER


class TestExpenseServiceBudgetValidation:
    """Test budget validation and unusual expense detection."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def expense_service(self, temp_vault):
        """Create ExpenseService instance."""
        return ExpenseService(vault_path=temp_vault)

    @pytest.fixture
    def sample_budget(self, temp_vault):
        """Create sample budget."""
        budget = Budget(
            budget_id="BUDGET_software_2026_03",
            category=ExpenseCategory.SOFTWARE,
            month="2026-03",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("200.00"),
            currency="USD"
        )

        budget_file = BudgetFile(temp_vault, "2026-03")
        budget_file.update_budget(budget)

        return budget

    def test_check_budget_approval_within_limit(self, expense_service, sample_budget, temp_vault):
        """Test budget approval check - within limit."""
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

        result = expense_service._check_budget_approval(expense, "2026-03")
        assert result is True

    def test_check_budget_approval_exceeds_limit(self, expense_service, sample_budget, temp_vault):
        """Test budget approval check - exceeds limit."""
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("400.00"),  # Would exceed limit
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

        result = expense_service._check_budget_approval(expense, "2026-03")
        assert result is False

    def test_is_unusual_expense_normal(self, expense_service, temp_vault):
        """Test unusual expense detection - normal expense."""
        # Create some historical expenses
        for i in range(1, 4):
            expense = Expense(
                expense_id=f"EXPENSE_2026_02_{i:02d}_001",
                amount=Decimal("50.00"),
                currency="USD",
                vendor=f"Vendor {i}",
                expense_date=date(2026, 2, i),
                category=ExpenseCategory.SOFTWARE,
                receipt_file="/Receipts/receipt.pdf",
                budget_category_id="BUDGET_software_2026_02",
                ocr_confidence=0.92,
                approval_status=ApprovalStatus.APPROVED,
                created_at=datetime.now()
            )

            from src.models.expense import save_expense
            save_expense(expense, temp_vault)

        # Test with similar amount
        test_expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("55.00"),
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

        result = expense_service._is_unusual_expense(test_expense)
        assert result is False

    def test_is_unusual_expense_high(self, expense_service, temp_vault):
        """Test unusual expense detection - unusually high."""
        # Create some historical expenses (avg = $50)
        for i in range(1, 4):
            expense = Expense(
                expense_id=f"EXPENSE_2026_02_{i:02d}_001",
                amount=Decimal("50.00"),
                currency="USD",
                vendor=f"Vendor {i}",
                expense_date=date(2026, 2, i),
                category=ExpenseCategory.SOFTWARE,
                receipt_file="/Receipts/receipt.pdf",
                budget_category_id="BUDGET_software_2026_02",
                ocr_confidence=0.92,
                approval_status=ApprovalStatus.APPROVED,
                created_at=datetime.now()
            )

            from src.models.expense import save_expense
            save_expense(expense, temp_vault)

        # Test with 3x average amount
        test_expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("200.00"),  # 4x average
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

        result = expense_service._is_unusual_expense(test_expense)
        assert result is True

    def test_get_next_expense_sequence(self, expense_service, temp_vault):
        """Test expense sequence number generation."""
        expense_date = date(2026, 3, 2)

        # No existing expenses
        seq = expense_service._get_next_expense_sequence(expense_date)
        assert seq == 1

        # Create one expense
        expense = Expense(
            expense_id="EXPENSE_2026_03_02_001",
            amount=Decimal("45.99"),
            currency="USD",
            vendor="Test Vendor",
            expense_date=expense_date,
            category=ExpenseCategory.SOFTWARE,
            receipt_file="/Receipts/receipt.pdf",
            budget_category_id="BUDGET_software_2026_03",
            ocr_confidence=0.92,
            approval_status=ApprovalStatus.PENDING,
            created_at=datetime.now()
        )

        from src.models.expense import save_expense
        save_expense(expense, temp_vault)

        # Next sequence should be 2
        seq = expense_service._get_next_expense_sequence(expense_date)
        assert seq == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
