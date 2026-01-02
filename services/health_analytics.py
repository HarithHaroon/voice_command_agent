"""
Health Analytics - Scoring and analysis of health data.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HealthAnalytics:
    """Analyzes health data and provides scores/insights."""

    # Normal ranges for health metrics (elderly-adjusted)
    NORMAL_RANGES = {
        # Vital Signs
        "heartRate": {"min": 60, "max": 100, "optimal_min": 60, "optimal_max": 80},
        "restingHeartRate": {
            "min": 60,
            "max": 80,
            "optimal_min": 60,
            "optimal_max": 75,
        },
        "bloodOxygen": {"min": 95, "max": 100, "optimal_min": 97, "optimal_max": 100},
        "bloodGlucose": {"min": 70, "max": 140, "optimal_min": 80, "optimal_max": 120},
        # Heart Variability (higher is better for HRV)
        "hrvRmssd": {"min": 20, "max": 100, "optimal_min": 30, "optimal_max": 100},
        "hrvSdnn": {"min": 20, "max": 100, "optimal_min": 30, "optimal_max": 100},
        # Activity (daily goals)
        "steps": {"min": 3000, "max": 10000, "optimal_min": 5000, "optimal_max": 10000},
        "activeEnergyBurned": {
            "min": 200,
            "max": 600,
            "optimal_min": 300,
            "optimal_max": 500,
        },
        "walkingRunningDistance": {
            "min": 1.0,
            "max": 5.0,
            "optimal_min": 2.0,
            "optimal_max": 4.0,
        },
        # Sleep (hours)
        "sleepDeep": {"min": 0.5, "max": 2.0, "optimal_min": 1.0, "optimal_max": 1.5},
        "sleepLight": {"min": 2.0, "max": 5.0, "optimal_min": 3.0, "optimal_max": 4.5},
        "sleepRem": {"min": 1.0, "max": 2.5, "optimal_min": 1.5, "optimal_max": 2.0},
        "sleepAwake": {"min": 0, "max": 1.0, "optimal_min": 0, "optimal_max": 0.5},
    }

    # Alert types (binary - presence indicates concern)
    ALERT_TYPES = {
        "irregularHeartRate",
        "highHeartRate",
        "lowHeartRate",
        "atrialFibrillationBurden",
    }

    @staticmethod
    def calculate_metric_score(metric_type: str, value: float) -> Dict[str, Any]:
        """
        Calculate score for a single metric.

        Args:
            metric_type: Type of metric
            value: Current value

        Returns:
            Dictionary with score (0-100), status, and message
        """
        # Handle alert types (binary indicators)
        if metric_type in HealthAnalytics.ALERT_TYPES:
            return {
                "score": 0,
                "status": "alert",
                "message": f"{metric_type} detected",
                "value": value,
            }

        # Handle unknown metrics
        if metric_type not in HealthAnalytics.NORMAL_RANGES:
            return {
                "score": 50,
                "status": "unknown",
                "message": f"No reference range for {metric_type}",
                "value": value,
            }

        ranges = HealthAnalytics.NORMAL_RANGES[metric_type]
        min_val = ranges["min"]
        max_val = ranges["max"]
        optimal_min = ranges["optimal_min"]
        optimal_max = ranges["optimal_max"]

        # Score calculation
        if optimal_min <= value <= optimal_max:
            # Optimal range
            score = 100
            status = "excellent"
            message = f"{metric_type} is in optimal range"
        elif min_val <= value <= max_val:
            # Acceptable but not optimal
            if value < optimal_min:
                deviation = (optimal_min - value) / (optimal_min - min_val)
                score = 100 - (deviation * 20)  # Max 20 point penalty
            else:
                deviation = (value - optimal_max) / (max_val - optimal_max)
                score = 100 - (deviation * 20)
            status = "good"
            message = f"{metric_type} is within acceptable range"
        elif value < min_val:
            # Below normal
            deviation = (min_val - value) / min_val
            score = max(0, 60 - (deviation * 60))
            status = "low"
            message = f"{metric_type} is below normal range"
        else:
            # Above normal
            deviation = (value - max_val) / max_val
            score = max(0, 60 - (deviation * 60))
            status = "high"
            message = f"{metric_type} is above normal range"

        return {
            "score": round(score, 1),
            "status": status,
            "message": message,
            "value": value,
            "normal_range": f"{min_val}-{max_val}",
            "optimal_range": f"{optimal_min}-{optimal_max}",
        }

    @staticmethod
    def calculate_overall_health_score(
        aggregated_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate overall health score from all metrics.

        Args:
            aggregated_metrics: Aggregated health data from HealthDataClient

        Returns:
            Overall score and detailed breakdown with concerns
        """
        scores = []
        metric_details = {}
        alerts = []

        # Score each available metric
        for metric_type, data in aggregated_metrics.items():
            latest_value = data.get("latest")
            if latest_value is not None:
                metric_score = HealthAnalytics.calculate_metric_score(
                    metric_type, latest_value
                )

                # Don't include alerts in overall score calculation
                if metric_type not in HealthAnalytics.ALERT_TYPES:
                    scores.append(metric_score["score"])
                else:
                    alerts.append(metric_score["message"])

                metric_details[metric_type] = metric_score

        # Calculate overall score
        if scores:
            overall_score = sum(scores) / len(scores)
        else:
            overall_score = 50  # Default if no data

        # Determine overall status
        if overall_score >= 85:
            status = "excellent"
        elif overall_score >= 70:
            status = "good"
        elif overall_score >= 50:
            status = "fair"
        else:
            status = "needs_attention"

        # Generate concerns
        concerns = []

        # Add metric concerns
        for metric, details in metric_details.items():
            if details["status"] in ["low", "high"]:
                concerns.append(details["message"])

        # Add alerts
        concerns.extend(alerts)

        return {
            "overall_score": round(overall_score, 1),
            "status": status,
            "metric_details": metric_details,
            "concerns": concerns,
            "alerts": alerts,
            "metrics_analyzed": len(metric_details),
        }

    @staticmethod
    def generate_morning_summary(health_score: Dict[str, Any]) -> str:
        """
        Generate a friendly morning health summary.

        Args:
            health_score: Output from calculate_overall_health_score

        Returns:
            Human-readable summary string
        """
        score = health_score["overall_score"]
        status = health_score["status"]
        concerns = health_score["concerns"]
        alerts = health_score.get("alerts", [])

        # Opening based on score
        if status == "excellent":
            opening = "Good morning! You're doing great today."
        elif status == "good":
            opening = "Good morning! Your health looks good overall."
        elif status == "fair":
            opening = "Good morning! There are a few things to keep an eye on."
        else:
            opening = "Good morning! Let's focus on your health today."

        # Add specific details
        details = []
        metric_details = health_score.get("metric_details", {})

        # Prioritize key metrics
        if "heartRate" in metric_details:
            hr = metric_details["heartRate"]
            details.append(f"heart rate is {int(hr['value'])} bpm")

        if "steps" in metric_details:
            steps = metric_details["steps"]
            details.append(f"you've taken {int(steps['value'])} steps")

        if "bloodOxygen" in metric_details:
            spo2 = metric_details["bloodOxygen"]
            details.append(f"blood oxygen is {int(spo2['value'])}%")

        # Build summary
        summary = opening
        if details:
            summary += " " + ", ".join(details[:3]) + "."

        # Add alerts first (most important)
        if alerts:
            summary += f" ⚠️ Important: {alerts[0]}."
        elif concerns:
            # Only show non-alert concerns if no alerts
            non_alert_concerns = [c for c in concerns if c not in alerts]
            if non_alert_concerns:
                summary += f" Note: {non_alert_concerns[0]}."

        return summary

    @staticmethod
    def format_health_summary(health_score: Dict[str, Any], timeframe: str) -> str:
        """
        Format health score into detailed summary.

        Args:
            health_score: Output from calculate_overall_health_score
            timeframe: Timeframe description (e.g., "24hours", "week")

        Returns:
            Human-readable detailed summary
        """
        score = health_score["overall_score"]
        status = health_score["status"]
        concerns = health_score["concerns"]
        alerts = health_score.get("alerts", [])
        metrics = health_score["metric_details"]

        # Opening
        timeframe_text = {
            "24hours": "the last 24 hours",
            "week": "the past week",
            "month": "the past month",
        }.get(timeframe, timeframe)

        summary = f"Based on your data from {timeframe_text}, your overall health score is {score}/100 ({status})."

        # Add key metrics highlights
        highlights = []

        if "heartRate" in metrics:
            hr = metrics["heartRate"]
            highlights.append(f"heart rate {int(hr['value'])} bpm ({hr['status']})")

        if "steps" in metrics:
            steps = metrics["steps"]
            highlights.append(f"{int(steps['value'])} steps ({steps['status']})")

        if "bloodOxygen" in metrics:
            spo2 = metrics["bloodOxygen"]
            highlights.append(f"blood oxygen {int(spo2['value'])}% ({spo2['status']})")

        if highlights:
            summary += f" Key metrics: {', '.join(highlights[:3])}."

        # Add alerts (most critical)
        if alerts:
            summary += f" ⚠️ Alerts: {', '.join(alerts)}."

        # Add other concerns
        non_alert_concerns = [c for c in concerns if c not in alerts]
        if non_alert_concerns:
            summary += f" Areas to watch: {', '.join(non_alert_concerns[:2])}."
        elif not alerts:
            summary += " Everything looks good!"

        return summary
