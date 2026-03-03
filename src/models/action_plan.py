"""
ActionPlan Entity Model for Personal AI Employee - Bronze Tier MVP

Represents AI-generated task plans created by Claude Code.
Implements Entity 3 from data-model.md

Attributes:
    plan_id: Unique plan identifier (PLAN_001, PLAN_002, etc.)
    title: Brief plan title (3-10 words)
    source_type: Origin of plan ("email" or "file_drop")
    source_id: ID of source entity (email_id or FileDrop timestamp)
    created: Plan creation timestamp (ISO 8601)
    objective: 1-2 sentence goal (max 500 chars)
    steps: List of action steps (3-7 steps required)
    approval_required: HITL approval needed (true/false)
    approval_file: Path to approval request file (if needed)
    status: Execution status ("draft", "awaiting_approval", "complete")
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional
import yaml


@dataclass
class Step:
    """Individual step in an action plan."""
    step_number: int
    description: str
    completed: bool = False


@dataclass
class ActionPlan:
    """ActionPlan entity with YAML frontmatter serialization."""

    # Required attributes
    plan_id: str
    title: str
    source_type: Literal["email", "file_drop"]
    source_id: str
    created: datetime
    objective: str
    steps: List[Step]
    approval_required: bool = False
    approval_file: Optional[str] = None
    status: Literal["draft", "awaiting_approval", "complete"] = "draft"

    # Feedback UI elements (T128 - Phase 11)
    user_feedback: Optional[str] = None  # "approved", "rejected", "modified", "auto_approved"
    feedback_comment: Optional[str] = None
    execution_rating: Optional[int] = None  # 1-5 stars

    # Type identifier (constant)
    type: str = field(default="action_plan", init=False)

    def to_frontmatter(self) -> dict:
        """
        Convert ActionPlan to YAML frontmatter dictionary.

        Returns:
            dict: Frontmatter data ready for YAML serialization
        """
        result = {
            "plan_id": self.plan_id,
            "title": self.title,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "created": self.created.isoformat(),
            "objective": self.objective,
            "approval_required": self.approval_required,
            "approval_file": self.approval_file,
            "status": self.status,
        }

        # Include feedback if present (T128)
        if self.user_feedback:
            result["user_feedback"] = self.user_feedback
        if self.feedback_comment:
            result["feedback_comment"] = self.feedback_comment
        if self.execution_rating:
            result["execution_rating"] = self.execution_rating

        return result

    @classmethod
    def from_frontmatter(cls, frontmatter: dict, steps: List[Step]) -> "ActionPlan":
        """
        Create ActionPlan instance from YAML frontmatter dictionary.

        Args:
            frontmatter: Dictionary containing plan metadata
            steps: List of Step objects (parsed from markdown body)

        Returns:
            ActionPlan: ActionPlan instance
        """
        return cls(
            plan_id=frontmatter["plan_id"],
            title=frontmatter["title"],
            source_type=frontmatter["source_type"],
            source_id=frontmatter["source_id"],
            created=datetime.fromisoformat(frontmatter["created"]),
            objective=frontmatter["objective"],
            steps=steps,
            approval_required=frontmatter.get("approval_required", False),
            approval_file=frontmatter.get("approval_file"),
            status=frontmatter.get("status", "draft"),
            user_feedback=frontmatter.get("user_feedback"),
            feedback_comment=frontmatter.get("feedback_comment"),
            execution_rating=frontmatter.get("execution_rating"),
        )

    def to_markdown(self) -> str:
        """
        Generate complete Markdown file content with frontmatter and body.

        Format matches Contract 3 from contracts/file-interfaces.md

        Returns:
            str: Complete markdown file content
        """
        frontmatter_yaml = yaml.dump(
            self.to_frontmatter(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Generate steps section
        steps_section = "\n".join([
            f"- [ ] {step.step_number}. {step.description}"
            for step in self.steps
        ])

        # Generate approval section if needed
        approval_section = ""
        if self.approval_required and self.approval_file:
            approval_filename = self.approval_file.split('/')[-1]
            approval_section = f"""

## Approval Required

This plan involves sensitive actions that require your approval.

**Review approval request**: [{approval_filename}]({self.approval_file})

To approve: Move approval file to `/Approved/` folder (Silver tier feature)
"""

        markdown_content = f"""---
{frontmatter_yaml.strip()}
---

## Objective

{self.objective}

## Steps

{steps_section}
{approval_section}
"""
        return markdown_content

    def validate(self) -> bool:
        """
        Validate ActionPlan attributes according to data-model.md rules.

        Returns:
            bool: True if valid, raises ValueError if invalid
        """
        # Validate plan_id format (PLAN_XXX)
        if not self.plan_id.startswith("PLAN_"):
            raise ValueError(f"plan_id must start with 'PLAN_': {self.plan_id}")

        # Validate title length (3-10 words)
        word_count = len(self.title.split())
        if word_count < 3 or word_count > 10:
            raise ValueError(f"Title must be 3-10 words: {word_count} words")

        # Validate source_type
        if self.source_type not in ["email", "file_drop"]:
            raise ValueError(f"Invalid source_type: {self.source_type}")

        # Validate objective length (max 500 chars)
        if len(self.objective) > 500:
            raise ValueError(f"Objective exceeds 500 chars: {len(self.objective)}")

        # Validate steps count (3-7 steps per FR-014)
        if len(self.steps) < 3 or len(self.steps) > 7:
            raise ValueError(f"Steps must be 3-7 items: {len(self.steps)} steps")

        # Validate status
        if self.status not in ["draft", "awaiting_approval", "complete"]:
            raise ValueError(f"Invalid status: {self.status}")

        # If approval required, approval_file should be set
        if self.approval_required and not self.approval_file:
            raise ValueError("approval_file required when approval_required=True")

        return True

    def add_step(self, description: str) -> None:
        """
        Add a step to the plan.

        Args:
            description: Step description

        Raises:
            ValueError: If adding step would exceed max count (7)
        """
        if len(self.steps) >= 7:
            raise ValueError("Cannot add more than 7 steps")

        step_number = len(self.steps) + 1
        self.steps.append(Step(step_number=step_number, description=description))

    def complete_step(self, step_number: int) -> None:
        """
        Mark a step as completed.

        Args:
            step_number: Step number to complete (1-indexed)
        """
        for step in self.steps:
            if step.step_number == step_number:
                step.completed = True
                return

        raise ValueError(f"Step {step_number} not found")

    def is_complete(self) -> bool:
        """
        Check if all steps are completed.

        Returns:
            bool: True if all steps completed
        """
        return all(step.completed for step in self.steps)


def create_plan_filename(plan_id: str, title: str) -> str:
    """
    Generate standardized filename for ActionPlan file.

    Format: PLAN_{id}_{title_slug}.md

    Args:
        plan_id: Plan ID (e.g., "PLAN_001")
        title: Plan title

    Returns:
        str: Filename for plan markdown file
    """
    # Create title slug (lowercase, replace spaces with hyphens)
    title_slug = title.lower().replace(' ', '-')

    # Remove special characters
    import re
    title_slug = re.sub(r'[^a-z0-9\-]', '', title_slug)

    # Limit slug length to 50 chars
    title_slug = title_slug[:50].rstrip('-')

    return f"{plan_id}_{title_slug}.md"


def get_next_plan_id(existing_ids: List[str]) -> str:
    """
    Generate next sequential plan ID.

    Args:
        existing_ids: List of existing plan IDs (e.g., ["PLAN_001", "PLAN_002"])

    Returns:
        str: Next plan ID (e.g., "PLAN_003")
    """
    if not existing_ids:
        return "PLAN_001"

    # Extract numbers from existing IDs
    numbers = []
    for plan_id in existing_ids:
        if plan_id.startswith("PLAN_"):
            try:
                num = int(plan_id.split("_")[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue

    # Get max and increment
    max_num = max(numbers) if numbers else 0
    next_num = max_num + 1

    return f"PLAN_{next_num:03d}"
