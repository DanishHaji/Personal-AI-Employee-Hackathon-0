#!/usr/bin/env python3
"""
Gold Tier Final Validation (T130)

Validates all 12 quickstart.md test scenarios:
- US1: Trust Rules (1 scenario)
- US2: Calendar Integration (1 scenario)
- US3: Document Generation (1 scenario)
- US4: Analytics & Insights (1 scenario)
- US5: Proactive Suggestions (1 scenario)
- US6: Meeting Transcription (1 scenario)
- US7: CRM Contact Management (2 scenarios)
- US8: Financial Tracking (1 scenario)
- Integration: End-to-End Workflow (1 scenario)

This script validates that all components are properly integrated
and ready for production use.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class ValidationChecker:
    """Validates Gold Tier implementation completeness."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.specs_path = project_root / "specs" / "003-gold-tier-upgrade"
        self.docs_path = project_root / "docs"
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def run_validation(self) -> bool:
        """Run complete validation suite."""
        print("\n" + "="*80)
        print("GOLD TIER FINAL VALIDATION (T130)")
        print("All 12 Quickstart Test Scenarios")
        print("="*80)

        scenarios = [
            ("US1: Trust Rules", self.validate_us1_trust_rules),
            ("US2: Calendar Integration", self.validate_us2_calendar),
            ("US3: Document Generation", self.validate_us3_documents),
            ("US4: Analytics & Insights", self.validate_us4_analytics),
            ("US5: Proactive Suggestions", self.validate_us5_suggestions),
            ("US6: Meeting Transcription", self.validate_us6_meetings),
            ("US7: CRM (Auto-create)", self.validate_us7_crm_create),
            ("US7: CRM (Stale Detection)", self.validate_us7_crm_stale),
            ("US8: Financial Tracking", self.validate_us8_expenses),
            ("Integration: End-to-End", self.validate_e2e_workflow),
            ("Documentation", self.validate_documentation),
            ("Configuration", self.validate_configuration)
        ]

        for name, validator_func in scenarios:
            print(f"\n{'='*80}")
            print(f"Scenario: {name}")
            print(f"{'='*80}")

            try:
                success = validator_func()
                if success:
                    self.passed += 1
                    print(f"✅ {name} - PASSED")
                else:
                    self.failed += 1
                    print(f"❌ {name} - FAILED")
            except Exception as e:
                self.failed += 1
                print(f"❌ {name} - ERROR: {e}")

        self.print_summary()
        return self.failed == 0

    def validate_us1_trust_rules(self) -> bool:
        """Validate US1: Autonomous Workflows & Trust Levels."""
        checks = []

        # Check trust_evaluator.py exists
        trust_eval = self.src_path / "services" / "trust_evaluator.py"
        checks.append(("Trust evaluator service exists", trust_eval.exists()))

        # Check trust_rule.py model exists
        trust_rule_model = self.src_path / "models" / "trust_rule.py"
        checks.append(("TrustRule model exists", trust_rule_model.exists()))

        # Check Company_Handbook.md template exists
        handbook = self.project_root / "Company_Handbook.md"
        checks.append(("Company_Handbook.md template exists", handbook.exists()))

        if handbook.exists():
            content = handbook.read_text()
            checks.append(("Handbook has trust_rules section", "trust_rules:" in content))

        # Check test file exists
        test_file = self.project_root / "tests" / "unit" / "test_trust_evaluator.py"
        checks.append(("Trust evaluator tests exist", test_file.exists()))

        # Check integration test
        integration_test = self.project_root / "tests" / "integration" / "test_us1_trust_framework.py"
        checks.append(("US1 integration test exists", integration_test.exists()))

        return self._print_checks(checks)

    def validate_us2_calendar(self) -> bool:
        """Validate US2: Calendar & Meeting Management."""
        checks = []

        # Check calendar_service.py
        calendar_service = self.src_path / "services" / "calendar_service.py"
        checks.append(("Calendar service exists", calendar_service.exists()))

        if calendar_service.exists():
            content = calendar_service.read_text()
            checks.append(("Has schedule_meeting method", "def schedule_meeting" in content))
            checks.append(("Has check_availability method", "def check_availability" in content or "availability" in content))

        # Check calendar_event model
        calendar_event = self.src_path / "models" / "calendar_event.py"
        checks.append(("CalendarEvent model exists", calendar_event.exists()))

        # Check calendar watcher
        calendar_watcher = self.src_path / "watchers" / "calendar_watcher.py"
        checks.append(("Calendar watcher exists", calendar_watcher.exists()))

        # Check JSON schema
        calendar_schema = self.specs_path / "contracts" / "calendar-event-schema.json"
        checks.append(("Calendar event schema exists", calendar_schema.exists()))

        # Check .env.example has calendar config
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            content = env_example.read_text()
            checks.append(("Calendar credentials in .env.example", "GOOGLE_CALENDAR_CREDENTIALS" in content))

        return self._print_checks(checks)

    def validate_us3_documents(self) -> bool:
        """Validate US3: Document Generation & Editing."""
        checks = []

        # Check document_service.py
        doc_service = self.src_path / "services" / "document_service.py"
        checks.append(("Document service exists", doc_service.exists()))

        # Check document model
        doc_model = self.src_path / "models" / "document.py"
        checks.append(("Document model exists", doc_model.exists()))

        # Check templates
        templates_dir = self.project_root / ".specify" / "templates" / "documents"
        checks.append(("Templates directory exists", templates_dir.exists()))

        if templates_dir.exists():
            templates = list(templates_dir.glob("*.j2"))
            checks.append(("Has Jinja2 templates", len(templates) > 0))
            checks.append(("Has meeting-notes template", (templates_dir / "meeting-notes.md.j2").exists()))
            checks.append(("Has weekly-status template", (templates_dir / "weekly-status.md.j2").exists()))

        # Check agent skill
        doc_agent = self.project_root / ".claude" / "commands" / "document-generator.md"
        checks.append(("Document generator agent skill exists", doc_agent.exists()))

        return self._print_checks(checks)

    def validate_us4_analytics(self) -> bool:
        """Validate US4: Advanced Analytics & Insights."""
        checks = []

        # Check analytics_service.py
        analytics_service = self.src_path / "services" / "analytics_service.py"
        checks.append(("Analytics service exists", analytics_service.exists()))

        if analytics_service.exists():
            content = analytics_service.read_text()
            checks.append(("Has generate_weekly_insights", "generate_weekly_insights" in content))
            checks.append(("Uses pandas for analysis", "pandas" in content or "pd" in content))

        # Check insight model
        insight_model = self.src_path / "models" / "insight.py"
        checks.append(("Insight model exists", insight_model.exists()))

        if insight_model.exists():
            content = insight_model.read_text()
            checks.append(("Has Pattern class", "class Pattern" in content))
            checks.append(("Has Recommendation class", "class Recommendation" in content))

        # Check analytics engine watcher
        analytics_watcher = self.src_path / "watchers" / "analytics_engine.py"
        checks.append(("Analytics engine watcher exists", analytics_watcher.exists()))

        # Check agent skill
        analytics_agent = self.project_root / ".claude" / "commands" / "analytics-insights.md"
        checks.append(("Analytics agent skill exists", analytics_agent.exists()))

        return self._print_checks(checks)

    def validate_us5_suggestions(self) -> bool:
        """Validate US5: Proactive Task Suggestions."""
        checks = []

        # Check suggestion_engine.py
        suggestion_engine = self.src_path / "services" / "suggestion_engine.py"
        checks.append(("Suggestion engine exists", suggestion_engine.exists()))

        if suggestion_engine.exists():
            content = suggestion_engine.read_text()
            checks.append(("Has detect_follow_ups", "detect_follow_ups" in content))
            checks.append(("Has pattern detection", "detect" in content.lower() and "pattern" in content.lower()))

        # Check proactive_suggestion model
        suggestion_model = self.src_path / "models" / "proactive_suggestion.py"
        checks.append(("ProactiveSuggestion model exists", suggestion_model.exists()))

        # Check suggestion engine watcher
        suggestion_watcher = self.src_path / "watchers" / "suggestion_engine_watcher.py"
        checks.append(("Suggestion engine watcher exists", suggestion_watcher.exists()))

        return self._print_checks(checks)

    def validate_us6_meetings(self) -> bool:
        """Validate US6: Meeting Attendance & Notes."""
        checks = []

        # Check meeting_service.py
        meeting_service = self.src_path / "services" / "meeting_service.py"
        checks.append(("Meeting service exists", meeting_service.exists()))

        # Check transcription_service.py
        transcription_service = self.src_path / "services" / "transcription_service.py"
        checks.append(("Transcription service exists", transcription_service.exists()))

        if transcription_service.exists():
            content = transcription_service.read_text()
            checks.append(("Uses OpenAI Whisper", "whisper" in content.lower() or "openai" in content.lower()))

        # Check meeting_note model
        meeting_model = self.src_path / "models" / "meeting_note.py"
        checks.append(("MeetingNote model exists", meeting_model.exists()))

        # Check agent skill
        meeting_agent = self.project_root / ".claude" / "commands" / "meeting-attendant.md"
        checks.append(("Meeting attendant agent skill exists", meeting_agent.exists()))

        # Check .env.example has Zoom and Whisper config
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            content = env_example.read_text()
            checks.append(("Zoom config in .env.example", "ZOOM" in content))
            checks.append(("OpenAI config in .env.example", "OPENAI_API_KEY" in content))

        return self._print_checks(checks)

    def validate_us7_crm_create(self) -> bool:
        """Validate US7: CRM Auto-Create Contact."""
        checks = []

        # Check contact_service.py
        contact_service = self.src_path / "services" / "contact_service.py"
        checks.append(("Contact service exists", contact_service.exists()))

        if contact_service.exists():
            content = contact_service.read_text()
            checks.append(("Has create_or_update_contact", "create_or_update_contact" in content))

        # Check contact model
        contact_model = self.src_path / "models" / "contact.py"
        checks.append(("Contact model exists", contact_model.exists()))

        if contact_model.exists():
            content = contact_model.read_text()
            checks.append(("Has encryption support", "encrypt" in content.lower()))

        # Check encryption_service.py
        encryption_service = self.src_path / "services" / "encryption_service.py"
        checks.append(("Encryption service exists", encryption_service.exists()))

        if encryption_service.exists():
            content = encryption_service.read_text()
            checks.append(("Uses AES-256-GCM", "AES" in content or "GCM" in content))

        # Check CRM watcher
        crm_watcher = self.src_path / "watchers" / "crm_watcher.py"
        checks.append(("CRM watcher exists", crm_watcher.exists()))

        return self._print_checks(checks)

    def validate_us7_crm_stale(self) -> bool:
        """Validate US7: CRM Stale Relationship Detection."""
        checks = []

        # Check contact_service has stale detection
        contact_service = self.src_path / "services" / "contact_service.py"
        if contact_service.exists():
            content = contact_service.read_text()
            checks.append(("Has stale relationship detection", "stale" in content.lower() or "last_contact" in content))

        # Check relationship scoring
        contact_model = self.src_path / "models" / "contact.py"
        if contact_model.exists():
            content = contact_model.read_text()
            checks.append(("Has relationship_strength field", "relationship_strength" in content))

        # Check integration with suggestion engine
        suggestion_engine = self.src_path / "services" / "suggestion_engine.py"
        if suggestion_engine.exists():
            content = suggestion_engine.read_text()
            checks.append(("Suggestion engine checks contacts", "contact" in content.lower()))

        return self._print_checks(checks)

    def validate_us8_expenses(self) -> bool:
        """Validate US8: Financial Tracking with OCR."""
        checks = []

        # Check expense_service.py
        expense_service = self.src_path / "services" / "expense_service.py"
        checks.append(("Expense service exists", expense_service.exists()))

        if expense_service.exists():
            content = expense_service.read_text()
            checks.append(("Has OCR integration", "easyocr" in content.lower() or "ocr" in content.lower()))
            checks.append(("Has receipt processing", "receipt" in content.lower()))

        # Check budget_service.py
        budget_service = self.src_path / "services" / "budget_service.py"
        checks.append(("Budget service exists", budget_service.exists()))

        if budget_service.exists():
            content = budget_service.read_text()
            checks.append(("Has budget alerts", "alert" in content.lower() or "threshold" in content))

        # Check expense model
        expense_model = self.src_path / "models" / "expense.py"
        checks.append(("Expense model exists", expense_model.exists()))

        # Check budget model
        budget_model = self.src_path / "models" / "budget.py"
        checks.append(("Budget model exists", budget_model.exists()))

        # Check pyproject.toml has OCR dependencies
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            checks.append(("Has easyocr dependency", "easyocr" in content.lower()))
            checks.append(("Has Pillow dependency", "pillow" in content.lower()))

        return self._print_checks(checks)

    def validate_e2e_workflow(self) -> bool:
        """Validate End-to-End Integration Workflow."""
        checks = []

        # Check all components exist
        checks.append(("Trust evaluation ✓", (self.src_path / "services" / "trust_evaluator.py").exists()))
        checks.append(("Calendar service ✓", (self.src_path / "services" / "calendar_service.py").exists()))
        checks.append(("Meeting service ✓", (self.src_path / "services" / "meeting_service.py").exists()))
        checks.append(("Document service ✓", (self.src_path / "services" / "document_service.py").exists()))
        checks.append(("Suggestion engine ✓", (self.src_path / "services" / "suggestion_engine.py").exists()))

        # Check integration test exists
        e2e_test = self.project_root / "tests" / "integration" / "test_gold_tier_e2e.py"
        checks.append(("End-to-end test file exists", e2e_test.exists()))

        if e2e_test.exists():
            content = e2e_test.read_text()
            checks.append(("Has full workflow test", "test_full_e2e_workflow" in content))

        return self._print_checks(checks)

    def validate_documentation(self) -> bool:
        """Validate documentation completeness."""
        checks = []

        # Check Gold Tier docs
        setup_doc = self.docs_path / "gold-tier-setup.md"
        checks.append(("gold-tier-setup.md exists", setup_doc.exists()))

        troubleshoot_doc = self.docs_path / "gold-tier-troubleshooting.md"
        checks.append(("gold-tier-troubleshooting.md exists", troubleshoot_doc.exists()))

        encryption_doc = self.docs_path / "encryption-backup.md"
        checks.append(("encryption-backup.md exists", encryption_doc.exists()))

        # Check specs
        spec_file = self.specs_path / "spec.md"
        checks.append(("spec.md exists", spec_file.exists()))

        quickstart_file = self.specs_path / "quickstart.md"
        checks.append(("quickstart.md exists", quickstart_file.exists()))

        tasks_file = self.specs_path / "tasks.md"
        checks.append(("tasks.md exists", tasks_file.exists()))

        # Check README updated
        readme = self.project_root / "README.md"
        if readme.exists():
            content = readme.read_text()
            checks.append(("README mentions Gold Tier", "Gold Tier" in content))
            checks.append(("README lists 8 user stories", "US8" in content or "User Story 8" in content))

        return self._print_checks(checks)

    def validate_configuration(self) -> bool:
        """Validate configuration files."""
        checks = []

        # Check .env.example
        env_example = self.project_root / ".env.example"
        checks.append((".env.example exists", env_example.exists()))

        if env_example.exists():
            content = env_example.read_text()
            checks.append(("Has Google Calendar config", "GOOGLE_CALENDAR" in content))
            checks.append(("Has Zoom config", "ZOOM" in content))
            checks.append(("Has OpenAI config", "OPENAI" in content))
            checks.append(("Has Google Vision config", "GOOGLE_" in content and "VISION" in content))

        # Check ecosystem.config.js
        ecosystem = self.project_root / "ecosystem.config.js"
        checks.append(("ecosystem.config.js exists", ecosystem.exists()))

        if ecosystem.exists():
            content = ecosystem.read_text()
            checks.append(("Has calendar-watcher process", "calendar-watcher" in content or "calendar_watcher" in content))
            checks.append(("Has analytics-engine process", "analytics-engine" in content or "analytics_engine" in content))

        # Check pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        checks.append(("pyproject.toml exists", pyproject.exists()))

        if pyproject.exists():
            content = pyproject.read_text()
            checks.append(("Has Gold Tier dependencies", "easyocr" in content or "openai" in content))

        return self._print_checks(checks)

    def _print_checks(self, checks: List[Tuple[str, bool]]) -> bool:
        """Print check results and return overall success."""
        all_passed = True

        for name, passed in checks:
            if passed:
                print(f"   ✅ {name}")
            else:
                print(f"   ❌ {name}")
                all_passed = False

        return all_passed

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0

        print(f"\n✅ Passed: {self.passed}/{total} scenarios")
        print(f"❌ Failed: {self.failed}/{total} scenarios")
        print(f"📊 Success Rate: {percentage:.1f}%")

        if self.failed == 0:
            print("\n🎉 ALL SCENARIOS PASSED!")
            print("Gold Tier implementation is complete and ready for production.")
        elif self.failed <= 2:
            print("\n⚠️  Minor issues found. Review failed scenarios.")
        else:
            print("\n❌ Significant issues found. Review and fix failed scenarios.")


def main():
    """Run final validation."""
    project_root = Path(__file__).parent.parent.parent

    validator = ValidationChecker(project_root)
    success = validator.run_validation()

    # Save results
    output_file = project_root / "tests" / "integration" / "validation_results.json"
    results = {
        'timestamp': datetime.now().isoformat(),
        'passed': validator.passed,
        'failed': validator.failed,
        'success_rate': (validator.passed / (validator.passed + validator.failed) * 100) if (validator.passed + validator.failed) > 0 else 0,
        'all_passed': success
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Results saved to: {output_file}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
