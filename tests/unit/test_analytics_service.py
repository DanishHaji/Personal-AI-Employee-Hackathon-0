"""
Unit tests for AnalyticsService - Gold Tier US4

Tests metrics calculation, pattern detection, and recommendation generation.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import json
from unittest.mock import Mock, patch

import pandas as pd
import numpy as np

from src.models.insight import Insight, Pattern, Recommendation, Anomaly
from src.services.analytics_service import AnalyticsService


class TestInsightModel:
    """Test Insight model creation and validation."""

    def test_create_insight(self):
        """Test creating a valid insight."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        insight = Insight(
            insight_id="INSIGHT_2026_03_01",
            week_start=now,
            week_end=now + timedelta(days=7),
            generated_at=now,
            metrics={"total_actions": 100},
            patterns=[],
            recommendations=[],
            anomalies=[]
        )

        assert insight.insight_id == "INSIGHT_2026_03_01"
        assert insight.type == "insight"
        assert insight.metrics["total_actions"] == 100

    def test_insight_validation_invalid_id(self):
        """Test insight creation with invalid ID."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        with pytest.raises(ValueError, match="must start with 'INSIGHT_'"):
            Insight(
                insight_id="INVALID_001",
                week_start=now,
                week_end=now + timedelta(days=7),
                generated_at=now,
                metrics={}
            )

    def test_insight_validation_invalid_date_range(self):
        """Test insight creation with invalid date range."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        with pytest.raises(ValueError, match="week_end must be after week_start"):
            Insight(
                insight_id="INSIGHT_2026_03_01",
                week_start=now,
                week_end=now - timedelta(days=1),
                generated_at=now,
                metrics={}
            )

    def test_get_high_priority_recommendations(self):
        """Test filtering high-priority recommendations."""
        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        insight = Insight(
            insight_id="INSIGHT_2026_03_01",
            week_start=now,
            week_end=now + timedelta(days=7),
            generated_at=now,
            metrics={},
            recommendations=[
                Recommendation("high", "trust_rules", "Upgrade rule", "Good performance"),
                Recommendation("medium", "productivity", "Optimize", "Can improve"),
                Recommendation("high", "scheduling", "Adjust", "Better timing")
            ]
        )

        high_priority = insight.get_high_priority_recommendations()
        assert len(high_priority) == 2
        assert all(r.priority == "high" for r in high_priority)


class TestAnalyticsService:
    """Test AnalyticsService functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        temp_dir = tempfile.mkdtemp()
        # Create Logs directory with test data
        logs_dir = Path(temp_dir) / "Logs"
        logs_dir.mkdir()

        # Create test audit log - one JSON object per line (JSONL format)
        today = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        log_data = []

        for i in range(7):
            for j in range(3):
                log_entry = {
                    "timestamp": (today - timedelta(days=i, hours=j)).isoformat(),
                    "action": "email_send" if i % 2 == 0 else "calendar_event",
                    "outcome": "success",
                    "execution_time": 0.5 + (i * 0.1),
                    "metadata": {
                        "rule_id": "RULE_test",
                        "effectiveness_score": 0.9 + (i * 0.01)
                    }
                }
                log_data.append(log_entry)

        # Write as JSON Lines format (one JSON object per line)
        log_file = logs_dir / f"{today.strftime('%Y-%m-%d')}.json"
        log_lines = "\n".join([json.dumps(entry) for entry in log_data])
        log_file.write_text(log_lines)

        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_service_initialization(self, temp_vault):
        """Test AnalyticsService initialization."""
        service = AnalyticsService(vault_path=temp_vault)

        assert service.vault_path == Path(temp_vault)
        assert service.insights_dir.exists()

    def test_load_audit_logs_df(self, temp_vault):
        """Test loading audit logs into DataFrame."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        df = service.load_audit_logs_df(
            start_time=now - timedelta(days=8),
            end_time=now
        )

        assert not df.empty
        assert 'timestamp' in df.columns
        assert 'action' in df.columns
        assert 'day_of_week' in df.columns
        assert 'hour' in df.columns

    def test_calculate_metrics_basic(self, temp_vault):
        """Test basic metrics calculation."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        df = service.load_audit_logs_df(
            start_time=now - timedelta(days=8),
            end_time=now
        )

        metrics = service.calculate_metrics(df)

        assert "total_actions" in metrics
        assert "actions_per_day" in metrics
        assert "email_volume" in metrics
        assert "meeting_stats" in metrics
        assert "response_times" in metrics
        assert "trust_effectiveness" in metrics

        assert metrics["total_actions"] > 0
        assert metrics["actions_per_day"] > 0

    def test_calculate_metrics_empty_df(self, temp_vault):
        """Test metrics calculation with empty DataFrame."""
        service = AnalyticsService(vault_path=temp_vault)

        df = pd.DataFrame()
        metrics = service.calculate_metrics(df)

        assert metrics["total_actions"] == 0
        assert metrics["actions_per_day"] == 0
        assert metrics["email_volume"]["sent"] == 0
        assert metrics["email_volume"]["received"] == 0

    def test_detect_patterns(self, temp_vault):
        """Test pattern detection."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        df = service.load_audit_logs_df(
            start_time=now - timedelta(days=8),
            end_time=now
        )

        patterns = service.detect_patterns(df)

        assert isinstance(patterns, list)
        # Should detect at least day-of-week or time-of-day patterns
        if len(patterns) > 0:
            assert all(isinstance(p, Pattern) for p in patterns)
            assert all(hasattr(p, 'pattern_type') for p in patterns)
            assert all(hasattr(p, 'confidence') for p in patterns)

    def test_detect_anomalies(self, temp_vault):
        """Test anomaly detection."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        df = service.load_audit_logs_df(
            start_time=now - timedelta(days=8),
            end_time=now
        )

        metrics = service.calculate_metrics(df)
        anomalies = service.detect_anomalies(df, metrics)

        assert isinstance(anomalies, list)
        if len(anomalies) > 0:
            assert all(isinstance(a, Anomaly) for a in anomalies)
            assert all(hasattr(a, 'severity') for a in anomalies)

    def test_analyze_trust_effectiveness(self, temp_vault):
        """Test trust rule effectiveness analysis."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        df = service.load_audit_logs_df(
            start_time=now - timedelta(days=8),
            end_time=now
        )

        analysis = service.analyze_trust_effectiveness(df)

        assert "rules_analyzed" in analysis
        assert "high_performing_rules" in analysis
        assert "low_performing_rules" in analysis
        assert "suggestions" in analysis

    def test_generate_recommendations(self, temp_vault):
        """Test recommendation generation."""
        service = AnalyticsService(vault_path=temp_vault)

        metrics = {
            "total_actions": 100,
            "actions_per_day": 50,
            "trust_effectiveness": {
                "avg_effectiveness_score": 0.92
            }
        }

        patterns = [
            Pattern(
                pattern_type="day_of_week",
                description="Peak on Tuesday",
                confidence=0.85,
                data={}
            )
        ]

        anomalies = [
            Anomaly(
                anomaly_type="high_activity",
                severity="medium",
                description="Unusual spike",
                detected_value=150,
                expected_value=100
            )
        ]

        trust_analysis = {
            "rules_analyzed": 5,
            "high_performing_rules": [
                {
                    "rule_id": "RULE_test_high",
                    "avg_effectiveness": 0.96,
                    "usage_count": 20
                }
            ],
            "low_performing_rules": [],
            "suggestions": []
        }

        recommendations = service.generate_recommendations(
            metrics, patterns, anomalies, trust_analysis
        )

        assert isinstance(recommendations, list)
        if len(recommendations) > 0:
            assert all(isinstance(r, Recommendation) for r in recommendations)
            assert all(hasattr(r, 'priority') for r in recommendations)
            assert all(hasattr(r, 'category') for r in recommendations)

    def test_generate_weekly_insight(self, temp_vault):
        """Test complete weekly insight generation."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        week_start = now - timedelta(days=now.weekday())

        insight, file_path = service.generate_weekly_insight(week_start=week_start)

        assert isinstance(insight, Insight)
        assert insight.insight_id.startswith("INSIGHT_")
        assert file_path.exists()
        assert file_path.suffix == ".json"

        # Verify JSON content
        with open(file_path) as f:
            data = json.load(f)
        
        assert data["insight_id"] == insight.insight_id
        assert "metrics" in data
        assert "patterns" in data
        assert "recommendations" in data

    def test_save_insight(self, temp_vault):
        """Test saving insight to JSON file."""
        service = AnalyticsService(vault_path=temp_vault)

        now = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None)
        insight = Insight(
            insight_id="INSIGHT_test",
            week_start=now,
            week_end=now + timedelta(days=7),
            generated_at=now,
            metrics={"total_actions": 42},
            patterns=[],
            recommendations=[],
            anomalies=[]
        )

        file_path = service._save_insight(insight)

        assert file_path.exists()
        assert file_path.suffix == ".json"

        # Verify content
        with open(file_path) as f:
            data = json.load(f)

        assert data["insight_id"] == "INSIGHT_test"
        assert data["metrics"]["total_actions"] == 42


class TestPatternDetection:
    """Test specific pattern detection algorithms."""

    def test_day_of_week_pattern(self):
        """Test day-of-week pattern detection."""
        # Create test DataFrame with clear pattern
        dates = pd.date_range('2026-03-01', periods=21, freq='D')
        actions_per_day = []
        
        for date in dates:
            # Tuesday and Thursday have more actions
            if date.dayofweek in [1, 3]:  # Tuesday, Thursday
                count = 30
            else:
                count = 10
            
            for _ in range(count):
                actions_per_day.append({
                    'timestamp': date,
                    'action': 'test',
                    'day_name': date.day_name(),
                    'day_of_week': date.dayofweek
                })
        
        df = pd.DataFrame(actions_per_day)

        service = AnalyticsService(vault_path=tempfile.mkdtemp())
        patterns = service.detect_patterns(df)

        # Should detect day-of-week pattern
        day_patterns = [p for p in patterns if p.pattern_type == "day_of_week"]
        assert len(day_patterns) > 0

    def test_anomaly_3sigma_detection(self):
        """Test 3-sigma anomaly detection."""
        # Create test DataFrame with one anomalous day
        dates = pd.date_range('2026-03-01', periods=14, freq='D')
        actions_per_day = []

        for i, date in enumerate(dates):
            # Day 10 has anomalous activity
            if i == 10:
                count = 200  # Much higher than normal
            else:
                count = 50  # Normal activity
            
            for _ in range(count):
                actions_per_day.append({
                    'timestamp': date,
                    'date': date.date(),
                    'action': 'test'
                })

        df = pd.DataFrame(actions_per_day)

        service = AnalyticsService(vault_path=tempfile.mkdtemp())
        metrics = service.calculate_metrics(df)
        anomalies = service.detect_anomalies(df, metrics)

        # Should detect high activity anomaly
        high_activity = [a for a in anomalies if a.anomaly_type == "high_activity"]
        assert len(high_activity) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
