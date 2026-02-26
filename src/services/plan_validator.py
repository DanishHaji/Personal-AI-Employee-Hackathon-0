#!/usr/bin/env python3
"""
Plan Validator - JSON Schema Validation for Silver Tier

Validates approved plans against JSON schemas before execution to ensure data integrity
and prevent execution errors. Supports email plans, social media posts, scheduled tasks,
and execution logs.

Uses jsonschema library for standardized validation with clear error messages.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
except ImportError:
    raise ImportError(
        "jsonschema library is required. Install with: uv pip install jsonschema"
    )


logger = logging.getLogger(__name__)


class PlanType(Enum):
    """Supported plan types with corresponding schemas."""
    EMAIL_SEND = "email_send"
    SOCIAL_POST = "social_media_post"
    SCHEDULED_TASK = "scheduled_task"
    EXECUTION_LOG = "execution_log"


# Schema file paths (relative to project root)
SCHEMA_PATHS = {
    PlanType.EMAIL_SEND: "specs/002-silver-tier-upgrade/contracts/email-plan-schema.json",
    PlanType.SOCIAL_POST: "specs/002-silver-tier-upgrade/contracts/social-post-plan-schema.json",
    PlanType.SCHEDULED_TASK: "specs/002-silver-tier-upgrade/contracts/scheduled-task-schema.json",
    PlanType.EXECUTION_LOG: "specs/002-silver-tier-upgrade/contracts/execution-log-schema.json",
}


@dataclass
class ValidationResult:
    """Result of plan validation."""
    valid: bool
    errors: List[str]
    plan_type: Optional[PlanType] = None

    @property
    def error_message(self) -> str:
        """Get formatted error message."""
        if not self.errors:
            return ""
        return "; ".join(self.errors)


class PlanValidator:
    """
    Validates plans against JSON schemas before execution.

    Loads schemas from contracts/ directory and validates plan data structures
    to ensure they meet requirements before execution via MCP servers.

    Usage:
        validator = PlanValidator()

        # Validate email plan
        result = validator.validate_email_plan({
            "type": "email_send",
            "action": "send",
            "recipient": "user@example.com",
            "subject": "Test",
            "body": "Hello"
        })

        if result.valid:
            print("Plan is valid")
        else:
            print(f"Validation errors: {result.error_message}")
    """

    def __init__(self, schema_base_path: Optional[Path] = None):
        """
        Initialize plan validator.

        Args:
            schema_base_path: Base path for schema files (default: current working directory)
        """
        self.schema_base_path = schema_base_path or Path.cwd()
        self.schemas: Dict[PlanType, Dict] = {}

        # Load all schemas
        self._load_schemas()

        logger.info(f"PlanValidator initialized with {len(self.schemas)} schemas")

    def _load_schemas(self):
        """Load JSON schemas from contract files."""
        for plan_type, schema_path in SCHEMA_PATHS.items():
            full_path = self.schema_base_path / schema_path

            try:
                if not full_path.exists():
                    logger.warning(
                        f"Schema file not found: {full_path} - skipping {plan_type.value}"
                    )
                    continue

                with open(full_path, 'r') as f:
                    schema = json.load(f)

                # Validate the schema itself
                Draft7Validator.check_schema(schema)

                self.schemas[plan_type] = schema
                logger.debug(f"Loaded schema for {plan_type.value} from {schema_path}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse schema {schema_path}: {e}")

            except jsonschema.exceptions.SchemaError as e:
                logger.error(f"Invalid schema {schema_path}: {e}")

            except Exception as e:
                logger.error(f"Error loading schema {schema_path}: {e}")

    def _validate_against_schema(
        self,
        plan_data: Dict[str, Any],
        plan_type: PlanType
    ) -> ValidationResult:
        """
        Validate plan data against schema.

        Args:
            plan_data: Plan data to validate
            plan_type: Type of plan

        Returns:
            ValidationResult with validation status and errors
        """
        # Check if schema is loaded
        if plan_type not in self.schemas:
            return ValidationResult(
                valid=False,
                errors=[f"Schema not loaded for {plan_type.value}"],
                plan_type=plan_type
            )

        schema = self.schemas[plan_type]
        errors = []

        try:
            # Validate against schema
            validate(instance=plan_data, schema=schema)

            return ValidationResult(
                valid=True,
                errors=[],
                plan_type=plan_type
            )

        except ValidationError as e:
            # Extract clear error messages
            error_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            error_msg = f"{error_path}: {e.message}"
            errors.append(error_msg)

            # Add schema path if available
            if e.schema_path:
                schema_path = " -> ".join(str(p) for p in e.schema_path)
                logger.debug(f"Schema path: {schema_path}")

            return ValidationResult(
                valid=False,
                errors=errors,
                plan_type=plan_type
            )

        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Unexpected validation error: {str(e)}"],
                plan_type=plan_type
            )

    def validate_email_plan(self, plan_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate email send plan.

        Args:
            plan_data: Email plan data with fields (type, action, recipient, subject, body, ...)

        Returns:
            ValidationResult
        """
        return self._validate_against_schema(plan_data, PlanType.EMAIL_SEND)

    def validate_social_post(self, plan_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate social media post plan.

        Args:
            plan_data: Social post data with fields (type, post_id, platforms, content, ...)

        Returns:
            ValidationResult
        """
        return self._validate_against_schema(plan_data, PlanType.SOCIAL_POST)

    def validate_scheduled_task(self, plan_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate scheduled task definition.

        Args:
            plan_data: Scheduled task data with fields (task_id, task_name, schedule_pattern, ...)

        Returns:
            ValidationResult
        """
        return self._validate_against_schema(plan_data, PlanType.SCHEDULED_TASK)

    def validate_execution_log(self, log_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate execution log entry.

        Args:
            log_data: Execution log data with fields (log_id, timestamp, action_type, ...)

        Returns:
            ValidationResult
        """
        return self._validate_against_schema(log_data, PlanType.EXECUTION_LOG)

    def validate_plan(self, plan_data: Dict[str, Any]) -> ValidationResult:
        """
        Auto-detect plan type and validate.

        Uses 'type' field in plan_data to determine plan type.

        Args:
            plan_data: Plan data with 'type' field

        Returns:
            ValidationResult
        """
        # Detect plan type from 'type' field
        if 'type' not in plan_data:
            return ValidationResult(
                valid=False,
                errors=["Missing 'type' field in plan data"]
            )

        plan_type_str = plan_data['type']

        # Map type string to PlanType enum
        type_mapping = {
            "email_send": PlanType.EMAIL_SEND,
            "social_media_post": PlanType.SOCIAL_POST,
            "scheduled_task": PlanType.SCHEDULED_TASK,
            "execution_log": PlanType.EXECUTION_LOG,
        }

        if plan_type_str not in type_mapping:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown plan type: {plan_type_str}"]
            )

        plan_type = type_mapping[plan_type_str]

        # Validate against appropriate schema
        return self._validate_against_schema(plan_data, plan_type)

    def get_loaded_schemas(self) -> List[str]:
        """
        Get list of successfully loaded schema types.

        Returns:
            List of plan type names
        """
        return [plan_type.value for plan_type in self.schemas.keys()]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Initialize validator
    validator = PlanValidator()

    # Example: Validate email plan
    print("\n=== Email Plan Validation ===")
    email_plan = {
        "type": "email_send",
        "action": "send",
        "recipient": "user@example.com",
        "subject": "Test Email",
        "body": "This is a test email from the AI Employee."
    }

    result = validator.validate_email_plan(email_plan)
    print(f"Valid: {result.valid}")
    if not result.valid:
        print(f"Errors: {result.error_message}")

    # Example: Validate social post with missing required field
    print("\n=== Social Post Validation (Invalid) ===")
    social_post = {
        "type": "social_media_post",
        "platforms": ["linkedin"],
        # Missing required fields: post_id, content, status
    }

    result = validator.validate_social_post(social_post)
    print(f"Valid: {result.valid}")
    if not result.valid:
        print(f"Errors: {result.error_message}")

    # Example: Auto-detect and validate
    print("\n=== Auto-Detect Validation ===")
    result = validator.validate_plan(email_plan)
    print(f"Detected type: {result.plan_type.value if result.plan_type else 'unknown'}")
    print(f"Valid: {result.valid}")

    # Show loaded schemas
    print("\n=== Loaded Schemas ===")
    print(f"Schemas: {', '.join(validator.get_loaded_schemas())}")
