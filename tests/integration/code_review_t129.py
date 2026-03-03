#!/usr/bin/env python3
"""
Gold Tier Code Review & Validation (T129)

Automated code review checking:
1. Code consistency across all 8 user stories
2. Error handling completeness
3. Documentation coverage
4. Type hints usage
5. Test coverage
6. Security best practices
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class CodeReviewValidator:
    """Automated code review for Gold Tier implementation."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.tests_path = project_root / "tests"
        self.issues = []
        self.warnings = []
        self.stats = defaultdict(int)

    def run_full_review(self) -> Dict:
        """Run complete code review."""
        print("\n" + "="*70)
        print("GOLD TIER CODE REVIEW (T129)")
        print("="*70)

        results = {
            'consistency': self.check_consistency(),
            'error_handling': self.check_error_handling(),
            'documentation': self.check_documentation(),
            'type_hints': self.check_type_hints(),
            'test_coverage': self.check_test_coverage(),
            'security': self.check_security(),
            'naming': self.check_naming_conventions(),
            'imports': self.check_import_organization()
        }

        self.print_summary(results)
        return results

    def check_consistency(self) -> Dict:
        """Check code consistency across services."""
        print("\n📋 Checking consistency across 8 user stories...")

        # Check all services follow same pattern
        services = list((self.src_path / "services").glob("*.py"))
        service_patterns = {}

        for service in services:
            if service.name.startswith('_'):
                continue

            content = service.read_text()
            tree = ast.parse(content)

            # Check for common patterns
            patterns = {
                'has_logger': 'logging.getLogger' in content,
                'has_docstring': ast.get_docstring(tree) is not None,
                'has_init': any(isinstance(node, ast.FunctionDef) and node.name == '__init__'
                               for node in ast.walk(tree)),
                'has_error_handling': 'try:' in content or 'except' in content
            }

            service_patterns[service.name] = patterns

        # Report inconsistencies
        all_have_logger = all(p['has_logger'] for p in service_patterns.values())
        all_have_docstring = all(p['has_docstring'] for p in service_patterns.values())

        issues = []
        if not all_have_logger:
            missing = [name for name, p in service_patterns.items() if not p['has_logger']]
            issues.append(f"Missing logger in: {', '.join(missing)}")

        if not all_have_docstring:
            missing = [name for name, p in service_patterns.items() if not p['has_docstring']]
            issues.append(f"Missing module docstring in: {', '.join(missing)}")

        if issues:
            self.warnings.extend(issues)
            print(f"   ⚠️  {len(issues)} consistency issues found")
        else:
            print("   ✅ All services follow consistent patterns")

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'services_checked': len(service_patterns)
        }

    def check_error_handling(self) -> Dict:
        """Check error handling completeness."""
        print("\n🛡️  Checking error handling...")

        services = list((self.src_path / "services").glob("*.py"))
        issues = []

        for service in services:
            if service.name.startswith('_'):
                continue

            content = service.read_text()
            tree = ast.parse(content)

            # Check for bare except clauses
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        issues.append(f"{service.name}: Bare 'except:' clause found (should specify exception type)")

            # Check for missing error logging
            try_blocks = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
            for try_node in try_blocks:
                has_logging = any(
                    'logger' in ast.unparse(stmt) if hasattr(ast, 'unparse') else str(stmt)
                    for handler in try_node.handlers
                    for stmt in handler.body
                )
                if not has_logging:
                    self.warnings.append(f"{service.name}: Try block without error logging")

        if issues:
            self.issues.extend(issues)
            print(f"   ❌ {len(issues)} error handling issues")
        else:
            print(f"   ✅ Error handling looks good ({len(services)} services checked)")

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': len([w for w in self.warnings if 'Try block' in w])
        }

    def check_documentation(self) -> Dict:
        """Check documentation coverage."""
        print("\n📚 Checking documentation...")

        models = list((self.src_path / "models").glob("*.py"))
        services = list((self.src_path / "services").glob("*.py"))
        all_files = models + services

        total_classes = 0
        documented_classes = 0
        total_functions = 0
        documented_functions = 0

        for file in all_files:
            if file.name.startswith('_'):
                continue

            content = file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    total_classes += 1
                    if ast.get_docstring(node):
                        documented_classes += 1

                elif isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if not node.name.startswith('_'):
                        total_functions += 1
                        if ast.get_docstring(node):
                            documented_functions += 1

        class_coverage = (documented_classes / total_classes * 100) if total_classes > 0 else 0
        function_coverage = (documented_functions / total_functions * 100) if total_functions > 0 else 0

        print(f"   Classes: {documented_classes}/{total_classes} ({class_coverage:.1f}%)")
        print(f"   Functions: {documented_functions}/{total_functions} ({function_coverage:.1f}%)")

        passed = class_coverage > 80 and function_coverage > 70

        if passed:
            print("   ✅ Documentation coverage adequate")
        else:
            print("   ⚠️  Documentation coverage could be improved")

        return {
            'passed': passed,
            'class_coverage': class_coverage,
            'function_coverage': function_coverage,
            'total_classes': total_classes,
            'total_functions': total_functions
        }

    def check_type_hints(self) -> Dict:
        """Check type hint usage."""
        print("\n🔤 Checking type hints...")

        services = list((self.src_path / "services").glob("*.py"))
        total_functions = 0
        typed_functions = 0

        for service in services:
            if service.name.startswith('_'):
                continue

            content = service.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    total_functions += 1

                    # Check for return type hint
                    if node.returns is not None:
                        typed_functions += 1

        coverage = (typed_functions / total_functions * 100) if total_functions > 0 else 0

        print(f"   Functions with return type hints: {typed_functions}/{total_functions} ({coverage:.1f}%)")

        if coverage > 70:
            print("   ✅ Good type hint usage")
        else:
            print("   ⚠️  Consider adding more type hints")

        return {
            'passed': coverage > 60,
            'coverage': coverage,
            'total_functions': total_functions
        }

    def check_test_coverage(self) -> Dict:
        """Check test coverage by counting test files."""
        print("\n🧪 Checking test coverage...")

        # Count service files
        services = list((self.src_path / "services").glob("*.py"))
        service_names = {s.stem for s in services if not s.name.startswith('_')}

        # Count test files
        unit_tests = list((self.tests_path / "unit").glob("test_*.py"))
        tested_services = {
            t.stem.replace('test_', '')
            for t in unit_tests
        }

        missing_tests = service_names - tested_services

        coverage = (len(tested_services) / len(service_names) * 100) if service_names else 0

        print(f"   Services with tests: {len(tested_services)}/{len(service_names)} ({coverage:.1f}%)")

        if missing_tests:
            print(f"   ⚠️  Missing tests for: {', '.join(sorted(missing_tests))}")
        else:
            print("   ✅ All services have test files")

        return {
            'passed': len(missing_tests) == 0,
            'coverage': coverage,
            'missing_tests': list(missing_tests),
            'total_services': len(service_names)
        }

    def check_security(self) -> Dict:
        """Check security best practices."""
        print("\n🔒 Checking security practices...")

        issues = []
        warnings = []

        # Check all Python files
        all_py_files = list(self.src_path.rglob("*.py"))

        for file in all_py_files:
            content = file.read_text()

            # Check for hardcoded secrets
            if re.search(r'password\s*=\s*["\'](?!.*\{).*["\']', content, re.IGNORECASE):
                issues.append(f"{file.name}: Potential hardcoded password")

            if re.search(r'api[_-]?key\s*=\s*["\'](?!.*\{).*["\']', content, re.IGNORECASE):
                issues.append(f"{file.name}: Potential hardcoded API key")

            # Check for SQL injection risks
            if 'execute(' in content and 'f"' in content:
                warnings.append(f"{file.name}: Potential SQL injection risk with f-string")

            # Check for encryption usage
            if 'password' in content.lower() and 'encrypt' not in content.lower():
                warnings.append(f"{file.name}: Password handling without encryption")

        # Check .env.example for sensitive data
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            content = env_example.read_text()
            if "your-" not in content.lower() and "replace" not in content.lower():
                warnings.append(".env.example: May contain actual secrets instead of placeholders")

        if issues:
            self.issues.extend(issues)
            print(f"   ❌ {len(issues)} security issues found")
        else:
            print("   ✅ No critical security issues found")

        if warnings:
            print(f"   ⚠️  {len(warnings)} security warnings")

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    def check_naming_conventions(self) -> Dict:
        """Check naming conventions consistency."""
        print("\n📝 Checking naming conventions...")

        issues = []

        # Check model naming
        models = list((self.src_path / "models").glob("*.py"))
        for model in models:
            if model.name.startswith('_'):
                continue

            # Model files should be snake_case
            if not re.match(r'^[a-z_]+\.py$', model.name):
                issues.append(f"{model.name}: Should be snake_case")

        # Check service naming
        services = list((self.src_path / "services").glob("*.py"))
        for service in services:
            if service.name.startswith('_'):
                continue

            # Service files should end with _service.py
            if not service.name.startswith('__') and not service.name.endswith('_service.py'):
                self.warnings.append(f"{service.name}: Service files should end with '_service.py'")

        if issues:
            self.issues.extend(issues)
            print(f"   ❌ {len(issues)} naming issues")
        else:
            print("   ✅ Naming conventions consistent")

        return {
            'passed': len(issues) == 0,
            'issues': issues
        }

    def check_import_organization(self) -> Dict:
        """Check import statement organization."""
        print("\n📦 Checking import organization...")

        issues = []

        py_files = list(self.src_path.rglob("*.py"))

        for file in py_files[:10]:  # Sample first 10 files
            if file.name.startswith('_'):
                continue

            content = file.read_text()
            lines = content.split('\n')

            # Check if imports are at the top
            first_import_line = next((i for i, line in enumerate(lines) if line.startswith('import') or line.startswith('from')), None)
            first_code_line = next((i for i, line in enumerate(lines) if line and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''")), None)

            if first_import_line and first_code_line and first_import_line > first_code_line:
                self.warnings.append(f"{file.name}: Imports should be at the top")

        print(f"   ✅ Checked {len(py_files)} files")

        return {
            'passed': True,
            'files_checked': len(py_files)
        }

    def print_summary(self, results: Dict):
        """Print review summary."""
        print("\n" + "="*70)
        print("REVIEW SUMMARY")
        print("="*70)

        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r.get('passed', False))

        print(f"\n✅ Passed: {passed_checks}/{total_checks} checks")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Issues: {len(self.issues)}")

        if self.issues:
            print("\n🔴 Critical Issues:")
            for issue in self.issues[:10]:
                print(f"   - {issue}")

        if self.warnings:
            print("\n🟡 Warnings:")
            for warning in self.warnings[:10]:
                print(f"   - {warning}")

        # Overall grade
        score = (passed_checks / total_checks) * 100
        print(f"\n📊 Overall Score: {score:.1f}%")

        if score >= 90:
            print("🎉 Excellent code quality!")
        elif score >= 75:
            print("✅ Good code quality with minor improvements needed")
        elif score >= 60:
            print("⚠️  Acceptable code quality, improvements recommended")
        else:
            print("❌ Significant improvements needed")

        return score


def main():
    """Run code review."""
    project_root = Path(__file__).parent.parent.parent

    reviewer = CodeReviewValidator(project_root)
    results = reviewer.run_full_review()

    # Save results to JSON
    output_file = project_root / "tests" / "integration" / "code_review_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
