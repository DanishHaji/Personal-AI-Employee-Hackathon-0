# Expense Tracker Agent Skill

**Skill Name**: expense-tracker
**Tier**: Gold Tier - US8
**Description**: Automated expense tracking with OCR extraction from receipts

## Purpose

The Expense Tracker enables automated expense recording from receipt attachments, with OCR extraction, budget validation, and threshold alerts.

## Key Features

1. **OCR Extraction**: Extract amount, vendor, date, and category from receipt PDFs and images
2. **Auto-Categorization**: Keyword matching for 8 expense categories
3. **Budget Validation**: Check expenses against monthly category budgets
4. **Auto-Approval**: Recurring vendors and budget-compliant expenses approved automatically
5. **Unusual Detection**: Flag expenses 3x category average for review
6. **Threshold Alerts**: Alert when 80% of budget spent
7. **Receipt Detection**: Automatic processing from Gmail attachments
8. **Vision API Fallback**: Google Vision API for low OCR confidence (<0.75)

## Usage

### Process Receipt Manually

```python
from src.services.expense_service import ExpenseService

service = ExpenseService(vault_path="/path/to/vault")

expense = service.create_expense_from_receipt(
    receipt_path="/path/to/receipt.pdf",
    month="2026-03",
    auto_approve=True
)

print(f"Expense: {expense.vendor} - ${expense.amount} ({expense.approval_status.value})")
```

### OCR Text Extraction Only

```python
text, confidence = service.extract_text_from_receipt("/path/to/receipt.pdf")
print(f"Extracted text (confidence: {confidence:.1%})")
```

### Budget Management

```python
from src.services.budget_service import BudgetService
from src.models.expense import ExpenseCategory
from decimal import Decimal

budget_service = BudgetService(vault_path="/path/to/vault")

# Create/update budget
budget = budget_service.create_or_update_budget(
    category=ExpenseCategory.SOFTWARE,
    month="2026-03",
    monthly_limit=Decimal("500.00"),
    alert_threshold=0.80  # Alert at 80%
)

# Get budget report
report = budget_service.get_budget_report("2026-03")
print(f"Total spent: ${report['total_spent']} of ${report['total_budget']}")
```

### Automatic Gmail Receipt Processing

Expense Tracker integrates with Gmail Watcher to automatically:
1. Detect receipt emails (keywords: receipt, invoice, bill, payment)
2. Download PDF/image attachments to `/Receipts/`
3. Extract expense details with OCR
4. Validate against budgets
5. Create expense entity in `/Expenses/YYYY-MM/`
6. Update budget tracking
7. Send alerts if threshold reached

## Configuration

### Categories and Keywords

- **Software**: adobe, github, aws, cloud, subscription, saas, license
- **Travel**: flight, hotel, airbnb, uber, rental car, booking
- **Office**: staples, office depot, desk, chair, supplies
- **Marketing**: google ads, facebook ads, linkedin, advertising
- **Meals**: restaurant, cafe, coffee, lunch, dinner, food delivery
- **Transportation**: gas, fuel, parking, toll, transit, taxi
- **Utilities**: electric, gas, water, internet, phone
- **Other**: Fallback category

### Default Budgets

- Software: $500/month
- Travel: $1000/month
- Office: $200/month
- Marketing: $300/month
- Meals: $400/month
- Transportation: $250/month
- Utilities: $150/month
- Other: $200/month

### Alert Thresholds

- **Budget Alert**: 80% spending (configurable)
- **Overspent Alert**: Immediate when budget exceeded
- **Unusual Expense**: 3x category average
- **Low OCR Confidence**: <0.75 (triggers Vision API fallback)

## File Structure

**Expenses**: `/Expenses/YYYY-MM/EXPENSE_YYYY_MM_DD_NNN.md`
**Budgets**: `/Budgets/YYYY-MM.json` (all categories per month)
**Receipts**: `/Receipts/YYYY-MM-DD_HHMMSS_filename.{pdf|png|jpg}`
**Alerts**: `/Needs_Action/BUDGET_ALERT_{category}_{timestamp}.md`

## OCR Requirements

### EasyOCR (Default)

```bash
pip install easyocr
```

- Runs locally (no API costs)
- GPU optional (CPU mode available)
- English language support
- Average confidence: 0.70-0.90

### Google Vision API (Fallback)

```bash
pip install google-cloud-vision
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

- Triggered when EasyOCR confidence <0.75
- Higher accuracy (0.90-0.98)
- Requires Google Cloud account
- Costs: $1.50 per 1000 requests

## Workflow

1. **Receipt Email Arrives**
   - Gmail Watcher detects receipt keywords in subject/body
   - Downloads PDF/image attachment to `/Receipts/`

2. **OCR Extraction**
   - EasyOCR extracts text from receipt
   - Falls back to Vision API if confidence <0.75
   - Parses: amount, vendor, date, category

3. **Budget Validation**
   - Checks category budget for current month
   - Creates budget if missing (uses defaults)
   - Validates expense won't exceed limit

4. **Auto-Approval**
   - ✅ Recurring vendor (3+ past occurrences)
   - ✅ Within budget limits
   - ⚠️ Flag if unusual (3x average)
   - ❌ Manual review if budget would be exceeded

5. **Expense Creation**
   - Save expense entity to `/Expenses/YYYY-MM/`
   - Update budget JSON file
   - Send alert if threshold reached (80%)
   - Log to audit trail

## Success Metrics

- ✅ **SC-022**: OCR extraction >75% confidence
- ✅ **SC-023**: Budget alerts sent within 1 minute of threshold
- ✅ **SC-024**: Expense processing <30 seconds per receipt
- ✅ **SC-025**: Unusual expense detection >90% accuracy

## Example Expense Entity

```markdown
---
type: expense
expense_id: EXPENSE_2026_03_02_001
amount: 45.99
currency: USD
vendor: Adobe Creative Cloud
expense_date: 2026-03-02
category: software
receipt_file: /Receipts/2026-03-02_143522_adobe_receipt.pdf
budget_category_id: BUDGET_software_2026_03
ocr_confidence: 0.92
approval_status: approved
approved_by: auto_recurring
approved_at: 2026-03-02T14:35:30
flagged_for_review: false
created_at: 2026-03-02T14:35:25
---

# Expense: Adobe Creative Cloud
**Amount**: $45.99 | **Date**: 2026-03-02 | **Category**: Software

## Details
- **Vendor**: Adobe Creative Cloud
- **Description**: Monthly subscription - Creative Cloud All Apps
- **Receipt**: [View Receipt](/Receipts/2026-03-02_143522_adobe_receipt.pdf)

## Budget Tracking
- **Category**: Software
- **Monthly Budget**: $500.00
- **Current Spend**: $325.50 (65% used)
- **Remaining**: $174.50

## Approval
- **Status**: ✅ Approved
- **Approved By**: auto_recurring
- **Approved At**: 2026-03-02 02:35 PM

## OCR Extraction
- **Confidence**: 92.0%
```

## Troubleshooting

### Low OCR Accuracy

- Ensure receipt image is clear (not blurry)
- Check lighting and contrast
- Enable Vision API fallback
- Manually review flagged expenses

### Budget Not Found

- Run `budget_service.initialize_month_budgets(month)` to create defaults
- Or manually create budgets in Company_Handbook.md

### Receipt Not Detected

- Check Gmail Watcher is running: `pm2 logs gmail-watcher`
- Verify receipt keywords in subject/body
- Check attachment is PDF or image format

---

**Status**: ✅ Implemented (Phase 10)
**Last Updated**: 2026-03-02
**Dependencies**: EasyOCR, pdf2image, Google Vision API (optional)
