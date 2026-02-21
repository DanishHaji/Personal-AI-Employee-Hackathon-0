---
name: file-processor
description: Analyze dropped files and suggest appropriate processing actions
---

# File Processor Skill

This skill provides file-specific analysis to determine:
- File type and purpose
- Appropriate processing actions
- Where to file/archive
- Whether review is needed

This is a helper skill used by vault-manager when processing FileDrop entities.

## Usage

```
Use file-processor skill to analyze file contract.pdf (512KB, PDF document)
```

Or with full context:

```
Analyze file:
Name: Q4_Report_2025.xlsx
Type: Excel Spreadsheet
Size: 2.4 MB
Location: /Needs_Action/Q4_Report_2025_20260221_143022.xlsx
```

## Analysis Process

When invoked, this skill should:

1. **Identify File Type**:
   - **Documents**: .pdf, .doc, .docx, .txt
   - **Spreadsheets**: .xls, .xlsx, .csv
   - **Images**: .jpg, .jpeg, .png, .gif
   - **Archives**: .zip, .tar, .gz
   - **Code**: .py, .js, .java, .md
   - **Data**: .json, .xml, .sql

2. **Determine File Purpose**:
   Based on filename patterns:
   - **invoice_**: Billing/payment document
   - **contract_**: Legal agreement
   - **report_**: Analysis or summary document
   - **proposal_**: Business proposal
   - **receipt_**: Purchase confirmation
   - **screenshot_**: Visual documentation
   - **backup_**: Archived data

3. **Assess File Size**:
   - **Small** (< 1MB): Quick to process
   - **Medium** (1-10MB): Standard processing
   - **Large** (10-50MB): May need review before processing
   - **Very Large** (> 50MB): Flag for approval

4. **Suggest Processing Actions**:
   Based on file type and purpose, suggest steps:

   **For Documents (PDF, Word)**:
   1. Review document content
   2. Extract key information (dates, amounts, parties)
   3. Summarize main points
   4. Determine filing location (archive folder)
   5. Move to appropriate folder or /Done/

   **For Spreadsheets (Excel, CSV)**:
   1. Open and analyze data structure
   2. Identify key metrics or insights
   3. Check for required updates
   4. Update relevant records if needed
   5. Archive processed data

   **For Images**:
   1. Review image content
   2. Determine purpose (receipt, screenshot, photo)
   3. Add descriptive note if needed
   4. Archive or attach to related project

   **For Archives (ZIP)**:
   1. List archive contents
   2. Verify no unsafe files inside
   3. Extract if needed or archive as-is
   4. Document what's inside

5. **Detect Special Cases**:
   - **Invoices**: Extract vendor, amount, date → Track in accounting
   - **Contracts**: Extract parties, dates, terms → Store securely
   - **Reports**: Extract summary → Share with team
   - **Receipts**: Extract purchase details → Track expenses

## Example Output

```
File Analysis:
- File Type: PDF Document
- Purpose: Invoice (detected from filename)
- Size: 512 KB (standard)
- Urgency: Medium (invoice should be processed within 24h)
- Review Needed: Yes (financial document)

Suggested Action Steps:
1. Open and review invoice details
2. Extract vendor name, invoice number, amount
3. Verify charges against records
4. Check if payment exceeds $100 (requires approval)
5. Process payment or forward to accounting
6. Archive invoice in /Done/Invoices/

Metadata to Extract:
- Vendor: [Parse from PDF]
- Amount: [Parse from PDF]
- Invoice #: [Parse from PDF]
- Due Date: [Parse from PDF]
- Payment Status: Pending

Risk Factors:
- Financial document - requires careful review
- May need approval if amount >$100
```

## File Type Specific Processing

### PDF Documents
- **Invoices**: Extract vendor, amount, date → Approval if >$100 → Pay
- **Contracts**: Read terms → Extract key dates → Store securely
- **Reports**: Summarize → Share insights → Archive
- **Forms**: Fill if needed → Submit → Archive

### Excel/CSV Files
- **Data files**: Analyze structure → Extract insights → Update records
- **Reports**: Review charts → Summarize findings → Share
- **Budgets**: Verify calculations → Track expenses → Monitor
- **Lists**: Process items → Update database → Archive

### Images
- **Receipts**: Extract purchase details → Track expense → Archive
- **Screenshots**: Identify purpose → Annotate if needed → File
- **Photos**: Review content → Add context → Store
- **Diagrams**: Understand concept → Reference in notes → Keep

### Archives (ZIP, etc.)
- **Backups**: Verify contents → Store safely → Document
- **Deliveries**: Extract files → Process individually → Archive
- **Collections**: Catalog contents → Process as needed → Store

## Size-Based Handling

### Small Files (< 1MB)
- Process immediately
- Quick review sufficient
- Standard workflow

### Medium Files (1-10MB)
- Normal processing
- Thorough review
- May take longer

### Large Files (10-50MB)
- Flag for review
- Check why file is large
- Consider if compression needed
- Process when ready

### Very Large Files (> 50MB)
- **ALERT**: Flag for approval
- Verify file is expected
- Check storage capacity
- May need special handling

## Approval Detection

Suggest approval needed if file:
- Size > 50MB (large file alert per Company Handbook)
- Contains financial data (invoice, payment, receipt)
- Is a contract or legal document
- Requires signature or commitment
- Contains sensitive information

## Security Checks

Already handled by FilesystemWatcher quarantine, but verify:
- File extension matches content (e.g., .pdf is actually a PDF)
- No suspicious patterns in filename
- File source is known/trusted
- Content matches expected type

## Integration with vault-manager

This skill feeds into the vault-manager plan action to:
- Generate file-type-appropriate processing steps
- Suggest correct filing locations
- Determine if approval workflow needed
- Provide file-specific context

## Example Processing Plans

### Invoice PDF
```
1. Review invoice details (vendor, amount, date)
2. Verify against purchase order or records
3. Check if amount exceeds $100 (requires approval)
4. Get approval if needed
5. Process payment or forward to accounting
6. Archive in /Done/Invoices/[vendor]/
```

### Spreadsheet Report
```
1. Open and analyze spreadsheet structure
2. Review key metrics and charts
3. Extract summary insights
4. Update relevant records or databases
5. Share findings with team if needed
6. Archive in /Done/Reports/[month]/
```

### Contract Document
```
1. Read contract thoroughly
2. Extract key terms: parties, dates, obligations
3. Flag important dates (renewal, termination)
4. Store securely in /Done/Contracts/
5. Set reminders for key dates (Silver tier feature)
```

## Error Handling

- If file type is unknown: Suggest manual review as first step
- If file is corrupted: Note error and suggest re-requesting file
- If file is too large to process: Suggest splitting or compression
- If file contains unexpected content: Flag for human review
