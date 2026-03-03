"""
Budget Service - Gold Tier US8

Handles budget tracking, validation, and threshold alerts.

Features:
- Monthly budget tracking by category
- Threshold alerts (default 80% spending)
- Budget validation for expenses
- Overspending detection
- Automatic alert creation to /Needs_Action/
"""

import logging
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.models.budget import Budget, BudgetFile, ExpenseCategory, create_default_budgets
from src.models.expense import Expense
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class BudgetService:
    """
    Service for budget tracking and threshold alerts.

    Features:
    - Track spending by category
    - Generate alerts when threshold reached (80% spending)
    - Validate expenses against budgets
    - Auto-create budgets if missing
    - Monthly budget reports
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize BudgetService.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.budgets_dir = self.vault_path / "Budgets"
        self.needs_action_dir = self.vault_path / "Needs_Action"

        # Create directories
        self.budgets_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

        # Initialize audit service
        self.audit_service = AuditService(vault_path=vault_path)

        logger.info(f"BudgetService initialized at {vault_path}")

    def get_budget(self, category: ExpenseCategory, month: str) -> Optional[Budget]:
        """
        Get budget for category and month.

        Args:
            category: Expense category
            month: Month in YYYY-MM format

        Returns:
            Budget: Budget instance or None if not found
        """
        budget_file = BudgetFile(self.vault_path, month)
        return budget_file.get_budget(category)

    def get_all_budgets(self, month: str) -> List[Budget]:
        """
        Get all budgets for a month.

        Args:
            month: Month in YYYY-MM format

        Returns:
            List[Budget]: List of all budgets
        """
        budget_file = BudgetFile(self.vault_path, month)
        return budget_file.load()

    def create_or_update_budget(
        self,
        category: ExpenseCategory,
        month: str,
        monthly_limit: Decimal,
        alert_threshold: float = 0.80,
        alerts_enabled: bool = True,
        rollover_enabled: bool = False
    ) -> Budget:
        """
        Create or update a budget.

        Args:
            category: Expense category
            month: Month in YYYY-MM format
            monthly_limit: Monthly spending limit
            alert_threshold: Threshold for alerts (0.0-1.0)
            alerts_enabled: Whether alerts are enabled
            rollover_enabled: Whether rollover is enabled

        Returns:
            Budget: Created/updated budget
        """
        budget_file = BudgetFile(self.vault_path, month)
        existing = budget_file.get_budget(category)

        if existing:
            # Update existing budget
            existing.monthly_limit = monthly_limit
            existing.alert_threshold = alert_threshold
            existing.alerts_enabled = alerts_enabled
            existing.rollover_enabled = rollover_enabled
            budget = existing
        else:
            # Create new budget
            budget = Budget(
                budget_id=Budget.generate_id(category, month),
                category=category,
                month=month,
                monthly_limit=monthly_limit,
                currency="USD",
                alert_threshold=alert_threshold,
                alerts_enabled=alerts_enabled,
                rollover_enabled=rollover_enabled
            )

        budget_file.update_budget(budget)

        logger.info(f"Created/updated budget for {category.value} in {month}: ${monthly_limit}")

        # Log action
        self.audit_service.log_action(
            action_type="budget_update",
            description=f"Updated budget: {category.value} - ${monthly_limit}/month",
            metadata={
                "category": category.value,
                "month": month,
                "monthly_limit": float(monthly_limit),
                "alert_threshold": alert_threshold
            }
        )

        return budget

    def add_expense_to_budget(self, expense: Expense, send_alerts: bool = True) -> Budget:
        """
        Add expense to budget and check for alerts.

        Args:
            expense: Expense to add
            send_alerts: Whether to send alerts if threshold reached

        Returns:
            Budget: Updated budget
        """
        month = expense.get_month_folder()
        budget_file = BudgetFile(self.vault_path, month)
        budget = budget_file.get_budget(expense.category)

        if not budget:
            # Create default budget if missing
            logger.warning(f"No budget found for {expense.category.value} in {month}, creating default")
            budgets = create_default_budgets(self.vault_path, month)
            budget = next(b for b in budgets if b.category == expense.category)

        # Add expense to budget
        old_spend = budget.current_spend
        budget.add_expense(expense.amount)

        # Save updated budget
        budget_file.update_budget(budget)

        logger.info(
            f"Added ${expense.amount} to {expense.category.value} budget "
            f"(${old_spend} -> ${budget.current_spend})"
        )

        # Check for alerts
        if send_alerts:
            self._check_budget_alerts(budget, expense)

        return budget

    def _check_budget_alerts(self, budget: Budget, expense: Expense):
        """
        Check budget thresholds and create alerts if needed.

        Args:
            budget: Budget to check
            expense: Expense that triggered the check
        """
        # Check for threshold alert
        if budget.should_send_alert():
            self._create_budget_alert(
                budget=budget,
                alert_type="threshold",
                expense=expense
            )
            budget.send_alert()

            # Update budget file to mark alert as sent
            budget_file = BudgetFile(self.vault_path, budget.month)
            budget_file.update_budget(budget)

        # Check for overspending
        if budget.is_overspent() and not budget.alert_sent:
            self._create_budget_alert(
                budget=budget,
                alert_type="overspent",
                expense=expense
            )
            budget.send_alert()

            # Update budget file
            budget_file = BudgetFile(self.vault_path, budget.month)
            budget_file.update_budget(budget)

    def _create_budget_alert(
        self,
        budget: Budget,
        alert_type: str,
        expense: Expense
    ):
        """
        Create budget alert in /Needs_Action/.

        Args:
            budget: Budget that triggered alert
            alert_type: Type of alert (threshold, overspent)
            expense: Expense that triggered alert
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"BUDGET_ALERT_{budget.category.value}_{timestamp}.md"
        file_path = self.needs_action_dir / filename

        # Calculate metrics
        spend_pct = budget.get_spend_percentage()
        remaining = budget.get_remaining_budget()

        # Build frontmatter
        frontmatter = {
            "type": "budget_alert",
            "alert_type": alert_type,
            "category": budget.category.value,
            "month": budget.month,
            "budget_limit": float(budget.monthly_limit),
            "current_spend": float(budget.current_spend),
            "spend_percentage": round(spend_pct, 2),
            "remaining_budget": float(remaining),
            "triggered_by_expense": expense.expense_id,
            "created_at": datetime.now().isoformat(),
            "priority": "high" if alert_type == "overspent" else "medium"
        }

        # Build body
        if alert_type == "threshold":
            emoji = "⚠️"
            title = f"Budget Threshold Alert: {budget.category.value.title()}"
            message = f"You've reached {spend_pct:.0%} of your monthly budget for {budget.category.value}."
        else:  # overspent
            emoji = "🚨"
            title = f"Budget Overspent: {budget.category.value.title()}"
            message = f"You've exceeded your monthly budget for {budget.category.value}."

        body = f"""# {emoji} {title}

{message}

## Budget Summary
- **Category**: {budget.category.value.title()}
- **Month**: {budget.month}
- **Budget Limit**: ${budget.monthly_limit:.2f}
- **Current Spend**: ${budget.current_spend:.2f} ({spend_pct:.0%})
- **Remaining**: ${remaining:.2f}

## Triggered By
- **Expense**: [{expense.expense_id}](/Expenses/{expense.get_month_folder()}/{expense.get_filename()})
- **Amount**: ${expense.amount:.2f}
- **Vendor**: {expense.vendor}
- **Date**: {expense.expense_date}

## Recommended Actions
"""

        if alert_type == "threshold":
            body += """- Review remaining expenses for this month
- Consider adjusting budget if needed
- Monitor future expenses in this category
"""
        else:  # overspent
            body += """- Review all expenses in this category
- Identify any unusual or unnecessary expenses
- Adjust budget for next month if needed
- Consider reallocating from other categories
"""

        body += f"""
## Budget Details
- **Alert Threshold**: {budget.alert_threshold:.0%}
- **Alerts Enabled**: {'Yes' if budget.alerts_enabled else 'No'}

---
*Auto-generated by Budget Service on {datetime.now().strftime('%Y-%m-%d %I:%M %p')}*
"""

        # Write file
        content = self._format_with_frontmatter(frontmatter, body)

        with open(file_path, 'w') as f:
            f.write(content)

        logger.warning(
            f"Created {alert_type} budget alert for {budget.category.value}: "
            f"{spend_pct:.0%} spent (${budget.current_spend}/${budget.monthly_limit})"
        )

        # Log action
        self.audit_service.log_action(
            action_type="budget_alert",
            description=f"Budget {alert_type} alert: {budget.category.value} ({spend_pct:.0%} spent)",
            metadata={
                "category": budget.category.value,
                "month": budget.month,
                "alert_type": alert_type,
                "spend_percentage": round(spend_pct, 2),
                "alert_file": str(file_path)
            }
        )

    def _format_with_frontmatter(self, frontmatter: dict, body: str) -> str:
        """Format content with YAML frontmatter."""
        # Convert frontmatter to YAML
        yaml_lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, str):
                yaml_lines.append(f'{key}: "{value}"')
            elif isinstance(value, bool):
                yaml_lines.append(f'{key}: {str(value).lower()}')
            else:
                yaml_lines.append(f'{key}: {value}')
        yaml_lines.append("---")

        return "\n".join(yaml_lines) + "\n\n" + body

    def validate_expense_against_budget(
        self,
        expense: Expense,
        month: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate expense against budget without adding it.

        Args:
            expense: Expense to validate
            month: Month to check (defaults to expense month)

        Returns:
            dict: Validation result with keys: valid, reason, budget_info
        """
        if month is None:
            month = expense.get_month_folder()

        budget_file = BudgetFile(self.vault_path, month)
        budget = budget_file.get_budget(expense.category)

        if not budget:
            return {
                "valid": False,
                "reason": f"No budget found for {expense.category.value} in {month}",
                "budget_info": None
            }

        # Check if adding expense would exceed budget
        projected_spend = budget.current_spend + expense.amount
        would_exceed = projected_spend > budget.monthly_limit

        if would_exceed:
            overage = projected_spend - budget.monthly_limit
            return {
                "valid": False,
                "reason": f"Would exceed budget by ${overage:.2f}",
                "budget_info": {
                    "current_spend": float(budget.current_spend),
                    "monthly_limit": float(budget.monthly_limit),
                    "projected_spend": float(projected_spend),
                    "overage": float(overage)
                }
            }

        return {
            "valid": True,
            "reason": "Within budget",
            "budget_info": {
                "current_spend": float(budget.current_spend),
                "monthly_limit": float(budget.monthly_limit),
                "projected_spend": float(projected_spend),
                "remaining": float(budget.monthly_limit - projected_spend)
            }
        }

    def get_budget_report(self, month: str) -> Dict[str, Any]:
        """
        Generate budget report for a month.

        Args:
            month: Month in YYYY-MM format

        Returns:
            dict: Budget report with summary and categories
        """
        budgets = self.get_all_budgets(month)

        if not budgets:
            return {
                "month": month,
                "total_budget": 0.0,
                "total_spent": 0.0,
                "categories": [],
                "alerts": []
            }

        total_budget = sum(b.monthly_limit for b in budgets)
        total_spent = sum(b.current_spend for b in budgets)

        categories = []
        alerts = []

        for budget in budgets:
            spend_pct = budget.get_spend_percentage()
            remaining = budget.get_remaining_budget()

            category_info = {
                "category": budget.category.value,
                "monthly_limit": float(budget.monthly_limit),
                "current_spend": float(budget.current_spend),
                "spend_percentage": round(spend_pct, 2),
                "remaining": float(remaining),
                "is_overspent": budget.is_overspent()
            }

            categories.append(category_info)

            # Check for alerts
            if budget.is_overspent():
                alerts.append({
                    "category": budget.category.value,
                    "type": "overspent",
                    "amount": float(budget.current_spend - budget.monthly_limit)
                })
            elif spend_pct >= budget.alert_threshold:
                alerts.append({
                    "category": budget.category.value,
                    "type": "threshold",
                    "percentage": round(spend_pct, 2)
                })

        return {
            "month": month,
            "total_budget": float(total_budget),
            "total_spent": float(total_spent),
            "overall_percentage": round(float(total_spent / total_budget) if total_budget > 0 else 0, 2),
            "categories": sorted(categories, key=lambda x: x["spend_percentage"], reverse=True),
            "alerts": alerts
        }

    def initialize_month_budgets(self, month: str) -> List[Budget]:
        """
        Initialize default budgets for a month if they don't exist.

        Args:
            month: Month in YYYY-MM format

        Returns:
            List[Budget]: Created budgets
        """
        budget_file = BudgetFile(self.vault_path, month)
        existing = budget_file.load()

        if existing:
            logger.info(f"Budgets already exist for {month}")
            return existing

        # Create default budgets
        budgets = create_default_budgets(self.vault_path, month)

        logger.info(f"Initialized {len(budgets)} default budgets for {month}")

        # Log action
        self.audit_service.log_action(
            action_type="budget_initialize",
            description=f"Initialized default budgets for {month}",
            metadata={
                "month": month,
                "budget_count": len(budgets)
            }
        )

        return budgets


def main():
    """Standalone test runner."""
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    vault_path = os.getenv('VAULT_PATH', '.')
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]

    service = BudgetService(vault_path=vault_path)

    # Test: Get current month
    current_month = date.today().strftime("%Y-%m")

    # Initialize budgets
    budgets = service.initialize_month_budgets(current_month)
    logger.info(f"Initialized {len(budgets)} budgets for {current_month}")

    # Get report
    report = service.get_budget_report(current_month)
    logger.info(f"Budget Report for {current_month}:")
    logger.info(f"  Total Budget: ${report['total_budget']:.2f}")
    logger.info(f"  Total Spent: ${report['total_spent']:.2f}")
    logger.info(f"  Overall: {report['overall_percentage']:.0%}")


if __name__ == "__main__":
    main()
