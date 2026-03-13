#!/bin/bash

#######################################################################
# Secret Detection Validation Script
#######################################################################
#
# Validates that no secrets exist in the vault or codebase that could
# be accidentally synced to Cloud VM.
#
# Checks:
# - Git-tracked files for secrets using detect-secrets
# - .gitignore patterns for sensitive files
# - WhatsApp session files not present on Cloud
# - Banking credentials not in Cloud vault
# - OAuth tokens properly secured
# - Environment files not committed
#
# Usage:
#   ./validate-secrets.sh [path-to-vault]
#
# Exit codes:
#   0 - No secrets found, all checks passed
#   1 - Secrets detected or security issues found
#
# Created: 2026-03-14
# Part of: Platinum Tier Phase 9 - Security Validation
#######################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VAULT_PATH=${1:-"${VAULT_PATH:-.}"}
PASSED=0
FAILED=0
WARNINGS=0
SECRETS_FOUND=0

log_pass() {
    echo -e "${GREEN}✅ PASS${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}❌ FAIL${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO${NC} $1"
}

log_section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Check 1: detect-secrets scan
check_detect_secrets() {
    log_section "Check 1: Scanning for Secrets with detect-secrets"

    if ! command -v detect-secrets &> /dev/null; then
        log_fail "detect-secrets not installed (pip install detect-secrets)"
        return
    fi

    cd "$VAULT_PATH" || return

    # Run detect-secrets scan
    if detect-secrets scan --baseline .secrets.baseline 2>&1 | grep -q "ERROR"; then
        log_fail "detect-secrets scan found potential secrets"
        SECRETS_FOUND=1

        # Show detected secrets
        echo ""
        log_info "Detected secrets:"
        detect-secrets scan --baseline .secrets.baseline 2>&1 | grep -A 5 "Potential secrets"
    else
        log_pass "No secrets detected by detect-secrets"
    fi
}

# Check 2: .gitignore patterns
check_gitignore() {
    log_section "Check 2: Validating .gitignore Patterns"

    cd "$VAULT_PATH" || return

    if [ ! -f ".gitignore" ]; then
        log_fail ".gitignore file missing"
        return
    fi

    # Required patterns
    required_patterns=(
        ".env"
        ".env.local"
        ".env.cloud"
        "*.key"
        "*.pem"
        "*credentials*.json"
        ".whatsapp-session"
        "oauth-token*.json"
    )

    for pattern in "${required_patterns[@]}"; do
        if grep -q "^${pattern}$" .gitignore; then
            log_pass ".gitignore contains: $pattern"
        else
            log_warn ".gitignore missing pattern: $pattern"
            echo "  Add to .gitignore:"
            echo "  echo '$pattern' >> .gitignore"
        fi
    done
}

# Check 3: Environment files not committed
check_env_files() {
    log_section "Check 3: Environment Files Not Committed"

    cd "$VAULT_PATH" || return

    env_files=(
        ".env"
        ".env.local"
        ".env.cloud"
        ".env.production"
    )

    for env_file in "${env_files[@]}"; do
        if git ls-files --error-unmatch "$env_file" 2>/dev/null; then
            log_fail "$env_file is committed to Git (should be ignored!)"
            echo "  Fix: git rm --cached $env_file && git commit -m 'Remove $env_file from Git'"
        else
            log_pass "$env_file not in Git"
        fi
    done
}

# Check 4: WhatsApp sessions (Local only)
check_whatsapp_sessions() {
    log_section "Check 4: WhatsApp Sessions (Local Only)"

    cd "$VAULT_PATH" || return

    whatsapp_patterns=(
        ".whatsapp-session*"
        "**/whatsapp_session*"
        "**/wa-session*"
    )

    found_whatsapp=0

    for pattern in "${whatsapp_patterns[@]}"; do
        if find . -name "$pattern" -type f 2>/dev/null | grep -q .; then
            found_whatsapp=1

            # Check if in .gitignore
            if git check-ignore -q "$pattern" 2>/dev/null; then
                log_pass "WhatsApp sessions found but properly ignored"
            else
                log_fail "WhatsApp sessions found and NOT ignored by Git!"
                echo "  Files found:"
                find . -name "$pattern" -type f
                echo "  Fix: Add pattern to .gitignore"
            fi
        fi
    done

    if [ $found_whatsapp -eq 0 ]; then
        log_info "No WhatsApp sessions found (OK if using Cloud only)"
    fi
}

# Check 5: OAuth credentials
check_oauth_credentials() {
    log_section "Check 5: OAuth Credentials Security"

    cd "$VAULT_PATH" || return

    oauth_files=(
        "gmail-oauth.json"
        "*credentials*.json"
        "token*.json"
    )

    for pattern in "${oauth_files[@]}"; do
        files=$(find . -name "$pattern" -type f 2>/dev/null || true)

        if [ -n "$files" ]; then
            for file in $files; do
                # Check if tracked by Git
                if git ls-files --error-unmatch "$file" 2>/dev/null; then
                    log_fail "OAuth file tracked by Git: $file"
                    echo "  Fix: git rm --cached $file && add to .gitignore"
                    SECRETS_FOUND=1
                else
                    # Check if ignored
                    if git check-ignore -q "$file" 2>/dev/null; then
                        log_pass "OAuth file properly ignored: $file"
                    else
                        log_warn "OAuth file not tracked but not in .gitignore: $file"
                    fi
                fi

                # Check file permissions
                perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%Lp" "$file" 2>/dev/null)
                if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
                    log_pass "OAuth file has secure permissions: $file ($perms)"
                else
                    log_warn "OAuth file permissions not restrictive: $file ($perms)"
                    echo "  Fix: chmod 600 $file"
                fi
            done
        fi
    done
}

# Check 6: Banking/sensitive credentials
check_banking_credentials() {
    log_section "Check 6: Banking Credentials (Should Not Exist in Repo)"

    cd "$VAULT_PATH" || return

    # Patterns that should NEVER be in repo
    sensitive_patterns=(
        "bank*credentials*"
        "plaid*key*"
        "*api*secret*"
        "*private*key*.pem"
        "*.p12"
        "*.pfx"
    )

    for pattern in "${sensitive_patterns[@]}"; do
        files=$(find . -iname "$pattern" -type f 2>/dev/null || true)

        if [ -n "$files" ]; then
            for file in $files; do
                if git ls-files --error-unmatch "$file" 2>/dev/null; then
                    log_fail "CRITICAL: Sensitive file tracked by Git: $file"
                    echo "  This should NEVER be in Git!"
                    echo "  Fix: git rm --cached $file && add to .gitignore"
                    echo "  WARNING: File is in Git history - may need to purge"
                    SECRETS_FOUND=1
                else
                    log_warn "Sensitive file found (not tracked): $file"
                    echo "  Ensure it's in .gitignore"
                fi
            done
        fi
    done
}

# Check 7: Secrets in log files
check_log_files() {
    log_section "Check 7: Secrets in Log Files"

    cd "$VAULT_PATH" || return

    log_dir="Logs"

    if [ -d "$log_dir" ]; then
        # Check if logs directory is ignored
        if ! git check-ignore -q "$log_dir" 2>/dev/null; then
            log_warn "Logs directory not in .gitignore (may contain sensitive data)"
            echo "  Fix: echo 'Logs/*.log' >> .gitignore"
        else
            log_pass "Logs directory properly ignored"
        fi

        # Scan recent logs for common secret patterns
        if command -v detect-secrets &> /dev/null; then
            log_count=$(find "$log_dir" -name "*.jsonl" -o -name "*.log" | wc -l)
            if [ "$log_count" -gt 0 ]; then
                log_info "Scanning $log_count log files for secrets..."

                secret_patterns=(
                    "password"
                    "api[_-]?key"
                    "secret"
                    "token"
                    "credentials"
                )

                found_in_logs=0
                for pattern in "${secret_patterns[@]}"; do
                    if grep -riI "$pattern" "$log_dir" 2>/dev/null | grep -v "# pragma: allowlist secret" | grep -q .; then
                        found_in_logs=1
                    fi
                done

                if [ $found_in_logs -eq 1 ]; then
                    log_warn "Potential secrets found in log files (review manually)"
                else
                    log_pass "No obvious secrets in log files"
                fi
            fi
        fi
    else
        log_info "No Logs directory found"
    fi
}

# Check 8: Cloud VM specific validation
check_cloud_vault() {
    log_section "Check 8: Cloud VM Vault Validation"

    # Detect if running on Cloud VM
    if [ "${INSTANCE:-local}" = "cloud" ]; then
        log_info "Running on Cloud instance - performing Cloud-specific checks"

        # WhatsApp sessions should NEVER exist on Cloud
        if find . -name "*whatsapp*" -o -name "*wa-session*" 2>/dev/null | grep -q .; then
            log_fail "CRITICAL: WhatsApp sessions found on Cloud VM!"
            echo "  WhatsApp sessions should ONLY exist on Local instance"
            find . -name "*whatsapp*" -o -name "*wa-session*"
            SECRETS_FOUND=1
        else
            log_pass "No WhatsApp sessions on Cloud (correct)"
        fi

        # Banking credentials should NEVER exist on Cloud
        if find . -iname "*bank*" -o -iname "*plaid*" 2>/dev/null | grep -q .; then
            log_fail "CRITICAL: Banking credentials found on Cloud VM!"
            echo "  Banking credentials should ONLY exist on Local instance"
            SECRETS_FOUND=1
        else
            log_pass "No banking credentials on Cloud (correct)"
        fi
    else
        log_info "Running on Local instance - skipping Cloud-specific checks"
    fi
}

# Check 9: Git history scan (advanced)
check_git_history() {
    log_section "Check 9: Git History Scan (Advanced)"

    cd "$VAULT_PATH" || return

    if ! command -v git &> /dev/null; then
        log_warn "Git not available - skipping history scan"
        return
    fi

    # Check if repo has commits
    if ! git rev-parse HEAD &>/dev/null; then
        log_info "No Git history - skipping history scan"
        return
    fi

    log_info "Scanning Git history for secrets (this may take a moment)..."

    # Common secret patterns in Git history
    secret_patterns=(
        "password\\s*=\\s*['\"]"
        "api[_-]?key\\s*=\\s*['\"]"
        "secret\\s*=\\s*['\"]"
        "token\\s*=\\s*['\"]"
        "BEGIN.*PRIVATE KEY"
    )

    found_in_history=0
    for pattern in "${secret_patterns[@]}"; do
        if git log -p --all -G "$pattern" 2>/dev/null | grep -v "# pragma: allowlist secret" | grep -q "$pattern"; then
            found_in_history=1
            log_warn "Pattern '$pattern' found in Git history"
        fi
    done

    if [ $found_in_history -eq 1 ]; then
        log_warn "Potential secrets found in Git history (review with: git log -p)"
        echo "  Consider using BFG Repo-Cleaner to purge secrets: https://rtyley.github.io/bfg-repo-cleaner/"
    else
        log_pass "No obvious secrets in Git history"
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Secret Detection Validation Script                       ║"
    echo "║  Platinum Tier Security Validation                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Scanning vault: $VAULT_PATH"
    log_info "Instance: ${INSTANCE:-local}"
    echo ""

    # Run all checks
    check_detect_secrets
    check_gitignore
    check_env_files
    check_whatsapp_sessions
    check_oauth_credentials
    check_banking_credentials
    check_log_files
    check_cloud_vault
    check_git_history

    # Summary
    echo ""
    log_section "Validation Summary"
    echo ""
    echo "  Passed:   $PASSED"
    echo "  Failed:   $FAILED"
    echo "  Warnings: $WARNINGS"
    echo ""

    if [ $SECRETS_FOUND -eq 1 ]; then
        echo -e "${RED}🚨 CRITICAL: Secrets detected!${NC}"
        echo ""
        echo "Action required:"
        echo "  1. Remove secrets from Git-tracked files"
        echo "  2. Add sensitive files to .gitignore"
        echo "  3. Rotate any exposed credentials"
        echo "  4. Re-run this script to verify fixes"
        echo ""
        exit 1
    elif [ $FAILED -gt 0 ]; then
        echo -e "${RED}❌ Validation failed${NC}"
        echo ""
        echo "Please fix the issues above and re-run validation"
        echo ""
        exit 1
    elif [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Validation passed with warnings${NC}"
        echo ""
        echo "Review warnings above and address if applicable"
        echo ""
        exit 0
    else
        echo -e "${GREEN}✅ All checks passed!${NC}"
        echo ""
        echo "Vault is secure - no secrets detected"
        echo ""
        exit 0
    fi
}

# Run main
main
