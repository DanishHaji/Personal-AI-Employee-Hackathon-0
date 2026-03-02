"""
Budget Model for Personal AI Employee - Gold Tier

Monthly budget allocations by expense category with threshold alerts.

Entity Definition: specs/003-gold-tier-upgrade/data-model.md#budget
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.models.expense import ExpenseCategory

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    """
    Monthly budget allocation for an expense category.

    Features:
    - Monthly spending limits by category
    - Threshold alerts (default 80% spending)
    - Current spend tracking
    - Rollover support (optional)
    - Budget vs actual reporting

    Storage: /Budgets/YYYY-MM.json (all categories in one JSON file per month)

    Example:
        budget = Budget(
            budget_id="BUDGET_software_2026_02",
            category=ExpenseCategory.SOFTWARE,
            month="2026-02",
            monthly_limit=Decimal("500.00"),
            current_spend=Decimal("325.50"),
            alerts_enabled=True,
            alert_threshold=0.80,
            currency="USD"
        )

        # Check if alert threshold reached
        if budget.should_send_alert():
            print(f"Alert: {budget.get_spend_percentage():.0%} of budget used")

        # Add expense to budget
        budget.add_expense(Decimal("45.99"))
    """

    # Required fields
    budget_id: str
    category: ExpenseCategory
    month: str
    monthly_limit: Decimal
    currency: str

    # Optional fields with defaults
    current_spend: Decimal = field(default_factory=lambda: Decimal("0.00"))
    alerts_enabled: bool = True
    alert_threshold: float = 0.80  # 80% threshold
    alert_sent: bool = False
    rollover_enabled: bool = False

    def __post_init__(self):
        """Validate fields after initialization."""
        self._validate_budget_id()
        self._validate_month()
        self._validate_monthly_limit()
        self._validate_alert_threshold()
        self._validate_currency()

        # Convert category to enum if string
        if isinstance(self.category, str):
            self.category = ExpenseCategory(self.category)

        # Convert amounts to Decimal if needed
        if isinstance(self.monthly_limit, (float, int)):
            self.monthly_limit = Decimal(str(self.monthly_limit))

        if isinstance(self.current_spend, (float, int)):
            self.current_spend = Decimal(str(self.current_spend))

    def _validate_budget_id(self):
        """Ensure budget_id follows format BUDGET_{category}_{month}."""
        if not self.budget_id.startswith("BUDGET_"):
            raise ValueError(f"budget_id must start with 'BUDGET_', got '{self.budget_id}'")

        # Check format: BUDGET_{category}_{YYYY_MM}
        pattern = r"^BUDGET_[a-z_]+_\d{4}_\d{2}$"
        if not re.match(pattern, self.budget_id):
            raise ValueError(f"budget_id must match format 'BUDGET_{{category}}_YYYY_MM', got '{self.budget_id}'")

    def _validate_month(self):
        """Ensure month is in YYYY-MM format."""
        pattern = r"^\d{4}-\d{2}$"
        if not re.match(pattern, self.month):
            raise ValueError(f"month must be in YYYY-MM format, got '{self.month}'")

        # Validate it's a real date
        try:
            year, month_num = self.month.split("-")
            year_int = int(year)
            month_int = int(month_num)

            if not (1 <= month_int <= 12):
                raise ValueError(f"Invalid month number: {month_num}")

            if year_int < 2000 or year_int > 2100:
                logger.warning(f"Unusual year in budget: {year_int}")

        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid month format '{self.month}': {e}")

    def _validate_monthly_limit(self):
        """Ensure monthly_limit is positive."""
        if self.monthly_limit <= 0:
            raise ValueError(f"monthly_limit must be positive, got {self.monthly_limit}")

    def _validate_alert_threshold(self):
        """Ensure alert_threshold is between 0.0 and 1.0."""
        if not 0.0 <= self.alert_threshold <= 1.0:
            raise ValueError(f"alert_threshold must be between 0.0 and 1.0, got {self.alert_threshold}")

    def _validate_currency(self):
        """Ensure currency is valid ISO 4217 code."""
        if len(self.currency) != 3 or not self.currency.isupper():
            logger.warning(f"currency may not be valid ISO 4217 code: {self.currency}")

    def get_spend_percentage(self) -> float:
        """
        Get current spending as percentage of monthly limit.

        Returns:
            float: Percentage (0.0-1.0+, can exceed 1.0 for overspending)
        """
        if self.monthly_limit <= 0:
            return 0.0

        return float(self.current_spend / self.monthly_limit)

    def get_remaining_budget(self) -> Decimal:
        """
        Get remaining budget for the month.

        Returns:
            Decimal: Remaining amount (can be negative if overspent)
        """
        return self.monthly_limit - self.current_spend

    def is_overspent(self) -> bool:
        """
        Check if budget is overspent.

        Returns:
            bool: True if current_spend exceeds monthly_limit
        """
        return self.current_spend > self.monthly_limit

    def should_send_alert(self) -> bool:
        """
        Check if alert threshold reached and alert not yet sent.

        Returns:
            bool: True if alert should be sent
        """
        if not self.alerts_enabled:
            return False

        if self.alert_sent:
            return False

        return self.get_spend_percentage() >= self.alert_threshold

    def send_alert(self):
        """Mark alert as sent."""
        self.alert_sent = True
        logger.info(f"Budget alert sent for {self.budget_id} ({self.get_spend_percentage():.0%} spent)")

    def add_expense(self, amount: Decimal) -> Decimal:
        """
        Add expense amount to current spend.

        Args:
            amount: Expense amount to add

        Returns:
            Decimal: Updated current_spend
        """
        self.current_spend += amount
        logger.debug(f"Added ${amount} to {self.budget_id}, new total: ${self.current_spend}")

        # Check if alert threshold crossed
        if self.should_send_alert():
            logger.warning(
                f"Budget threshold reached for {self.category.value}: "
                f"${self.current_spend}/{self.monthly_limit} ({self.get_spend_percentage():.0%})"
            )

        return self.current_spend

    def reset_for_next_month(self, next_month: str, rollover_amount: Optional[Decimal] = None) -> "Budget":
        """
        Create new budget for next month.

        Args:
            next_month: Next month in YYYY-MM format
            rollover_amount: Amount to carry forward (if rollover_enabled)

        Returns:
            Budget: New budget instance for next month
        """
        # Calculate starting balance
        if self.rollover_enabled and rollover_amount is not None:
            starting_spend = Decimal("0.00")
            starting_limit = self.monthly_limit + rollover_amount
        else:
            starting_spend = Decimal("0.00")
            starting_limit = self.monthly_limit

        # Generate new budget_id
        new_budget_id = Budget.generate_id(self.category, next_month)

        return Budget(
            budget_id=new_budget_id,
            category=self.category,
            month=next_month,
            monthly_limit=starting_limit,
            current_spend=starting_spend,
            alerts_enabled=self.alerts_enabled,
            alert_threshold=self.alert_threshold,
            alert_sent=False,
            rollover_enabled=self.rollover_enabled,
            currency=self.currency
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert budget to dictionary for JSON serialization.

        Returns:
            dict: Budget data
        """
        return {
            "budget_id": self.budget_id,
            "category": self.category.value,
            "month": self.month,
            "monthly_limit": float(self.monthly_limit),
            "current_spend": float(self.current_spend),
            "alerts_enabled": self.alerts_enabled,
            "alert_threshold": self.alert_threshold,
            "alert_sent": self.alert_sent,
            "currency": self.currency,
            "rollover_enabled": self.rollover_enabled
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        """
        Create Budget instance from dictionary.

        Args:
            data: Budget data dictionary

        Returns:
            Budget: Budget instance
        """
        # Convert amounts to Decimal
        data["monthly_limit"] = Decimal(str(data["monthly_limit"]))
        data["current_spend"] = Decimal(str(data["current_spend"]))

        # Convert category string to enum
        if isinstance(data["category"], str):
            data["category"] = ExpenseCategory(data["category"])

        return cls(**data)

    @classmethod
    def generate_id(cls, category: ExpenseCategory, month: str) -> str:
        """
        Generate budget ID from category and month.

        Args:
            category: Expense category
            month: Month in YYYY-MM format

        Returns:
            str: Budget ID in format BUDGET_{category}_{YYYY_MM}
        """
        # Convert YYYY-MM to YYYY_MM for budget_id
        month_str = month.replace("-", "_")
        category_str = category.value if isinstance(category, ExpenseCategory) else category

        return f"BUDGET_{category_str}_{month_str}"


# Helper functions for managing budget files

class BudgetFile:
    """
    Manager for monthly budget JSON files.

    Each file contains all budget categories for a given month.
    """

    def __init__(self, vault_path: Path, month: str):
        """
        Initialize budget file manager.

        Args:
            vault_path: Path to vault root
            month: Month in YYYY-MM format
        """
        self.vault_path = vault_path
        self.month = month
        self.budgets_dir = vault_path / "Budgets"
        self.budgets_dir.mkdir(parents=True, exist_ok=True)

        self.file_path = self.budgets_dir / f"{month}.json"

    def load(self) -> List[Budget]:
        """
        Load all budgets for the month.

        Returns:
            List[Budget]: List of budget instances
        """
        if not self.file_path.exists():
            logger.debug(f"Budget file not found: {self.file_path}")
            return []

        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)

            budgets = []
            for budget_data in data.get("budgets", []):
                budget = Budget.from_dict(budget_data)
                budgets.append(budget)

            logger.debug(f"Loaded {len(budgets)} budgets from {self.file_path}")
            return budgets

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to load budgets from {self.file_path}: {e}")
            return []

    def save(self, budgets: List[Budget]):
        """
        Save all budgets for the month.

        Args:
            budgets: List of budget instances
        """
        data = {
            "month": self.month,
            "budgets": [budget.to_dict() for budget in budgets]
        }

        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(budgets)} budgets to {self.file_path}")

        except (OSError, TypeError) as e:
            logger.error(f"Failed to save budgets to {self.file_path}: {e}")
            raise

    def get_budget(self, category: ExpenseCategory) -> Optional[Budget]:
        """
        Get budget for specific category.

        Args:
            category: Expense category

        Returns:
            Budget: Budget instance or None if not found
        """
        budgets = self.load()

        for budget in budgets:
            if budget.category == category:
                return budget

        return None

    def update_budget(self, budget: Budget):
        """
        Update or add a budget for the month.

        Args:
            budget: Budget instance to update
        """
        budgets = self.load()

        # Find and replace existing budget
        found = False
        for i, existing in enumerate(budgets):
            if existing.budget_id == budget.budget_id:
                budgets[i] = budget
                found = True
                break

        # Add if not found
        if not found:
            budgets.append(budget)

        self.save(budgets)


def create_default_budgets(vault_path: Path, month: str) -> List[Budget]:
    """
    Create default budgets for all categories.

    Args:
        vault_path: Path to vault root
        month: Month in YYYY-MM format

    Returns:
        List[Budget]: List of created budgets
    """
    # Default budget allocations
    defaults = {
        ExpenseCategory.SOFTWARE: Decimal("500.00"),
        ExpenseCategory.TRAVEL: Decimal("1000.00"),
        ExpenseCategory.OFFICE: Decimal("200.00"),
        ExpenseCategory.MARKETING: Decimal("300.00"),
        ExpenseCategory.MEALS: Decimal("400.00"),
        ExpenseCategory.TRANSPORTATION: Decimal("250.00"),
        ExpenseCategory.UTILITIES: Decimal("150.00"),
        ExpenseCategory.OTHER: Decimal("200.00"),
    }

    budgets = []
    for category, limit in defaults.items():
        budget = Budget(
            budget_id=Budget.generate_id(category, month),
            category=category,
            month=month,
            monthly_limit=limit,
            currency="USD"
        )
        budgets.append(budget)

    # Save to file
    budget_file = BudgetFile(vault_path, month)
    budget_file.save(budgets)

    logger.info(f"Created default budgets for {month}")
    return budgets
