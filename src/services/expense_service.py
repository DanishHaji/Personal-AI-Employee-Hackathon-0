"""
Expense Service - Gold Tier US8

Handles expense tracking with OCR extraction from receipts.

Features:
- OCR text extraction from receipts (PDF and images)
- Expense parsing (amount, vendor, date, category)
- Category keyword matching
- Budget validation
- Unusual expense detection (3x category average)
- Google Vision API fallback for low OCR confidence
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import json

# OCR and image processing
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR not available - install with: pip install easyocr")

try:
    from google.cloud import vision
    VISION_API_AVAILABLE = True
except ImportError:
    VISION_API_AVAILABLE = False
    logging.warning("Google Vision API not available - install with: pip install google-cloud-vision")

# PDF processing
try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logging.warning("pdf2image not available - install with: pip install pdf2image")

from src.models.expense import Expense, ExpenseCategory, save_expense, ApprovalStatus
from src.models.budget import BudgetFile
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Odoo integration (Platinum Tier US5)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logging.warning("httpx not available - Odoo sync disabled. Install with: pip install httpx")


class ExpenseService:
    """
    Service for expense tracking with OCR extraction from receipts.

    Features:
    - Extract text from receipt images and PDFs using EasyOCR
    - Parse expense details (amount, vendor, date, category)
    - Validate against budgets
    - Detect unusual expenses
    - Auto-approve recurring vendors
    - Create expense entity files
    """

    def __init__(
        self,
        vault_path: str | Path,
        use_vision_api: bool = False,
        vision_api_threshold: float = 0.75,
        odoo_url: Optional[str] = None,
        odoo_api_key: Optional[str] = None,
        odoo_database: Optional[str] = None
    ):
        """
        Initialize ExpenseService.

        Args:
            vault_path: Path to Obsidian vault
            use_vision_api: Whether to use Google Vision API for low confidence OCR
            vision_api_threshold: OCR confidence threshold to trigger Vision API fallback
            odoo_url: Odoo instance URL (optional, for Platinum Tier)
            odoo_api_key: Odoo API key (optional, for Platinum Tier)
            odoo_database: Odoo database name (optional, for Platinum Tier)
        """
        self.vault_path = Path(vault_path)
        self.use_vision_api = use_vision_api and VISION_API_AVAILABLE
        self.vision_api_threshold = vision_api_threshold

        # Odoo configuration (Platinum Tier US5)
        self.odoo_url = odoo_url
        self.odoo_api_key = odoo_api_key
        self.odoo_database = odoo_database
        self.odoo_enabled = bool(odoo_url and odoo_api_key and HTTPX_AVAILABLE)
        self._odoo_client = None

        # Initialize directories
        self.expenses_dir = self.vault_path / "Expenses"
        self.receipts_dir = self.vault_path / "Receipts"
        self.budgets_dir = self.vault_path / "Budgets"

        self.expenses_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.budgets_dir.mkdir(parents=True, exist_ok=True)

        # Initialize EasyOCR reader (lazy loading)
        self._ocr_reader = None

        # Initialize Google Vision client (lazy loading)
        self._vision_client = None

        # Initialize audit service
        self.audit_service = AuditService(vault_path=vault_path)

        # Category keywords for matching
        self.category_keywords = {
            ExpenseCategory.SOFTWARE: [
                "adobe", "github", "aws", "azure", "cloud", "subscription", "saas",
                "software", "license", "api", "hosting", "domain", "ssl"
            ],
            ExpenseCategory.TRAVEL: [
                "flight", "airline", "hotel", "airbnb", "uber", "lyft", "rental car",
                "airport", "booking", "expedia", "travel", "accommodation"
            ],
            ExpenseCategory.OFFICE: [
                "staples", "office depot", "amazon", "desk", "chair", "supplies",
                "printer", "paper", "pens", "office"
            ],
            ExpenseCategory.MARKETING: [
                "google ads", "facebook ads", "linkedin", "marketing", "advertising",
                "campaign", "social media", "seo", "analytics"
            ],
            ExpenseCategory.MEALS: [
                "restaurant", "cafe", "coffee", "lunch", "dinner", "breakfast",
                "food", "delivery", "uber eats", "doordash", "grubhub"
            ],
            ExpenseCategory.TRANSPORTATION: [
                "gas", "fuel", "parking", "toll", "transit", "subway", "bus",
                "taxi", "uber", "lyft", "metro"
            ],
            ExpenseCategory.UTILITIES: [
                "electric", "gas", "water", "internet", "phone", "utility",
                "verizon", "att", "comcast", "spectrum"
            ]
        }

        # Known recurring vendors (for auto-approval)
        self.recurring_vendors = set()
        self._load_recurring_vendors()

        # Load Odoo category mappings
        if self.odoo_enabled:
            self._load_odoo_config()

        logger.info(
            f"ExpenseService initialized "
            f"(OCR: {EASYOCR_AVAILABLE}, Vision API: {self.use_vision_api}, Odoo: {self.odoo_enabled})"
        )

    @property
    def ocr_reader(self):
        """Lazy load EasyOCR reader."""
        if self._ocr_reader is None and EASYOCR_AVAILABLE:
            logger.info("Initializing EasyOCR reader (this may take a moment)...")
            self._ocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR reader initialized")
        return self._ocr_reader

    @property
    def vision_client(self):
        """Lazy load Google Vision client."""
        if self._vision_client is None and self.use_vision_api:
            self._vision_client = vision.ImageAnnotatorClient()
            logger.info("Google Vision API client initialized")
        return self._vision_client

    def _load_recurring_vendors(self):
        """Load known recurring vendors from past expenses."""
        # Load past expenses and track vendors with 3+ occurrences
        vendor_counts = {}

        # Scan past 6 months of expenses
        for expense_file in self.expenses_dir.rglob("EXPENSE_*.md"):
            try:
                expense = Expense.load_from_file(expense_file)[0]
                vendor = expense.vendor.lower()
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            except Exception as e:
                logger.debug(f"Error loading expense {expense_file}: {e}")

        # Mark vendors with 3+ occurrences as recurring
        self.recurring_vendors = {v for v, count in vendor_counts.items() if count >= 3}
        logger.debug(f"Loaded {len(self.recurring_vendors)} recurring vendors")

    def extract_text_from_receipt(
        self,
        receipt_path: str | Path,
        use_vision_fallback: bool = True
    ) -> Tuple[str, float]:
        """
        Extract text from receipt image or PDF using OCR.

        Args:
            receipt_path: Path to receipt file (image or PDF)
            use_vision_fallback: Use Google Vision API if EasyOCR confidence is low

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)
        """
        receipt_path = Path(receipt_path)

        if not receipt_path.exists():
            raise FileNotFoundError(f"Receipt file not found: {receipt_path}")

        # Convert PDF to image if needed
        if receipt_path.suffix.lower() == '.pdf':
            if not PDF2IMAGE_AVAILABLE:
                raise RuntimeError("PDF processing requires pdf2image: pip install pdf2image")

            logger.info(f"Converting PDF to image: {receipt_path}")
            images = pdf2image.convert_from_path(receipt_path)

            if not images:
                raise ValueError(f"No images extracted from PDF: {receipt_path}")

            # Use first page only for receipts
            image_path = receipt_path.with_suffix('.png')
            images[0].save(image_path)
            receipt_path = image_path

        # Extract text using EasyOCR
        text, confidence = self._extract_with_easyocr(receipt_path)

        # Fallback to Google Vision API if confidence is low
        if use_vision_fallback and self.use_vision_api and confidence < self.vision_api_threshold:
            logger.info(f"Low OCR confidence ({confidence:.2f}), trying Google Vision API...")
            vision_text, vision_confidence = self._extract_with_vision_api(receipt_path)

            if vision_confidence > confidence:
                logger.info(f"Using Vision API result (confidence: {vision_confidence:.2f})")
                return vision_text, vision_confidence

        return text, confidence

    def _extract_with_easyocr(self, image_path: Path) -> Tuple[str, float]:
        """
        Extract text using EasyOCR.

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)
        """
        if not EASYOCR_AVAILABLE:
            raise RuntimeError("EasyOCR not available - install with: pip install easyocr")

        logger.info(f"Extracting text with EasyOCR from {image_path.name}")

        try:
            # Read image and extract text
            results = self.ocr_reader.readtext(str(image_path))

            if not results:
                logger.warning(f"No text extracted from {image_path}")
                return "", 0.0

            # Combine text and calculate average confidence
            text_parts = []
            confidences = []

            for (bbox, text, conf) in results:
                text_parts.append(text)
                confidences.append(conf)

            extracted_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            logger.info(f"EasyOCR extracted {len(text_parts)} text blocks (confidence: {avg_confidence:.2f})")

            return extracted_text, avg_confidence

        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}", exc_info=True)
            return "", 0.0

    def _extract_with_vision_api(self, image_path: Path) -> Tuple[str, float]:
        """
        Extract text using Google Vision API.

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)
        """
        if not VISION_API_AVAILABLE:
            logger.warning("Google Vision API not available")
            return "", 0.0

        logger.info(f"Extracting text with Vision API from {image_path.name}")

        try:
            # Read image
            with open(image_path, 'rb') as f:
                content = f.read()

            image = vision.Image(content=content)

            # Perform text detection
            response = self.vision_client.text_detection(image=image)

            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")

            texts = response.text_annotations

            if not texts:
                logger.warning(f"No text detected by Vision API from {image_path}")
                return "", 0.0

            # First annotation contains full text
            extracted_text = texts[0].description

            # Vision API doesn't provide confidence scores, use high confidence
            confidence = 0.95

            logger.info(f"Vision API extracted text (confidence: {confidence:.2f})")

            return extracted_text, confidence

        except Exception as e:
            logger.error(f"Vision API extraction failed: {e}", exc_info=True)
            return "", 0.0

    def parse_expense_from_text(
        self,
        text: str,
        ocr_confidence: float,
        receipt_path: str | Path
    ) -> Dict[str, Any]:
        """
        Parse expense details from OCR text.

        Args:
            text: Extracted text from receipt
            ocr_confidence: OCR extraction confidence
            receipt_path: Path to receipt file

        Returns:
            dict: Parsed expense data with keys: amount, vendor, date, category, confidence
        """
        logger.info("Parsing expense from OCR text")

        # Extract amount
        amount = self._extract_amount(text)

        # Extract vendor
        vendor = self._extract_vendor(text)

        # Extract date
        expense_date = self._extract_date(text)

        # Categorize based on vendor and text
        category = self._categorize_expense(vendor, text)

        # Extract description (first few meaningful lines)
        description = self._extract_description(text)

        return {
            "amount": amount,
            "vendor": vendor,
            "date": expense_date,
            "category": category,
            "description": description,
            "confidence": ocr_confidence
        }

    def _extract_amount(self, text: str) -> Decimal:
        """Extract total amount from receipt text."""
        # Common patterns for total amount
        patterns = [
            r"total[:\s]+\$?\s*([\d,]+\.?\d{2})",
            r"amount due[:\s]+\$?\s*([\d,]+\.?\d{2})",
            r"balance[:\s]+\$?\s*([\d,]+\.?\d{2})",
            r"\$\s*([\d,]+\.\d{2})",
        ]

        amounts = []

        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    # Remove commas and convert to Decimal
                    amount_str = match.replace(",", "")
                    amount = Decimal(amount_str)
                    amounts.append(amount)
                except (ValueError, Exception):
                    continue

        # Return largest amount found (likely the total)
        if amounts:
            return max(amounts)

        logger.warning("No amount found in receipt text")
        return Decimal("0.00")

    def _extract_vendor(self, text: str) -> str:
        """Extract vendor/merchant name from receipt text."""
        # First line often contains vendor name
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return "Unknown Vendor"

        # First meaningful line (>3 characters) is likely vendor
        for line in lines[:5]:
            if len(line) > 3 and not line.replace('.', '').replace('$', '').isdigit():
                return line

        return lines[0] if lines else "Unknown Vendor"

    def _extract_date(self, text: str) -> Optional[date]:
        """Extract expense date from receipt text."""
        # Common date patterns
        patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # MM/DD/YYYY or DD/MM/YYYY
            r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",  # YYYY-MM-DD
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}",  # Month DD, YYYY
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                try:
                    # Try parsing first match
                    date_str = matches[0]
                    # Try multiple formats
                    for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                except Exception as e:
                    logger.debug(f"Failed to parse date '{matches[0]}': {e}")

        # Default to today if no date found
        logger.warning("No date found in receipt, using today")
        return date.today()

    def _extract_description(self, text: str) -> Optional[str]:
        """Extract description from receipt text."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Take first 2-3 meaningful lines as description
        description_lines = []
        for line in lines[:5]:
            if len(line) > 5 and not line.replace('.', '').replace('$', '').isdigit():
                description_lines.append(line)
                if len(description_lines) >= 2:
                    break

        if description_lines:
            return " - ".join(description_lines)

        return None

    def _categorize_expense(self, vendor: str, text: str) -> ExpenseCategory:
        """
        Categorize expense based on vendor and text keywords.

        Args:
            vendor: Vendor name
            text: Full receipt text

        Returns:
            ExpenseCategory: Matched category or OTHER
        """
        # Combine vendor and text for matching
        combined_text = f"{vendor} {text}".lower()

        # Count keyword matches for each category
        category_scores = {}

        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            logger.info(f"Categorized as {best_category.value} (score: {category_scores[best_category]})")
            return best_category

        logger.warning("No category matched, defaulting to OTHER")
        return ExpenseCategory.OTHER

    def create_expense_from_receipt(
        self,
        receipt_path: str | Path,
        month: str,
        auto_approve: bool = True
    ) -> Expense:
        """
        Process receipt and create expense entity.

        Args:
            receipt_path: Path to receipt file
            month: Month for budget allocation (YYYY-MM)
            auto_approve: Whether to auto-approve if possible

        Returns:
            Expense: Created expense instance
        """
        receipt_path = Path(receipt_path)

        logger.info(f"Processing receipt: {receipt_path.name}")

        # Extract text from receipt
        text, ocr_confidence = self.extract_text_from_receipt(receipt_path)

        if not text:
            raise ValueError(f"No text extracted from receipt: {receipt_path}")

        # Parse expense details
        expense_data = self.parse_expense_from_text(text, ocr_confidence, receipt_path)

        # Get budget category ID
        category = ExpenseCategory(expense_data["category"])
        from src.models.budget import Budget
        budget_category_id = Budget.generate_id(category, month)

        # Generate expense ID (get next sequence number for the day)
        expense_date = expense_data["date"] or date.today()
        sequence = self._get_next_expense_sequence(expense_date)

        # Create expense from OCR data
        expense = Expense.from_ocr_data(
            ocr_data=expense_data,
            receipt_file=str(receipt_path),
            budget_category_id=budget_category_id,
            expense_date=expense_date,
            sequence=sequence
        )

        # Auto-approve logic
        if auto_approve:
            vendor_lower = expense.vendor.lower()

            # Check if recurring vendor
            if vendor_lower in self.recurring_vendors:
                expense.approve(approved_by="auto_recurring")
                logger.info(f"Auto-approved recurring vendor: {expense.vendor}")

            # Check budget and approve if within limits
            elif self._check_budget_approval(expense, month):
                expense.approve(approved_by="auto_budget")
                logger.info(f"Auto-approved within budget: {expense.vendor}")

            # Check for unusual amount
            elif self._is_unusual_expense(expense):
                expense.flag_for_review("Unusually high amount (3x category average)")
                logger.warning(f"Flagged unusual expense: {expense.vendor} - ${expense.amount}")

        # Save expense
        save_expense(expense, self.vault_path)

        # Log action
        self.audit_service.log_action(
            action_type="expense_record",
            description=f"Recorded expense: {expense.vendor} - ${expense.amount}",
            metadata={
                "expense_id": expense.expense_id,
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category.value,
                "approval_status": expense.approval_status.value
            }
        )

        logger.info(f"Created expense: {expense.expense_id} ({expense.approval_status.value})")

        return expense

    def _get_next_expense_sequence(self, expense_date: date) -> int:
        """Get next sequence number for expenses on the given date."""
        # Find existing expenses for the date
        pattern = f"EXPENSE_{expense_date.strftime('%Y_%m_%d')}_*"
        month_folder = self.expenses_dir / expense_date.strftime("%Y-%m")

        if not month_folder.exists():
            return 1

        existing = list(month_folder.glob(f"{pattern}.md"))
        return len(existing) + 1

    def _check_budget_approval(self, expense: Expense, month: str) -> bool:
        """Check if expense can be auto-approved based on budget."""
        budget_file = BudgetFile(self.vault_path, month)
        budget = budget_file.get_budget(expense.category)

        if not budget:
            logger.warning(f"No budget found for {expense.category.value} in {month}")
            return False

        # Check if adding expense would exceed budget
        projected_spend = budget.current_spend + expense.amount

        if projected_spend > budget.monthly_limit:
            logger.warning(f"Expense would exceed budget: ${projected_spend} > ${budget.monthly_limit}")
            return False

        return True

    def _is_unusual_expense(self, expense: Expense) -> bool:
        """Check if expense is unusually high (3x category average)."""
        # Calculate category average from past expenses
        category_expenses = []

        for expense_file in self.expenses_dir.rglob(f"EXPENSE_*.md"):
            try:
                past_expense = Expense.load_from_file(expense_file)[0]
                if past_expense.category == expense.category:
                    category_expenses.append(past_expense.amount)
            except Exception:
                continue

        if not category_expenses:
            # No history, can't determine if unusual
            return False

        avg_amount = sum(category_expenses) / len(category_expenses)

        # Flag if 3x or more than average
        if expense.amount >= (avg_amount * 3):
            logger.info(f"Unusual expense detected: ${expense.amount} vs avg ${avg_amount:.2f}")
            return True

        return False

    # ==================== Odoo Integration (Platinum Tier US5) ====================

    @property
    def odoo_client(self):
        """Lazy load httpx client for Odoo API."""
        if self._odoo_client is None and self.odoo_enabled:
            self._odoo_client = httpx.Client(
                base_url=self.odoo_url,
                headers={
                    "Authorization": f"Bearer {self.odoo_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            logger.info("Odoo API client initialized")
        return self._odoo_client

    def _load_odoo_config(self):
        """Load Odoo category mappings from config.json."""
        config_path = Path(__file__).parent.parent.parent / "mcp-servers" / "odoo" / "config.json"

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            self.odoo_category_mappings = config.get("category_mappings", {})
            self.odoo_default_account = config.get("default_account", "600000")

            logger.info(f"Loaded {len(self.odoo_category_mappings)} Odoo category mappings")

        except Exception as e:
            logger.warning(f"Failed to load Odoo config: {e}")
            self.odoo_category_mappings = {}
            self.odoo_default_account = "600000"

    def sync_expense_to_odoo(self, expense: Expense) -> bool:
        """
        Sync approved expense to Odoo accounting system.

        Args:
            expense: Expense to sync (must be approved)

        Returns:
            bool: True if sync successful, False otherwise
        """
        if not self.odoo_enabled:
            logger.debug("Odoo sync disabled - skipping")
            return False

        if expense.approval_status != ApprovalStatus.APPROVED:
            logger.warning(f"Cannot sync unapproved expense: {expense.expense_id}")
            return False

        try:
            # Map category to Odoo account code
            category_key = expense.category.value.lower()
            account_code = self.odoo_category_mappings.get(category_key, self.odoo_default_account)

            # Prepare expense data
            expense_data = {
                "date": expense.expense_date.isoformat(),
                "amount": float(expense.amount),
                "currency": expense.currency,
                "vendor": expense.vendor,
                "description": expense.description or f"{expense.category.value} expense",
                "category": expense.category.value,
                "account_code": account_code,
                "reference": expense.expense_id,
                "receipt_url": expense.receipt_file
            }

            # Call Odoo API to create expense
            response = self.odoo_client.post(
                f"/api/expenses",
                json=expense_data
            )

            if response.status_code in (200, 201):
                logger.info(f"✅ Synced expense {expense.expense_id} to Odoo")

                # Log sync event
                self._log_odoo_sync(expense.expense_id, "success", response.json())
                return True
            else:
                logger.error(f"Odoo sync failed: {response.status_code} - {response.text}")
                self._log_odoo_sync(expense.expense_id, "failed", {"error": response.text})
                return False

        except Exception as e:
            logger.exception(f"Error syncing expense {expense.expense_id} to Odoo: {e}")
            self._log_odoo_sync(expense.expense_id, "error", {"error": str(e)})
            return False

    def sync_all_approved_expenses(self, month: Optional[str] = None) -> Dict[str, int]:
        """
        Batch sync all approved expenses to Odoo.

        Args:
            month: Month to sync in YYYY-MM format (default: current month)

        Returns:
            dict: Sync results with counts: {synced: int, failed: int, skipped: int}
        """
        if not self.odoo_enabled:
            logger.warning("Odoo sync disabled")
            return {"synced": 0, "failed": 0, "skipped": 0}

        # Determine month to sync
        if month is None:
            month = date.today().strftime("%Y-%m")

        logger.info(f"Starting batch sync for month: {month}")

        # Find all approved expenses for the month
        month_dir = self.expenses_dir / month
        if not month_dir.exists():
            logger.warning(f"No expenses found for month: {month}")
            return {"synced": 0, "failed": 0, "skipped": 0}

        results = {"synced": 0, "failed": 0, "skipped": 0}

        for expense_file in month_dir.glob("EXPENSE_*.md"):
            try:
                expense = Expense.load_from_file(expense_file)[0]

                # Check if already synced
                if self._is_synced_to_odoo(expense.expense_id):
                    logger.debug(f"Expense {expense.expense_id} already synced - skipping")
                    results["skipped"] += 1
                    continue

                # Sync to Odoo
                if self.sync_expense_to_odoo(expense):
                    results["synced"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(f"Error processing {expense_file}: {e}")
                results["failed"] += 1

        logger.info(
            f"Batch sync complete: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

        return results

    def get_budget_status_from_odoo(self, month: str) -> Optional[Dict]:
        """
        Get current budget status from Odoo.

        Args:
            month: Month in YYYY-MM format

        Returns:
            dict: Budget status or None if failed
        """
        if not self.odoo_enabled:
            return None

        try:
            response = self.odoo_client.get(
                f"/api/budget",
                params={"month": month}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get budget status: {response.status_code}")
                return None

        except Exception as e:
            logger.exception(f"Error getting budget status from Odoo: {e}")
            return None

    def check_budget_warnings(self, month: str) -> List[Dict]:
        """
        Check for budget warnings from Odoo and create alerts.

        Args:
            month: Month in YYYY-MM format

        Returns:
            list: List of budget warnings
        """
        warnings = []

        budget_status = self.get_budget_status_from_odoo(month)
        if not budget_status:
            return warnings

        # Check each category for threshold breaches
        for category_data in budget_status.get("categories", []):
            category = category_data.get("category")
            spent = Decimal(str(category_data.get("spent", 0)))
            budget = Decimal(str(category_data.get("budget", 0)))

            if budget > 0:
                percentage = float(spent / budget)

                # Warning at 80%
                if percentage >= 0.80 and percentage < 1.0:
                    warnings.append({
                        "category": category,
                        "level": "warning",
                        "percentage": percentage,
                        "spent": float(spent),
                        "budget": float(budget),
                        "message": f"{category} budget at {percentage:.0%} ({spent}/{budget})"
                    })

                # Critical at 100%+
                elif percentage >= 1.0:
                    warnings.append({
                        "category": category,
                        "level": "critical",
                        "percentage": percentage,
                        "spent": float(spent),
                        "budget": float(budget),
                        "message": f"{category} budget EXCEEDED at {percentage:.0%} ({spent}/{budget})"
                    })

        # Create alert files for warnings
        if warnings:
            self._create_budget_alerts(warnings, month)

        return warnings

    def _create_budget_alerts(self, warnings: List[Dict], month: str):
        """Create alert files in Needs_Action/ for budget warnings."""
        alerts_dir = self.vault_path / "Needs_Action"
        alerts_dir.mkdir(parents=True, exist_ok=True)

        for warning in warnings:
            category = warning["category"]
            level = warning["level"]
            message = warning["message"]

            # Create alert file
            alert_file = alerts_dir / f"BUDGET_ALERT_{month}_{category}_{level}.md"

            alert_content = f"""---
type: budget_alert
category: {category}
month: {month}
level: {level}
percentage: {warning['percentage']:.2f}
spent: {warning['spent']}
budget: {warning['budget']}
created_at: {datetime.now().isoformat()}
---

# ⚠️ Budget Alert: {category.title()}

{message}

## Details
- **Month**: {month}
- **Category**: {category}
- **Budget**: ${warning['budget']:.2f}
- **Spent**: ${warning['spent']:.2f}
- **Percentage**: {warning['percentage']:.0%}

## Action Required
{"Review and approve additional spending, or adjust budget for this category." if level == "warning" else "IMMEDIATE ATTENTION: Budget exceeded. Review expenses and take corrective action."}

## View in Odoo
[Open Odoo Budget Report]({self.odoo_url}/accounting/budget/{month})
"""

            with open(alert_file, 'w', encoding='utf-8') as f:
                f.write(alert_content)

            logger.warning(f"Created budget alert: {alert_file.name}")

    def _is_synced_to_odoo(self, expense_id: str) -> bool:
        """Check if expense has already been synced to Odoo."""
        sync_log = self.vault_path / "Logs" / "odoo_sync.jsonl"

        if not sync_log.exists():
            return False

        try:
            with open(sync_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("expense_id") == expense_id and entry.get("status") == "success":
                        return True
        except Exception as e:
            logger.debug(f"Error checking sync log: {e}")

        return False

    def _log_odoo_sync(self, expense_id: str, status: str, details: Dict):
        """Log Odoo sync event to odoo_sync.jsonl."""
        sync_log = self.vault_path / "Logs" / "odoo_sync.jsonl"
        sync_log.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "expense_id": expense_id,
            "status": status,
            "details": details
        }

        try:
            with open(sync_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to write sync log: {e}")


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

    service = ExpenseService(vault_path=vault_path)

    logger.info(f"ExpenseService initialized")
    logger.info(f"OCR Available: {EASYOCR_AVAILABLE}")
    logger.info(f"Vision API Available: {VISION_API_AVAILABLE}")
    logger.info(f"PDF Processing Available: {PDF2IMAGE_AVAILABLE}")


if __name__ == "__main__":
    main()
