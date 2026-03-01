"""
Analytics Service - Gold Tier US4

Analyzes audit logs to generate weekly insights with metrics, patterns, and recommendations.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

import pandas as pd
import numpy as np

from src.models.insight import Insight, Pattern, Recommendation, Anomaly
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for analyzing audit logs and generating insights.

    Features:
    - Load audit logs into pandas DataFrames
    - Calculate productivity metrics
    - Detect patterns and anomalies
    - Analyze trust rule effectiveness
    - Generate actionable recommendations
    """

    def __init__(self, vault_path: str):
        """
        Initialize AnalyticsService.

        Args:
            vault_path: Path to Obsidian vault
        """
        self.vault_path = Path(vault_path)
        self.audit_service = AuditService(vault_path=vault_path)
        self.insights_dir = self.vault_path / "Insights"
        self.insights_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AnalyticsService initialized with vault_path={vault_path}")

    def load_audit_logs_df(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Load audit logs into a pandas DataFrame.

        Args:
            start_time: Start of time period
            end_time: End of time period

        Returns:
            DataFrame with audit log data
        """
        # Query audit logs
        logs = self.audit_service.query_logs(
            start_date=start_time,
            end_date=end_time
        )

        if not logs:
            logger.warning(f"No audit logs found between {start_time} and {end_time}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(logs)

        # Parse timestamp column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
            df['day_name'] = df['timestamp'].dt.day_name()

        logger.info(f"Loaded {len(df)} audit log entries into DataFrame")
        return df

    def calculate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate productivity metrics from audit log DataFrame.

        Args:
            df: DataFrame with audit log data

        Returns:
            Dict with calculated metrics
        """
        if df.empty:
            return {
                "total_actions": 0,
                "actions_per_day": 0,
                "email_volume": {"sent": 0, "received": 0},
                "meeting_stats": {
                    "total_meetings": 0,
                    "total_hours": 0,
                    "avg_duration_minutes": 0
                },
                "response_times": {"avg_seconds": 0, "median_seconds": 0},
                "trust_effectiveness": {
                    "auto_approved_count": 0,
                    "manual_review_count": 0,
                    "avg_effectiveness_score": 0
                }
            }

        metrics = {}

        # Total actions
        metrics["total_actions"] = len(df)

        # Actions per day
        if 'date' in df.columns:
            unique_days = df['date'].nunique()
            metrics["actions_per_day"] = round(len(df) / max(unique_days, 1), 2)
        else:
            metrics["actions_per_day"] = 0

        # Email volume
        email_sent = len(df[df['action'] == 'email_send']) if 'action' in df.columns else 0
        email_received = len(df[df['action'] == 'email_receive']) if 'action' in df.columns else 0
        metrics["email_volume"] = {
            "sent": email_sent,
            "received": email_received
        }

        # Meeting stats
        if 'action' in df.columns:
            meeting_df = df[df['action'].str.contains('meeting|calendar', case=False, na=False)]
            total_meetings = len(meeting_df)

            # Calculate total hours from execution_time if available
            total_hours = 0
            if 'execution_time' in meeting_df.columns:
                total_hours = meeting_df['execution_time'].sum() / 3600  # Convert to hours

            avg_duration = 0
            if total_meetings > 0 and 'execution_time' in meeting_df.columns:
                avg_duration = (meeting_df['execution_time'].mean() / 60)  # Convert to minutes

            metrics["meeting_stats"] = {
                "total_meetings": total_meetings,
                "total_hours": round(total_hours, 2),
                "avg_duration_minutes": round(avg_duration, 2)
            }
        else:
            metrics["meeting_stats"] = {
                "total_meetings": 0,
                "total_hours": 0,
                "avg_duration_minutes": 0
            }

        # Response times (for email responses)
        if 'execution_time' in df.columns:
            response_times = df['execution_time'].dropna()
            if len(response_times) > 0:
                metrics["response_times"] = {
                    "avg_seconds": round(response_times.mean(), 2),
                    "median_seconds": round(response_times.median(), 2)
                }
            else:
                metrics["response_times"] = {"avg_seconds": 0, "median_seconds": 0}
        else:
            metrics["response_times"] = {"avg_seconds": 0, "median_seconds": 0}

        # Trust effectiveness
        if 'action' in df.columns:
            trust_actions = df[df['action'].str.contains('trust|approval', case=False, na=False)]
            auto_approved = len(trust_actions[trust_actions['outcome'] == 'auto_approved']) if 'outcome' in trust_actions.columns else 0
            manual_review = len(trust_actions[trust_actions['outcome'] == 'manual_review']) if 'outcome' in trust_actions.columns else 0

            # Calculate average effectiveness score from metadata
            effectiveness_scores = []
            for _, row in trust_actions.iterrows():
                if 'metadata' in row and isinstance(row['metadata'], dict):
                    score = row['metadata'].get('effectiveness_score')
                    if score is not None:
                        effectiveness_scores.append(score)

            avg_effectiveness = np.mean(effectiveness_scores) if effectiveness_scores else 0

            metrics["trust_effectiveness"] = {
                "auto_approved_count": auto_approved,
                "manual_review_count": manual_review,
                "avg_effectiveness_score": round(avg_effectiveness, 3)
            }
        else:
            metrics["trust_effectiveness"] = {
                "auto_approved_count": 0,
                "manual_review_count": 0,
                "avg_effectiveness_score": 0
            }

        logger.info(f"Calculated metrics: {metrics}")
        return metrics

    def detect_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect patterns in audit log data.

        Args:
            df: DataFrame with audit log data

        Returns:
            List of detected patterns
        """
        patterns = []

        if df.empty:
            return patterns

        # Day-of-week pattern detection
        if 'day_name' in df.columns and 'day_of_week' in df.columns:
            day_counts = df['day_name'].value_counts().to_dict()

            # Find peak days (above average + 0.5 * std)
            counts = list(day_counts.values())
            if counts:
                avg_count = np.mean(counts)
                std_count = np.std(counts)
                threshold = avg_count + 0.5 * std_count

                peak_days = {day: count for day, count in day_counts.items() if count > threshold}

                if peak_days:
                    peak_day_names = ", ".join(sorted(peak_days.keys(), key=lambda x: peak_days[x], reverse=True)[:2])
                    patterns.append(Pattern(
                        pattern_type="day_of_week",
                        description=f"Peak activity on {peak_day_names}",
                        confidence=0.8,
                        data=day_counts
                    ))

        # Time-of-day pattern detection
        if 'hour' in df.columns:
            hour_counts = df['hour'].value_counts().to_dict()

            # Find peak hours
            if hour_counts:
                sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
                peak_hour = sorted_hours[0][0]

                # Determine time period
                if 6 <= peak_hour < 12:
                    period = "morning (6am-12pm)"
                elif 12 <= peak_hour < 18:
                    period = "afternoon (12pm-6pm)"
                elif 18 <= peak_hour < 22:
                    period = "evening (6pm-10pm)"
                else:
                    period = "night (10pm-6am)"

                patterns.append(Pattern(
                    pattern_type="time_of_day",
                    description=f"Peak activity during {period}",
                    confidence=0.75,
                    data={"peak_hour": peak_hour, "hour_distribution": hour_counts}
                ))

        # Recurring pattern detection (same action type multiple times)
        if 'action' in df.columns:
            action_counts = df['action'].value_counts()
            recurring_actions = action_counts[action_counts >= 5].to_dict()

            if recurring_actions:
                for action, count in list(recurring_actions.items())[:3]:  # Top 3
                    patterns.append(Pattern(
                        pattern_type="recurring",
                        description=f"Recurring {action} actions ({count} times)",
                        confidence=0.85,
                        data={"action": action, "count": count}
                    ))

        logger.info(f"Detected {len(patterns)} patterns")
        return patterns

    def detect_anomalies(self, df: pd.DataFrame, metrics: Dict[str, Any]) -> List[Anomaly]:
        """
        Detect anomalies using 3-sigma detection.

        Args:
            df: DataFrame with audit log data
            metrics: Calculated metrics

        Returns:
            List of detected anomalies
        """
        anomalies = []

        if df.empty:
            return anomalies

        # Anomaly: Unusually high action volume
        actions_per_day = metrics.get("actions_per_day", 0)
        if actions_per_day > 0 and 'date' in df.columns:
            daily_counts = df.groupby('date').size()
            mean_daily = daily_counts.mean()
            std_daily = daily_counts.std()

            if std_daily > 0:
                # Check for days exceeding 3 sigma
                threshold = mean_daily + 3 * std_daily
                high_days = daily_counts[daily_counts > threshold]

                if len(high_days) > 0:
                    for date, count in high_days.items():
                        anomalies.append(Anomaly(
                            anomaly_type="high_activity",
                            severity="medium",
                            description=f"Unusually high activity on {date}",
                            detected_value=float(count),
                            expected_value=float(mean_daily)
                        ))

        # Anomaly: Very low trust effectiveness
        trust_eff = metrics.get("trust_effectiveness", {}).get("avg_effectiveness_score", 0)
        if trust_eff > 0 and trust_eff < 0.7:
            anomalies.append(Anomaly(
                anomaly_type="low_trust_effectiveness",
                severity="high",
                description="Trust rule effectiveness below threshold",
                detected_value=trust_eff,
                expected_value=0.85
            ))

        # Anomaly: Unusually long response times
        avg_response = metrics.get("response_times", {}).get("avg_seconds", 0)
        if avg_response > 7200:  # More than 2 hours
            anomalies.append(Anomaly(
                anomaly_type="slow_responses",
                severity="medium",
                description="Response times higher than expected",
                detected_value=avg_response,
                expected_value=3600  # 1 hour
            ))

        logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies

    def analyze_trust_effectiveness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze trust rule effectiveness from audit logs.

        Args:
            df: DataFrame with audit log data

        Returns:
            Dict with trust rule analysis
        """
        analysis = {
            "rules_analyzed": 0,
            "high_performing_rules": [],
            "low_performing_rules": [],
            "suggestions": []
        }

        if df.empty or 'metadata' not in df.columns:
            return analysis

        # Extract trust evaluation actions
        trust_actions = df[df['action'].str.contains('trust_evaluation', case=False, na=False)]

        if trust_actions.empty:
            return analysis

        # Group by rule_id and calculate effectiveness
        rule_stats = {}
        for _, row in trust_actions.iterrows():
            if isinstance(row.get('metadata'), dict):
                rule_id = row['metadata'].get('rule_id')
                effectiveness = row['metadata'].get('effectiveness_score')

                if rule_id and effectiveness is not None:
                    if rule_id not in rule_stats:
                        rule_stats[rule_id] = []
                    rule_stats[rule_id].append(effectiveness)

        analysis["rules_analyzed"] = len(rule_stats)

        # Identify high and low performing rules
        for rule_id, scores in rule_stats.items():
            avg_score = np.mean(scores)
            usage_count = len(scores)

            if avg_score >= 0.95 and usage_count >= 10:
                analysis["high_performing_rules"].append({
                    "rule_id": rule_id,
                    "avg_effectiveness": round(avg_score, 3),
                    "usage_count": usage_count
                })
            elif avg_score < 0.75:
                analysis["low_performing_rules"].append({
                    "rule_id": rule_id,
                    "avg_effectiveness": round(avg_score, 3),
                    "usage_count": usage_count
                })

        logger.info(f"Analyzed {analysis['rules_analyzed']} trust rules")
        return analysis

    def generate_recommendations(
        self,
        metrics: Dict[str, Any],
        patterns: List[Pattern],
        anomalies: List[Anomaly],
        trust_analysis: Dict[str, Any]
    ) -> List[Recommendation]:
        """
        Generate actionable recommendations based on analysis.

        Args:
            metrics: Calculated metrics
            patterns: Detected patterns
            anomalies: Detected anomalies
            trust_analysis: Trust rule effectiveness analysis

        Returns:
            List of recommendations
        """
        recommendations = []

        # Trust rule recommendations
        if trust_analysis.get("high_performing_rules"):
            for rule in trust_analysis["high_performing_rules"][:2]:  # Top 2
                recommendations.append(Recommendation(
                    priority="high",
                    category="trust_rules",
                    recommendation=f"Consider increasing trust level for {rule['rule_id']}",
                    rationale=f"{rule['avg_effectiveness']*100:.1f}% effectiveness over {rule['usage_count']} actions with no rejections",
                    action_items=[
                        f"Review {rule['rule_id']} configuration",
                        "Consider upgrading trust level for silent auto-approval"
                    ]
                ))

        if trust_analysis.get("low_performing_rules"):
            for rule in trust_analysis["low_performing_rules"][:2]:
                recommendations.append(Recommendation(
                    priority="high",
                    category="trust_rules",
                    recommendation=f"Review or disable {rule['rule_id']}",
                    rationale=f"Low effectiveness score ({rule['avg_effectiveness']*100:.1f}%) suggests rule needs refinement",
                    action_items=[
                        f"Review {rule['rule_id']} conditions",
                        "Consider adding more specific filters or disabling"
                    ]
                ))

        # Productivity recommendations
        actions_per_day = metrics.get("actions_per_day", 0)
        if actions_per_day > 50:
            recommendations.append(Recommendation(
                priority="medium",
                category="productivity",
                recommendation="Consider batching similar tasks for efficiency",
                rationale=f"High action volume ({actions_per_day:.1f} actions/day) may benefit from task batching",
                action_items=[
                    "Identify repetitive action patterns",
                    "Create automation workflows for common tasks"
                ]
            ))

        # Scheduling recommendations based on patterns
        for pattern in patterns:
            if pattern.pattern_type == "day_of_week":
                recommendations.append(Recommendation(
                    priority="low",
                    category="scheduling",
                    recommendation="Optimize meeting scheduling based on activity patterns",
                    rationale=pattern.description,
                    action_items=[
                        "Schedule important meetings on peak activity days",
                        "Reserve low-activity days for deep work"
                    ]
                ))

        # Anomaly-based recommendations
        for anomaly in anomalies:
            if anomaly.severity == "high":
                priority = "high"
            elif anomaly.severity == "medium":
                priority = "medium"
            else:
                priority = "low"

            if anomaly.anomaly_type == "low_trust_effectiveness":
                recommendations.append(Recommendation(
                    priority=priority,
                    category="trust_rules",
                    recommendation="Review trust framework configuration",
                    rationale=anomaly.description,
                    action_items=[
                        "Audit recent trust evaluations",
                        "Refine trust rule conditions"
                    ]
                ))

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations

    def generate_weekly_insight(
        self,
        week_start: Optional[datetime] = None
    ) -> Tuple[Insight, Path]:
        """
        Generate a weekly insight from audit logs.

        Args:
            week_start: Start of week (default: last Monday)

        Returns:
            Tuple of (Insight, file_path)
        """
        # Default to last Monday if not specified
        if week_start is None:
            today = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
            week_start = today - timedelta(days=today.weekday())

        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        logger.info(f"Generating weekly insight for {week_start} to {week_end}")

        # Load audit logs
        df = self.load_audit_logs_df(week_start, week_end)

        # Calculate metrics
        metrics = self.calculate_metrics(df)

        # Detect patterns and anomalies
        patterns = self.detect_patterns(df)
        anomalies = self.detect_anomalies(df, metrics)

        # Analyze trust effectiveness
        trust_analysis = self.analyze_trust_effectiveness(df)

        # Generate recommendations
        recommendations = self.generate_recommendations(
            metrics, patterns, anomalies, trust_analysis
        )

        # Create Insight
        insight_id = f"INSIGHT_{week_start.strftime('%Y_%m_%d')}"
        generated_at = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)

        insight = Insight(
            insight_id=insight_id,
            week_start=week_start,
            week_end=week_end,
            generated_at=generated_at,
            metrics=metrics,
            patterns=patterns,
            recommendations=recommendations,
            anomalies=anomalies
        )

        # Save to file
        file_path = self._save_insight(insight)

        logger.info(f"Generated weekly insight: {file_path}")
        return insight, file_path

    def _save_insight(self, insight: Insight) -> Path:
        """
        Save insight to JSON file.

        Args:
            insight: Insight to save

        Returns:
            Path to saved file
        """
        # Create filename
        filename = f"{insight.week_start.strftime('%Y-%m-%d')}.json"
        file_path = self.insights_dir / filename

        # Convert to JSON
        data = insight.to_json()

        # Write file
        file_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

        logger.info(f"Saved insight to {file_path}")
        return file_path
