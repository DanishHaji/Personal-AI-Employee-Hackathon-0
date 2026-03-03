"""
Expense Model for Personal AI Employee - Gold Tier

Business expense tracking with OCR extraction from receipts.

Entity Definition: specs/003-gold-tier-upgrade/data-model.md#expense
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pathlib import Path

from src.models.base_model import BaseModel

logger = logging.getLogger(__name__)


class ExpenseCategory(str, Enum):
    """Expense category types."""
    SOFTWARE = "software"
    TRAVEL = "travel"
    OFFICE = "office"
    MARKETING = "marketing"
    MEALS = "meals"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    OTHER = "other"


class ApprovalStatus(str, Enum):
    """Approval status types."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class Expense(BaseModel):
    """
    Business expense tracking with OCR extraction from receipts.

    Features:
    - OCR extraction from receipts (PDFs and images)
    - Budget validation and tracking
    - Auto-approval for recurring vendors
    - Unusual expense detection (3x category average)
    - Encryption for sensitive receipts

    Storage: /Expenses/YYYY-MM/{expense_id}.md

    Example:
        expense = Expense(
            expense_id="EXPENSE_2026_02_27_001",
            amount=Decimal("45.99"),
            currency="USD",
            vendor="Adobe Creative Cloud",
            expense_date=date(2026, 2, 27),
            category=ExpenseCategory.SOFTWARE,
            description="Monthly subscription - Creative Cloud All Apps",
            receipt_file="/Receipts/2026-02-27_adobe_receipt.pdf",
            budget_category_id="BUDGET_software_2026_02",
            ocr_confidence=0.95,
            approval_status=ApprovalStatus.APPROVED,
            approved_by="auto"
        )

        # Save to vault
        expense.save_to_file(
            "/vault/Expenses/2026-02/EXPENSE_2026_02_27_001.md",
            body=expense.generate_body()
        )
    """

    # Required fields
    expense_id: str
    amount: Decimal
    currency: str
    vendor: str
    expense_date: date
    category: ExpenseCategory
    receipt_file: str
    budget_category_id: str
    ocr_confidence: float
    approval_status: ApprovalStatus
    created_at: datetime

    # Optional fields
    description: Optional[str] = None
    flagged_for_review: bool = False
    review_reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Type identifier
    type: str = field(default="expense", init=False)

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_expense_id()
        self._validate_amount()
        self._validate_currency()
        self._validate_expense_date()
        self._validate_ocr_confidence()
        self._validate_approval_status()

        # Convert category to enum if string
        if isinstance(self.category, str):
            self.category = ExpenseCategory(self.category)

        # Convert approval_status to enum if string
        if isinstance(self.approval_status, str):
            self.approval_status = ApprovalStatus(self.approval_status)

        # Convert amount to Decimal if float
        if isinstance(self.amount, (float, int)):
            self.amount = Decimal(str(self.amount))

    def _validate_expense_id(self):
        """Ensure expense_id follows format EXPENSE_{date}_{sequence}."""
        if not self.expense_id.startswith("EXPENSE_"):
            raise ValueError(f"expense_id must start with 'EXPENSE_', got '{self.expense_id}'")

        # Check format: EXPENSE_YYYY_MM_DD_NNN
        pattern = r"^EXPENSE_\d{4}_\d{2}_\d{2}_\d+$"
        if not re.match(pattern, self.expense_id):
            raise ValueError(f"expense_id must match format 'EXPENSE_YYYY_MM_DD_NNN', got '{self.expense_id}'")

    def _validate_amount(self):
        """Ensure amount is positive with max 2 decimal places."""
        if self.amount <= 0:
            raise ValueError(f"amount must be positive, got {self.amount}")

        # Check decimal places
        if self.amount.as_tuple().exponent < -2:
            raise ValueError(f"amount must have max 2 decimal places, got {self.amount}")

    def _validate_currency(self):
        """Ensure currency is valid ISO 4217 code."""
        # Common currency codes (can be extended)
        valid_currencies = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "INR"]

        if len(self.currency) != 3 or not self.currency.isupper():
            logger.warning(f"currency may not be valid ISO 4217 code: {self.currency}")

    def _validate_expense_date(self):
        """Ensure expense_date is not in the future."""
        today = date.today()
        if self.expense_date > today:
            raise ValueError(f"expense_date cannot be in the future, got {self.expense_date}")

    def _validate_ocr_confidence(self):
        """Ensure OCR confidence is between 0.0 and 1.0."""
        if not 0.0 <= self.ocr_confidence <= 1.0:
            raise ValueError(f"ocr_confidence must be between 0.0 and 1.0, got {self.ocr_confidence}")

    def _validate_approval_status(self):
        """Ensure approval fields are consistent."""
        if self.approval_status == ApprovalStatus.APPROVED:
            if not self.approved_by:
                logger.warning(f"Approved expense {self.expense_id} missing approved_by")

    def get_schema_name(self) -> Optional[str]:
        """Get JSON Schema filename for validation."""
        return "expense-schema.json"

    def flag_for_review(self, reason: str):
        """
        Flag expense for manual review.

        Args:
            reason: Reason for flagging (e.g., "3x category average")
        """
        self.flagged_for_review = True
        self.review_reason = reason
        logger.info(f"Flagged expense {self.expense_id} for review: {reason}")

    def approve(self, approved_by: str = "auto"):
        """
        Approve the expense.

        Args:
            approved_by: Who approved (auto, user, etc.)
        """
        self.approval_status = ApprovalStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.now()
        logger.info(f"Approved expense {self.expense_id} by {approved_by}")

    def reject(self, reason: Optional[str] = None):
        """
        Reject the expense.

        Args:
            reason: Optional reason for rejection
        """
        self.approval_status = ApprovalStatus.REJECTED
        if reason:
            self.review_reason = reason
        logger.info(f"Rejected expense {self.expense_id}: {reason}")

    def get_month_folder(self) -> str:
        """
        Get the month folder for this expense.

        Returns:
            str: Folder name in format YYYY-MM
        """
        return self.expense_date.strftime("%Y-%m")

    def get_percentage_spent(self, budget_limit: Decimal) -> float:
        """
        Calculate percentage of budget spent.

        Args:
            budget_limit: Monthly budget limit

        Returns:
            float: Percentage (0.0-1.0+)
        """
        if budget_limit <= 0:
            return 0.0
        return float(self.amount / budget_limit)

    def generate_body(self, budget_info: Optional[dict] = None) -> str:
        """
        Generate markdown body for expense record.

        Args:
            budget_info: Optional budget tracking info

        Returns:
            str: Formatted markdown body
        """
        # Header
        amount_str = f"${self.amount:.2f}" if self.currency == "USD" else f"{self.amount:.2f} {self.currency}"
        body = f"""# Expense: {self.vendor}
**Amount**: {amount_str} | **Date**: {self.expense_date} | **Category**: {self.category.value.title()}

## Details
- **Vendor**: {self.vendor}
"""

        if self.description:
            body += f"- **Description**: {self.description}\n"

        body += f"- **Receipt**: [View Receipt]({self.receipt_file})\n"

        # Budget tracking
        if budget_info:
            body += f"\n## Budget Tracking\n"
            body += f"- **Category**: {self.category.value.title()}\n"
            body += f"- **Monthly Budget**: ${budget_info.get('monthly_limit', 0):.2f}\n"
            body += f"- **Current Spend**: ${budget_info.get('current_spend', 0):.2f}"

            # Calculate percentage
            monthly_limit = budget_info.get('monthly_limit', 0)
            current_spend = budget_info.get('current_spend', 0)
            if monthly_limit > 0:
                pct = (current_spend / monthly_limit) * 100
                body += f" ({pct:.0f}% used)\n"
                remaining = monthly_limit - current_spend
                body += f"- **Remaining**: ${remaining:.2f}\n"
            else:
                body += "\n"

        # Approval status
        body += f"\n## Approval\n"

        if self.approval_status == ApprovalStatus.APPROVED:
            approval_time = self.approved_at.strftime("%Y-%m-%d %I:%M %p") if self.approved_at else "Unknown"
            body += f"- **Status**: ✅ Approved\n"
            body += f"- **Approved By**: {self.approved_by or 'Unknown'}\n"
            body += f"- **Approved At**: {approval_time}\n"
        elif self.approval_status == ApprovalStatus.REJECTED:
            body += f"- **Status**: ❌ Rejected\n"
            if self.review_reason:
                body += f"- **Reason**: {self.review_reason}\n"
        else:
            body += f"- **Status**: ⏳ Pending Review\n"

        # Review flag
        if self.flagged_for_review:
            body += f"\n## ⚠️ Flagged for Review\n"
            body += f"**Reason**: {self.review_reason or 'Unusual expense pattern detected'}\n"

        # OCR confidence
        body += f"\n## OCR Extraction\n"
        body += f"- **Confidence**: {self.ocr_confidence:.1%}\n"

        if self.ocr_confidence < 0.75:
            body += f"- **⚠️ Low Confidence**: Manual verification recommended\n"

        return body.strip()

    @classmethod
    def generate_id(cls, expense_date: date, sequence: int = 1) -> str:
        """
        Generate expense ID from date and sequence.

        Args:
            expense_date: Date of expense
            sequence: Sequence number for that day (default: 1)

        Returns:
            str: Expense ID in format EXPENSE_YYYY_MM_DD_NNN
        """
        date_str = expense_date.strftime("%Y_%m_%d")
        return f"EXPENSE_{date_str}_{sequence:03d}"

    def get_filename(self) -> str:
        """
        Generate filename for expense record.

        Returns:
            str: Filename in format "{expense_id}.md"
        """
        return f"{self.expense_id}.md"

    @classmethod
    def from_ocr_data(
        cls,
        ocr_data: dict,
        receipt_file: str,
        budget_category_id: str,
        expense_date: Optional[date] = None,
        sequence: int = 1
    ) -> "Expense":
        """
        Factory method to create expense from OCR extraction data.

        Args:
            ocr_data: Parsed OCR data with keys: amount, vendor, date, category, confidence
            receipt_file: Path to receipt file
            budget_category_id: Budget category to charge against
            expense_date: Override expense date (defaults to OCR extracted date or today)
            sequence: Sequence number for expense ID generation

        Returns:
            Expense: New expense instance
        """
        # Extract fields from OCR data
        amount = Decimal(str(ocr_data.get("amount", 0)))
        vendor = ocr_data.get("vendor", "Unknown Vendor")
        category_str = ocr_data.get("category", "other")
        confidence = ocr_data.get("confidence", 0.0)
        description = ocr_data.get("description")

        # Parse category
        try:
            category = ExpenseCategory(category_str.lower())
        except ValueError:
            logger.warning(f"Invalid category '{category_str}', defaulting to 'other'")
            category = ExpenseCategory.OTHER

        # Parse date
        if expense_date is None:
            if "date" in ocr_data and ocr_data["date"]:
                try:
                    if isinstance(ocr_data["date"], str):
                        expense_date = date.fromisoformat(ocr_data["date"])
                    elif isinstance(ocr_data["date"], date):
                        expense_date = ocr_data["date"]
                    else:
                        expense_date = date.today()
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse date from OCR: {ocr_data.get('date')}")
                    expense_date = date.today()
            else:
                expense_date = date.today()

        # Generate expense ID
        expense_id = cls.generate_id(expense_date, sequence)

        # Determine approval status (pending by default)
        approval_status = ApprovalStatus.PENDING

        return cls(
            expense_id=expense_id,
            amount=amount,
            currency="USD",  # Default to USD
            vendor=vendor,
            expense_date=expense_date,
            category=category,
            description=description,
            receipt_file=receipt_file,
            budget_category_id=budget_category_id,
            ocr_confidence=confidence,
            approval_status=approval_status,
            created_at=datetime.now()
        )


# Helper functions

def save_expense(
    expense: Expense,
    vault_path: Path,
    budget_info: Optional[dict] = None
) -> Path:
    """
    Save expense to vault.

    Args:
        expense: Expense instance
        vault_path: Path to vault root
        budget_info: Optional budget tracking info

    Returns:
        Path: Path to saved file
    """
    # Create month folder
    expenses_dir = vault_path / "Expenses" / expense.get_month_folder()
    expenses_dir.mkdir(parents=True, exist_ok=True)

    filename = expense.get_filename()
    file_path = expenses_dir / filename

    body = expense.generate_body(budget_info=budget_info)

    expense.save_to_file(file_path, body=body)

    logger.info(f"Saved expense to {file_path}")
    return file_path


def load_expense(file_path: Path) -> Expense:
    """
    Load expense from markdown file.

    Args:
        file_path: Path to expense file

    Returns:
        Expense: Expense instance
    """
    expense, _ = Expense.load_from_file(file_path)
    return expense
