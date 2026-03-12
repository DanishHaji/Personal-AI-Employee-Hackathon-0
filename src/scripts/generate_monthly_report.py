#!/usr/bin/env python3
"""
Generate Monthly Financial Report - Platinum Tier US5

Generates comprehensive monthly financial report pulling data from:
- Odoo accounting system (if enabled)
- Local expense tracking
- Budget status and variance
- Category breakdowns
- Vendor analysis

Output: /Reports/Financial/YYYY-MM_Financial_Report.md

Usage:
    python3 -m src.scripts.generate_monthly_report [YYYY-MM]

Example:
    python3 -m src.scripts.generate_monthly_report 2026-03

If no month specified, uses current month.
"""

import os
import sys
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.models.expense import Expense, ExpenseCategory
from src.models.budget import BudgetFile
from src.services.expense_service import ExpenseService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class MonthlyReportGenerator:
    """Generate comprehensive monthly financial reports."""

    def __init__(self, vault_path: Path, expense_service: ExpenseService):
        """
        Initialize report generator.

        Args:
            vault_path: Path to Obsidian vault
            expense_service: ExpenseService instance
        """
        self.vault_path = vault_path
        self.expense_service = expense_service
        self.reports_dir = vault_path / "Reports" / "Financial"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, month: str) -> Path:
        """
        Generate monthly financial report.

        Args:
            month: Month in YYYY-MM format

        Returns:
            Path to generated report
        """
        logger.info(f"Generating monthly financial report for {month}")

        # Collect data
        expenses = self._load_month_expenses(month)
        budgets = self._load_month_budgets(month)
        odoo_data = self._get_odoo_data(month) if self.expense_service.odoo_enabled else None

        # Generate report sections
        report_content = self._generate_report_content(month, expenses, budgets, odoo_data)

        # Write report file
        report_file = self.reports_dir / f"{month}_Financial_Report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ Monthly report generated: {report_file}")

        return report_file

    def _load_month_expenses(self, month: str) -> List[Expense]:
        """Load all expenses for the month."""
        expenses = []
        month_dir = self.vault_path / "Expenses" / month

        if not month_dir.exists():
            logger.warning(f"No expenses directory found for {month}")
            return expenses

        for expense_file in month_dir.glob("EXPENSE_*.md"):
            try:
                expense = Expense.load_from_file(expense_file)[0]
                expenses.append(expense)
            except Exception as e:
                logger.debug(f"Error loading {expense_file}: {e}")

        logger.info(f"Loaded {len(expenses)} expenses for {month}")
        return expenses

    def _load_month_budgets(self, month: str) -> List:
        """Load all budgets for the month."""
        budget_file = BudgetFile(self.vault_path, month)
        budgets = budget_file.load()
        logger.info(f"Loaded {len(budgets)} budgets for {month}")
        return budgets

    def _get_odoo_data(self, month: str) -> Optional[Dict]:
        """Get financial data from Odoo."""
        try:
            budget_status = self.expense_service.get_budget_status_from_odoo(month)
            return budget_status
        except Exception as e:
            logger.error(f"Failed to get Odoo data: {e}")
            return None

    def _generate_report_content(
        self,
        month: str,
        expenses: List[Expense],
        budgets: List,
        odoo_data: Optional[Dict]
    ) -> str:
        """Generate markdown content for the report."""

        # Calculate totals
        total_expenses = sum(e.amount for e in expenses)
        total_budget = sum(b.monthly_limit for b in budgets)
        approved_expenses = [e for e in expenses if e.approval_status.value == "approved"]
        pending_expenses = [e for e in expenses if e.approval_status.value == "pending"]

        # Category breakdown
        category_spending = {}
        for expense in expenses:
            cat = expense.category.value
            category_spending[cat] = category_spending.get(cat, Decimal("0.00")) + expense.amount

        # Budget variance
        budget_variance = {}
        for budget in budgets:
            cat = budget.category.value
            spent = category_spending.get(cat, Decimal("0.00"))
            variance = budget.monthly_limit - spent
            budget_variance[cat] = {
                "budget": budget.monthly_limit,
                "spent": spent,
                "variance": variance,
                "percentage": float(spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
            }

        # Top vendors
        vendor_spending = {}
        for expense in expenses:
            vendor = expense.vendor
            vendor_spending[vendor] = vendor_spending.get(vendor, Decimal("0.00")) + expense.amount

        top_vendors = sorted(vendor_spending.items(), key=lambda x: x[1], reverse=True)[:10]

        # Build report
        report = f"""---
type: financial_report
month: {month}
generated_at: {datetime.now().isoformat()}
total_expenses: {float(total_expenses)}
total_budget: {float(total_budget)}
odoo_synced: {self.expense_service.odoo_enabled}
---

# Monthly Financial Report: {month}

**Generated**: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

## Executive Summary

| Metric | Amount | Status |
|--------|--------|--------|
| **Total Expenses** | ${total_expenses:,.2f} | {self._get_status_emoji(total_expenses, total_budget)} |
| **Total Budget** | ${total_budget:,.2f} | - |
| **Variance** | ${total_budget - total_expenses:,.2f} | {"✅ Under Budget" if total_expenses <= total_budget else "⚠️ Over Budget"} |
| **Utilization** | {float(total_expenses / total_budget * 100) if total_budget > 0 else 0:.1f}% | - |

**Expense Breakdown**:
- ✅ Approved: {len(approved_expenses)} expenses (${sum(e.amount for e in approved_expenses):,.2f})
- ⏳ Pending: {len(pending_expenses)} expenses (${sum(e.amount for e in pending_expenses):,.2f})

"""

        # Odoo integration status
        if odoo_data:
            report += f"""
## Odoo Integration Status

✅ **Connected to Odoo Accounting**

- Expenses synced to Odoo this month
- Real-time budget tracking enabled
- [View in Odoo]({self.expense_service.odoo_url}/accounting/reports/{month})

"""
        else:
            report += """
## Odoo Integration

ℹ️ Odoo integration not configured or disabled.

"""

        # Budget variance by category
        report += """
## Budget Performance by Category

| Category | Budget | Spent | Remaining | Utilization |
|----------|--------|-------|-----------|-------------|
"""

        for cat in sorted(budget_variance.keys()):
            data = budget_variance[cat]
            emoji = "✅" if data["percentage"] < 80 else "⚠️" if data["percentage"] < 100 else "❌"
            report += (
                f"| {cat.title()} {emoji} "
                f"| ${data['budget']:,.2f} "
                f"| ${data['spent']:,.2f} "
                f"| ${data['variance']:,.2f} "
                f"| {data['percentage']:.1f}% |\n"
            )

        # Top vendors
        report += """

## Top 10 Vendors by Spending

| Rank | Vendor | Amount |
|------|--------|--------|
"""

        for i, (vendor, amount) in enumerate(top_vendors, 1):
            report += f"| {i} | {vendor} | ${amount:,.2f} |\n"

        # Monthly trends (if previous month data exists)
        prev_month = self._get_previous_month(month)
        prev_expenses = self._load_month_expenses(prev_month)

        if prev_expenses:
            prev_total = sum(e.amount for e in prev_expenses)
            change = total_expenses - prev_total
            change_pct = float(change / prev_total * 100) if prev_total > 0 else 0

            trend_emoji = "📈" if change > 0 else "📉"
            trend_text = "increase" if change > 0 else "decrease"

            report += f"""

## Month-over-Month Comparison

Compared to {prev_month}:

- **Previous Month**: ${prev_total:,.2f}
- **Current Month**: ${total_expenses:,.2f}
- **Change**: {trend_emoji} ${abs(change):,.2f} ({abs(change_pct):.1f}% {trend_text})

"""

        # Action items
        report += """
## Action Items

"""

        # Add warnings for over-budget categories
        over_budget = [cat for cat, data in budget_variance.items() if data["percentage"] >= 100]
        if over_budget:
            report += "### ⚠️ Budget Overages\n\n"
            for cat in over_budget:
                data = budget_variance[cat]
                report += f"- **{cat.title()}**: Over by ${abs(data['variance']):,.2f} ({data['percentage']:.1f}%)\n"
            report += "\n"

        # Pending approvals
        if pending_expenses:
            report += "### ⏳ Pending Approvals\n\n"
            report += f"{len(pending_expenses)} expenses awaiting approval (${sum(e.amount for e in pending_expenses):,.2f} total)\n\n"

        # Footer
        report += f"""
---

**Report Details**:
- Expenses Analyzed: {len(expenses)}
- Budget Categories: {len(budgets)}
- Data Source: {"Odoo + Local Vault" if self.expense_service.odoo_enabled else "Local Vault"}
- Report Location: `{self.reports_dir / f"{month}_Financial_Report.md"}`

*Generated by Personal AI Employee - Platinum Tier Financial Reporting*
"""

        return report

    def _get_status_emoji(self, spent: Decimal, budget: Decimal) -> str:
        """Get status emoji based on spending percentage."""
        if budget <= 0:
            return "ℹ️"

        pct = float(spent / budget)

        if pct < 0.8:
            return "✅"
        elif pct < 1.0:
            return "⚠️"
        else:
            return "❌"

    def _get_previous_month(self, month: str) -> str:
        """Get previous month in YYYY-MM format."""
        year, month_num = map(int, month.split("-"))

        if month_num == 1:
            return f"{year - 1}-12"
        else:
            return f"{year}-{month_num - 1:02d}"


def main():
    """Main entry point."""
    # Get vault path
    vault_path = os.getenv("VAULT_PATH")
    if not vault_path:
        logger.error("VAULT_PATH environment variable not set")
        sys.exit(1)

    vault_path = Path(vault_path).resolve()

    # Get month from args or use current
    if len(sys.argv) > 1:
        month = sys.argv[1]
    else:
        month = date.today().strftime("%Y-%m")

    logger.info(f"Generating monthly report for {month}")

    # Initialize expense service
    odoo_url = os.getenv("ODOO_URL")
    odoo_api_key = os.getenv("ODOO_API_KEY")
    odoo_database = os.getenv("ODOO_DATABASE")

    expense_service = ExpenseService(
        vault_path=vault_path,
        odoo_url=odoo_url,
        odoo_api_key=odoo_api_key,
        odoo_database=odoo_database
    )

    # Generate report
    generator = MonthlyReportGenerator(vault_path, expense_service)

    try:
        report_path = generator.generate_report(month)
        logger.info(f"✅ Report saved to: {report_path}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"Monthly Financial Report Generated")
        print(f"{'='*60}")
        print(f"Month: {month}")
        print(f"Report: {report_path}")
        print(f"{'='*60}\n")

    except Exception as e:
        logger.exception(f"Failed to generate report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
