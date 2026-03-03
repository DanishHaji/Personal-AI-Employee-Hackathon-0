"""
Insight Model - Gold Tier US4

Represents weekly analytics insights with metrics and recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from src.models.base_model import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Detected pattern in audit log data."""
    pattern_type: str  # day_of_week, time_of_day, anomaly, recurring, trend
    description: str
    confidence: float  # 0.0-1.0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "confidence": self.confidence,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pattern":
        """Create from dictionary."""
        return cls(
            pattern_type=data["pattern_type"],
            description=data["description"],
            confidence=data["confidence"],
            data=data.get("data", {})
        )


@dataclass
class Recommendation:
    """Actionable recommendation based on analysis."""
    priority: str  # high, medium, low
    category: str  # productivity, trust_rules, scheduling, budget, relationships
    recommendation: str
    rationale: str
    action_items: List[str] = field(default_factory=list)

    # Feedback UI elements (T128 - Phase 11)
    user_feedback: Optional[str] = None  # "helpful", "not_helpful", "implemented", "dismissed"
    feedback_comment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "priority": self.priority,
            "category": self.category,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "action_items": self.action_items
        }

        # Include feedback if present
        if self.user_feedback:
            result["user_feedback"] = self.user_feedback
        if self.feedback_comment:
            result["feedback_comment"] = self.feedback_comment

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recommendation":
        """Create from dictionary."""
        return cls(
            priority=data["priority"],
            category=data["category"],
            recommendation=data["recommendation"],
            rationale=data["rationale"],
            action_items=data.get("action_items", []),
            user_feedback=data.get("user_feedback"),
            feedback_comment=data.get("feedback_comment")
        )


@dataclass
class Anomaly:
    """Detected anomaly requiring attention."""
    anomaly_type: str
    severity: str  # low, medium, high
    description: str
    detected_value: float
    expected_value: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "detected_value": self.detected_value,
            "expected_value": self.expected_value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Anomaly":
        """Create from dictionary."""
        return cls(
            anomaly_type=data["anomaly_type"],
            severity=data["severity"],
            description=data["description"],
            detected_value=data["detected_value"],
            expected_value=data["expected_value"]
        )


@dataclass
class Insight(BaseModel):
    """
    Weekly analytics insight with metrics and recommendations.

    Attributes:
        insight_id: Unique identifier (INSIGHT_xxx format)
        week_start: Start of analysis period
        week_end: End of analysis period
        generated_at: Timestamp when insight was generated
        metrics: Calculated productivity metrics
        patterns: Detected patterns and anomalies
        recommendations: Actionable recommendations
        anomalies: Detected anomalies requiring attention
    """

    insight_id: str
    week_start: datetime
    week_end: datetime
    generated_at: datetime
    metrics: Dict[str, Any]
    patterns: List[Pattern] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    anomalies: List[Anomaly] = field(default_factory=list)

    def __post_init__(self):
        """Initialize and validate."""
        # Set type identifier
        object.__setattr__(self, 'type', 'insight')

        # Validate insight_id format
        if not self.insight_id.startswith('INSIGHT_'):
            raise ValueError("insight_id must start with 'INSIGHT_'")

        # Validate date range
        if self.week_end <= self.week_start:
            raise ValueError("week_end must be after week_start")

        # Convert dict patterns to Pattern objects if needed
        if self.patterns and isinstance(self.patterns[0], dict):
            object.__setattr__(
                self, 'patterns',
                [Pattern.from_dict(p) for p in self.patterns]
            )

        # Convert dict recommendations to Recommendation objects if needed
        if self.recommendations and isinstance(self.recommendations[0], dict):
            object.__setattr__(
                self, 'recommendations',
                [Recommendation.from_dict(r) for r in self.recommendations]
            )

        # Convert dict anomalies to Anomaly objects if needed
        if self.anomalies and isinstance(self.anomalies[0], dict):
            object.__setattr__(
                self, 'anomalies',
                [Anomaly.from_dict(a) for a in self.anomalies]
            )

    @classmethod
    def get_schema_name(cls) -> Optional[str]:
        """Return JSON Schema filename for validation."""
        return "insight-schema.json"

    def to_frontmatter(self, encrypt: bool = False) -> Dict[str, Any]:
        """
        Convert to YAML frontmatter dictionary.

        Args:
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Dict with insight data
        """
        data = super().to_frontmatter(encrypt=encrypt)

        # Convert datetime objects to ISO strings
        data["week_start"] = self.week_start.isoformat()
        data["week_end"] = self.week_end.isoformat()
        data["generated_at"] = self.generated_at.isoformat()

        # Convert nested objects to dicts
        data["patterns"] = [p.to_dict() for p in self.patterns]
        data["recommendations"] = [r.to_dict() for r in self.recommendations]
        data["anomalies"] = [a.to_dict() for a in self.anomalies]

        return data

    @classmethod
    def from_frontmatter(cls, data: Dict[str, Any]) -> "Insight":
        """
        Create Insight from frontmatter dictionary.

        Args:
            data: Dictionary from YAML frontmatter or JSON

        Returns:
            Insight instance
        """
        # Parse datetime strings
        if isinstance(data.get("week_start"), str):
            data["week_start"] = datetime.fromisoformat(data["week_start"].replace('Z', '+00:00'))
        if isinstance(data.get("week_end"), str):
            data["week_end"] = datetime.fromisoformat(data["week_end"].replace('Z', '+00:00'))
        if isinstance(data.get("generated_at"), str):
            data["generated_at"] = datetime.fromisoformat(data["generated_at"].replace('Z', '+00:00'))

        # Parse nested objects
        if data.get("patterns"):
            data["patterns"] = [Pattern.from_dict(p) for p in data["patterns"]]
        if data.get("recommendations"):
            data["recommendations"] = [Recommendation.from_dict(r) for r in data["recommendations"]]
        if data.get("anomalies"):
            data["anomalies"] = [Anomaly.from_dict(a) for a in data["anomalies"]]

        # Remove BaseModel fields before creating instance
        data.pop("ENCRYPTED_FIELDS", None)
        data.pop("type", None)

        return cls(**data)

    def get_high_priority_recommendations(self) -> List[Recommendation]:
        """Get only high-priority recommendations."""
        return [r for r in self.recommendations if r.priority == "high"]

    def get_anomalies_by_severity(self, severity: str) -> List[Anomaly]:
        """Get anomalies filtered by severity level."""
        return [a for a in self.anomalies if a.severity == severity]

    def to_json(self, encrypt: bool = False) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dictionary.

        Args:
            encrypt: Whether to encrypt sensitive fields

        Returns:
            Dict ready for JSON serialization
        """
        return self.to_frontmatter(encrypt=encrypt)
