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

from src.models.expense import Expense, ExpenseCategory, save_expense
from src.models.budget import BudgetFile
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


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
        vision_api_threshold: float = 0.75
    ):
        """
        Initialize ExpenseService.

        Args:
            vault_path: Path to Obsidian vault
            use_vision_api: Whether to use Google Vision API for low confidence OCR
            vision_api_threshold: OCR confidence threshold to trigger Vision API fallback
        """
        self.vault_path = Path(vault_path)
        self.use_vision_api = use_vision_api and VISION_API_AVAILABLE
        self.vision_api_threshold = vision_api_threshold

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

        logger.info(f"ExpenseService initialized (OCR: {EASYOCR_AVAILABLE}, Vision API: {self.use_vision_api})")

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
