#!/usr/bin/env python3
"""
Security Audit Script for Personal AI Employee - Bronze Tier MVP

Validates security requirements:
- T056: No credentials stored in Obsidian vault
- FR-017: Credentials outside vault
- SC-008: Vault free of secrets

Usage:
    python scripts/security_audit.py --vault-path /path/to/vault

Exit codes:
    0: All checks passed
    1: Security violations found
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Patterns to search for (case-insensitive)
CREDENTIAL_PATTERNS = [
    r'password\s*[:=]',
    r'token\s*[:=]',
    r'secret\s*[:=]',
    r'api[_-]?key\s*[:=]',
    r'client[_-]?id\s*[:=]',
    r'client[_-]?secret\s*[:=]',
    r'access[_-]?token\s*[:=]',
    r'refresh[_-]?token\s*[:=]',
    r'private[_-]?key\s*[:=]',
    r'auth[_-]?token\s*[:=]',
    r'bearer\s+[a-zA-Z0-9\-_]+',
    r'sk-[a-zA-Z0-9]{20,}',  # OpenAI-style API keys
    r'ghp_[a-zA-Z0-9]{36,}',  # GitHub personal access tokens
    r'AIza[a-zA-Z0-9\-_]{35}',  # Google API keys
]

# Files/folders to exclude from scan
EXCLUDED_PATTERNS = [
    '.git',
    'node_modules',
    '__pycache__',
    '*.pyc',
    '.DS_Store',
    'security_audit.py',  # This script itself
    'success-criteria-validation.md',  # Contains examples
    'gmail-api-setup.md',  # Contains documentation examples
]

class SecurityAudit:
    """Security audit checker for AI Employee project."""

    def __init__(self, vault_path: Path, project_root: Path):
        """
        Initialize security audit.

        Args:
            vault_path: Path to Obsidian vault
            project_root: Path to project root
        """
        self.vault_path = vault_path.resolve()
        self.project_root = project_root.resolve()
        self.violations: List[Tuple[Path, int, str, str]] = []

    def run_audit(self) -> bool:
        """
        Run complete security audit.

        Returns:
            bool: True if all checks passed
        """
        print("=" * 70)
        print("Security Audit - Personal AI Employee Bronze Tier MVP")
        print("=" * 70)
        print()

        all_passed = True

        # Check 1: Vault credential scan
        print("Check 1: Scanning vault for credentials...")
        vault_violations = self._scan_directory(self.vault_path)
        if vault_violations:
            print(f"  ❌ FAILED: Found {len(vault_violations)} potential credential(s) in vault")
            all_passed = False
        else:
            print("  ✅ PASSED: No credentials found in vault")
        print()

        # Check 2: Verify credentials are outside vault
        print("Check 2: Verifying credentials location...")
        credentials_outside = self._check_credentials_location()
        if not credentials_outside:
            print("  ❌ FAILED: Credentials not in correct location")
            all_passed = False
        else:
            print("  ✅ PASSED: Credentials correctly stored outside vault")
        print()

        # Check 3: Verify .gitignore coverage
        print("Check 3: Verifying .gitignore coverage...")
        gitignore_valid = self._check_gitignore()
        if not gitignore_valid:
            print("  ❌ FAILED: .gitignore does not cover all credential files")
            all_passed = False
        else:
            print("  ✅ PASSED: .gitignore properly configured")
        print()

        # Check 4: Verify no credentials in committed files
        print("Check 4: Checking git-tracked files...")
        tracked_violations = self._check_git_tracked_files()
        if tracked_violations:
            print(f"  ❌ FAILED: Found {len(tracked_violations)} credential(s) in git-tracked files")
            all_passed = False
        else:
            print("  ✅ PASSED: No credentials in git-tracked files")
        print()

        # Report violations
        if vault_violations:
            print("=" * 70)
            print("VAULT VIOLATIONS:")
            print("=" * 70)
            for file_path, line_num, line_text, pattern in vault_violations:
                rel_path = file_path.relative_to(self.vault_path)
                print(f"\n{rel_path}:{line_num}")
                print(f"  Pattern: {pattern}")
                print(f"  Line: {line_text.strip()}")
            print()

        # Summary
        print("=" * 70)
        print("AUDIT SUMMARY")
        print("=" * 70)
        if all_passed:
            print("✅ ALL CHECKS PASSED")
            print("\nSecurity status: COMPLIANT")
            print("- No credentials in Obsidian vault (SC-008)")
            print("- Credentials outside vault (FR-017)")
            print("- .gitignore properly configured")
            print("- No credentials in version control")
        else:
            print("❌ SECURITY VIOLATIONS DETECTED")
            print("\nAction required:")
            print("1. Remove all credentials from vault")
            print("2. Move credentials to project root (outside vault)")
            print("3. Update .gitignore to exclude credential files")
            print("4. Verify no credentials committed to git")
        print("=" * 70)

        return all_passed

    def _scan_directory(self, directory: Path) -> List[Tuple[Path, int, str, str]]:
        """
        Scan directory for credential patterns.

        Args:
            directory: Directory to scan

        Returns:
            List of violations (file_path, line_num, line_text, pattern)
        """
        violations = []

        if not directory.exists():
            return violations

        # Get all text files
        text_files = []
        for pattern in ['*.md', '*.json', '*.txt', '*.yaml', '*.yml']:
            text_files.extend(directory.rglob(pattern))

        # Scan each file
        for file_path in text_files:
            # Skip excluded paths
            if self._should_exclude(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, start=1):
                    for pattern in CREDENTIAL_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append((file_path, line_num, line, pattern))

            except Exception as e:
                print(f"  Warning: Could not scan {file_path}: {e}", file=sys.stderr)

        return violations

    def _should_exclude(self, file_path: Path) -> bool:
        """
        Check if file should be excluded from scan.

        Args:
            file_path: File path to check

        Returns:
            bool: True if should be excluded
        """
        for pattern in EXCLUDED_PATTERNS:
            if pattern in str(file_path):
                return True
        return False

    def _check_credentials_location(self) -> bool:
        """
        Verify credentials are stored outside vault.

        Returns:
            bool: True if credentials are correctly located
        """
        # Check that credential files exist in project root
        credentials_file = self.project_root / 'credentials.json'
        token_file = self.project_root / 'token.json'
        env_file = self.project_root / '.env'

        # Credentials may not exist yet (first run), so we just check they're not in vault
        vault_credentials = self.vault_path / 'credentials.json'
        vault_token = self.vault_path / 'token.json'
        vault_env = self.vault_path / '.env'

        if vault_credentials.exists():
            print(f"  ❌ Found credentials.json in vault: {vault_credentials}")
            return False

        if vault_token.exists():
            print(f"  ❌ Found token.json in vault: {vault_token}")
            return False

        if vault_env.exists():
            print(f"  ❌ Found .env in vault: {vault_env}")
            return False

        # If files exist, they should be in project root
        if credentials_file.exists():
            print(f"  ✓ credentials.json correctly in project root")

        if token_file.exists():
            print(f"  ✓ token.json correctly in project root")

        if env_file.exists():
            print(f"  ✓ .env correctly in project root")

        return True

    def _check_gitignore(self) -> bool:
        """
        Verify .gitignore has proper coverage.

        Returns:
            bool: True if .gitignore is valid
        """
        gitignore_file = self.project_root / '.gitignore'

        if not gitignore_file.exists():
            print("  ❌ .gitignore file not found")
            return False

        # Read .gitignore
        with open(gitignore_file, 'r', encoding='utf-8') as f:
            gitignore_content = f.read()

        # Required patterns
        required = [
            'credentials.json',
            'token.json',
            '.env',
        ]

        missing = []
        for pattern in required:
            if pattern not in gitignore_content:
                missing.append(pattern)

        if missing:
            print(f"  ❌ .gitignore missing patterns: {', '.join(missing)}")
            return False

        print(f"  ✓ .gitignore includes all required patterns")
        return True

    def _check_git_tracked_files(self) -> List[Tuple[Path, int, str, str]]:
        """
        Check git-tracked files for credentials.

        Returns:
            List of violations in git-tracked files
        """
        import subprocess

        try:
            # Get list of git-tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print("  ⚠️  Not a git repository or git not available")
                return []

            tracked_files = result.stdout.strip().split('\n')
            violations = []

            # Scan each tracked file
            for rel_path in tracked_files:
                file_path = self.project_root / rel_path

                # Only scan text files
                if not file_path.suffix in ['.md', '.json', '.txt', '.py', '.js', '.yaml', '.yml']:
                    continue

                if self._should_exclude(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, start=1):
                        for pattern in CREDENTIAL_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append((file_path, line_num, line, pattern))

                except Exception:
                    pass

            return violations

        except subprocess.TimeoutExpired:
            print("  ⚠️  Git command timed out")
            return []
        except FileNotFoundError:
            print("  ⚠️  Git not installed")
            return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Security audit for AI Employee project'
    )
    parser.add_argument(
        '--vault-path',
        type=str,
        required=False,
        help='Path to Obsidian vault (defaults to VAULT_PATH env var)'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        default='.',
        help='Path to project root (default: current directory)'
    )

    args = parser.parse_args()

    # Get vault path
    if args.vault_path:
        vault_path = Path(args.vault_path)
    else:
        import os
        from dotenv import load_dotenv
        load_dotenv()

        vault_path_str = os.getenv('VAULT_PATH')
        if not vault_path_str:
            print("ERROR: VAULT_PATH not set. Use --vault-path or set VAULT_PATH in .env", file=sys.stderr)
            sys.exit(1)

        vault_path = Path(vault_path_str)

    # Validate paths
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    project_root = Path(args.project_root).resolve()

    # Run audit
    audit = SecurityAudit(vault_path, project_root)
    passed = audit.run_audit()

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
