#!/usr/bin/env python3
"""
Odoo MCP Server for Personal AI Employee - Platinum Tier

Provides tools for integrating with Odoo accounting system:
- Create expenses from AI Employee expense entities
- Retrieve budget status and financial reports
- Sync approved expenses to Odoo
- Backup database

Platinum Tier US5 - Cloud-hosted Odoo with professional financial management.

Authentication: Bearer token (Odoo API key)
Deployment: Cloud VM alongside AI Employee
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    import httpx
except ImportError:
    print("ERROR: MCP SDK not installed. Run: uv pip install mcp httpx", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OdooConfig:
    """Odoo instance configuration."""
    url: str  # Odoo instance URL (e.g., https://odoo.example.com)
    database: str  # Odoo database name
    username: str  # Odoo username
    api_key: str  # Odoo API key (Bearer token)
    vault_path: Path  # Path to AI Employee vault


@dataclass
class OdooExpense:
    """Expense record for Odoo."""
    name: str  # Description
    date: str  # Expense date (YYYY-MM-DD)
    amount: float  # Amount in local currency
    category: str  # Expense category
    vendor: Optional[str] = None  # Vendor/merchant name
    notes: Optional[str] = None  # Additional notes
    receipt_path: Optional[str] = None  # Path to receipt file
    ai_employee_id: Optional[str] = None  # Original expense ID from AI Employee


class OdooMCPServer:
    """
    MCP Server for Odoo integration.

    Provides tools for expense tracking, budget management, and financial reporting
    through Odoo accounting system.
    """

    def __init__(self, config: OdooConfig):
        """
        Initialize Odoo MCP server.

        Args:
            config: Odoo configuration
        """
        self.config = config
        self.server = Server("odoo-mcp-server")

        # HTTP client for Odoo API
        self.client = httpx.Client(
            base_url=config.url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        # Load category mappings
        self.category_mappings = self._load_category_mappings()

        # Sync log
        self.sync_log_path = config.vault_path / "Logs" / "odoo_sync.jsonl"
        self.sync_log_path.parent.mkdir(exist_ok=True)

        # Register tools
        self._register_tools()

    def _load_category_mappings(self) -> Dict[str, str]:
        """
        Load category mappings from config file.

        Maps AI Employee categories to Odoo account codes.

        Returns:
            Dictionary mapping category names to Odoo account codes
        """
        config_path = Path(__file__).parent / "config.json"

        if not config_path.exists():
            logger.warning(f"Category mappings not found at {config_path}, using defaults")
            return {
                "food": "600100",  # Food & Dining
                "transport": "600200",  # Transportation
                "utilities": "600300",  # Utilities
                "software": "600400",  # Software & Subscriptions
                "office": "600500",  # Office Supplies
                "marketing": "600600",  # Marketing & Advertising
                "professional": "600700",  # Professional Services
                "other": "600000"  # General Expenses
            }

        try:
            with open(config_path) as f:
                config_data = json.load(f)
                return config_data.get("category_mappings", {})
        except Exception as e:
            logger.error(f"Failed to load category mappings: {e}")
            return {}

    def _register_tools(self):
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available Odoo tools."""
            return [
                Tool(
                    name="odoo_create_expense",
                    description="Create expense entry in Odoo accounting system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Expense description"},
                            "date": {"type": "string", "description": "Expense date (YYYY-MM-DD)"},
                            "amount": {"type": "number", "description": "Expense amount"},
                            "category": {"type": "string", "description": "Expense category"},
                            "vendor": {"type": "string", "description": "Vendor/merchant name (optional)"},
                            "notes": {"type": "string", "description": "Additional notes (optional)"},
                            "receipt_path": {"type": "string", "description": "Path to receipt file (optional)"},
                            "ai_employee_id": {"type": "string", "description": "AI Employee expense ID (optional)"}
                        },
                        "required": ["name", "date", "amount", "category"]
                    }
                ),
                Tool(
                    name="odoo_get_budget_status",
                    description="Get current budget status and spending summary",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "month": {"type": "string", "description": "Month in YYYY-MM format (optional, defaults to current month)"}
                        }
                    }
                ),
                Tool(
                    name="odoo_generate_financial_report",
                    description="Generate financial report for specified period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "report_type": {
                                "type": "string",
                                "enum": ["summary", "detailed", "by_category"],
                                "description": "Report type"
                            }
                        },
                        "required": ["start_date", "end_date"]
                    }
                ),
                Tool(
                    name="odoo_sync_all_expenses",
                    description="Batch sync all approved expenses from AI Employee to Odoo",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "month": {"type": "string", "description": "Month to sync (YYYY-MM, optional)"},
                            "dry_run": {"type": "boolean", "description": "Preview sync without creating entries"}
                        }
                    }
                ),
                Tool(
                    name="odoo_backup_database",
                    description="Create backup of Odoo database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "backup_path": {"type": "string", "description": "Path to save backup file"}
                        },
                        "required": ["backup_path"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute tool by name."""

            if name == "odoo_create_expense":
                result = await self._create_expense(arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "odoo_get_budget_status":
                result = await self._get_budget_status(arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "odoo_generate_financial_report":
                result = await self._generate_financial_report(arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "odoo_sync_all_expenses":
                result = await self._sync_all_expenses(arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "odoo_backup_database":
                result = await self._backup_database(arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"})
                )]

    async def _create_expense(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create expense entry in Odoo.

        Args:
            args: Expense parameters

        Returns:
            Creation result with Odoo expense ID
        """
        try:
            # Build expense data
            expense = OdooExpense(
                name=args["name"],
                date=args["date"],
                amount=args["amount"],
                category=args["category"],
                vendor=args.get("vendor"),
                notes=args.get("notes"),
                receipt_path=args.get("receipt_path"),
                ai_employee_id=args.get("ai_employee_id")
            )

            # Map category to Odoo account
            account_code = self.category_mappings.get(
                expense.category.lower(),
                self.category_mappings.get("other", "600000")
            )

            # Create vendor if needed
            vendor_id = None
            if expense.vendor:
                vendor_id = await self._get_or_create_vendor(expense.vendor)

            # Prepare Odoo API request
            odoo_data = {
                "name": expense.name,
                "date": expense.date,
                "unit_amount": expense.amount,
                "account_id": account_code,
                "employee_id": 1,  # TODO: Configure employee mapping
                "partner_id": vendor_id,
                "description": expense.notes or ""
            }

            # Call Odoo API (POST /api/v1/expenses)
            response = self.client.post(
                "/api/v1/expenses",
                json=odoo_data
            )

            response.raise_for_status()
            result = response.json()

            # Log sync event
            self._log_sync_event({
                "event": "expense_created",
                "odoo_expense_id": result.get("id"),
                "ai_employee_id": expense.ai_employee_id,
                "amount": expense.amount,
                "category": expense.category,
                "vendor": expense.vendor,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"Created expense in Odoo: {result.get('id')}")

            return {
                "success": True,
                "odoo_expense_id": result.get("id"),
                "ai_employee_id": expense.ai_employee_id,
                "message": f"Expense created successfully in Odoo"
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Odoo API error: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"Odoo API error: {e.response.status_code}",
                "details": e.response.text
            }
        except Exception as e:
            logger.error(f"Failed to create expense: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_budget_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get budget status from Odoo.

        Args:
            args: Query parameters (month optional)

        Returns:
            Budget status summary
        """
        try:
            month = args.get("month")
            if not month:
                month = datetime.now().strftime("%Y-%m")

            # Query Odoo API for budget status
            response = self.client.get(
                "/api/v1/budgets",
                params={"month": month}
            )

            response.raise_for_status()
            budget_data = response.json()

            return {
                "success": True,
                "month": month,
                "budget": budget_data
            }

        except Exception as e:
            logger.error(f"Failed to get budget status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_financial_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate financial report from Odoo.

        Args:
            args: Report parameters (start_date, end_date, report_type)

        Returns:
            Financial report data
        """
        try:
            report_type = args.get("report_type", "summary")

            response = self.client.post(
                "/api/v1/reports/financial",
                json={
                    "start_date": args["start_date"],
                    "end_date": args["end_date"],
                    "report_type": report_type
                }
            )

            response.raise_for_status()
            report_data = response.json()

            return {
                "success": True,
                "report": report_data
            }

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _sync_all_expenses(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Batch sync all approved expenses from AI Employee to Odoo.

        Args:
            args: Sync parameters (month optional, dry_run)

        Returns:
            Sync result summary
        """
        try:
            month = args.get("month")
            dry_run = args.get("dry_run", False)

            # Load approved expenses from vault
            expenses_dir = self.config.vault_path / "Expenses"

            if not expenses_dir.exists():
                return {
                    "success": True,
                    "synced_count": 0,
                    "message": "No expenses directory found"
                }

            synced_count = 0
            skipped_count = 0
            errors = []

            for expense_file in expenses_dir.glob("EXPENSE_*.md"):
                # TODO: Parse expense file and check if approved
                # TODO: Check if already synced to Odoo
                # TODO: Call _create_expense if needed
                pass

            return {
                "success": True,
                "synced_count": synced_count,
                "skipped_count": skipped_count,
                "errors": errors,
                "dry_run": dry_run
            }

        except Exception as e:
            logger.error(f"Failed to sync expenses: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _backup_database(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Odoo database backup.

        Args:
            args: Backup parameters (backup_path)

        Returns:
            Backup result
        """
        try:
            backup_path = args["backup_path"]

            # Call Odoo backup API
            response = self.client.post(
                "/web/database/backup",
                json={
                    "master_pwd": os.getenv("ODOO_MASTER_PASSWORD"),
                    "name": self.config.database,
                    "backup_format": "zip"
                },
                timeout=300.0  # 5 minutes for backup
            )

            response.raise_for_status()

            # Save backup file
            with open(backup_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Odoo database backed up to: {backup_path}")

            return {
                "success": True,
                "backup_path": backup_path,
                "size_bytes": len(response.content),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_or_create_vendor(self, vendor_name: str) -> Optional[int]:
        """
        Get existing vendor ID or create new vendor.

        Args:
            vendor_name: Vendor name

        Returns:
            Odoo vendor/partner ID
        """
        try:
            # Search for existing vendor
            response = self.client.get(
                "/api/v1/partners",
                params={"name": vendor_name, "limit": 1}
            )

            response.raise_for_status()
            partners = response.json()

            if partners:
                return partners[0]["id"]

            # Create new vendor
            create_response = self.client.post(
                "/api/v1/partners",
                json={
                    "name": vendor_name,
                    "is_company": True,
                    "supplier_rank": 1
                }
            )

            create_response.raise_for_status()
            new_partner = create_response.json()

            logger.info(f"Created new vendor in Odoo: {vendor_name} (ID: {new_partner['id']})")

            return new_partner["id"]

        except Exception as e:
            logger.error(f"Failed to get/create vendor {vendor_name}: {e}")
            return None

    def _log_sync_event(self, event: Dict[str, Any]):
        """
        Log sync event to odoo_sync.jsonl.

        Args:
            event: Event data
        """
        try:
            with open(self.sync_log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to log sync event: {e}")

    def run(self):
        """Start the MCP server."""
        import asyncio
        from mcp.server.stdio import stdio_server

        logger.info("Starting Odoo MCP Server...")
        logger.info(f"Odoo URL: {self.config.url}")
        logger.info(f"Database: {self.config.database}")
        logger.info(f"Vault path: {self.config.vault_path}")

        async def main():
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )

        asyncio.run(main())


def main():
    """Main entry point for Odoo MCP server."""
    # Load configuration from environment
    config = OdooConfig(
        url=os.getenv("ODOO_URL", "http://localhost:8069"),
        database=os.getenv("ODOO_DATABASE", "odoo"),
        username=os.getenv("ODOO_USERNAME", "admin"),
        api_key=os.getenv("ODOO_API_KEY", ""),
        vault_path=Path(os.getenv("VAULT_PATH", "."))
    )

    # Validate configuration
    if not config.api_key:
        logger.error("ODOO_API_KEY not set in environment")
        sys.exit(1)

    # Create and run server
    server = OdooMCPServer(config)
    server.run()


if __name__ == "__main__":
    main()
