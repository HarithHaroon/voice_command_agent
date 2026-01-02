"""
Health Query Tool - Allows agent to query and analyze health data.
"""

import logging
from typing import List
from datetime import datetime

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from clients.health_data_client import HealthDataClient
from services.health_analytics import HealthAnalytics

logger = logging.getLogger(__name__)


class HealthQueryTool(ServerSideTool):
    """Server-side tool for querying health data and generating summaries."""

    def __init__(self, health_client: HealthDataClient):
        super().__init__("health_query")
        self.health_client = health_client
        self.analytics = HealthAnalytics()
        logger.info("HealthQueryTool initialized")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["get_health_summary", "get_specific_metric"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [
            self.get_health_summary,
            self.get_specific_metric,
        ]

    @function_tool
    async def get_health_summary(self, period: str) -> str:
        """
        Get health summary for a preset time period.

        Args:
            period: MUST be one of: "today", "this_week", "this_month", "last_month"
        """
        if not self._user_id:
            logger.error("User ID not set for get_health_summary")
            return "Cannot access health data without user identification."

        # Validate period
        valid_periods = ["today", "this_week", "this_month", "last_month"]
        if period not in valid_periods:
            return (
                f"I can only show health data for: today, this week, this month, or last month. "
                f"For specific dates like October, please use the Health History screen in the app."
            )

        # Calculate hours based on period
        period_hours = {
            "today": 24,
            "this_week": 168,  # 7 days
            "this_month": 720,  # 30 days
            "last_month": 720,  # 30 days (approximate)
        }
        hours = period_hours[period]

        # Fetch data
        aggregated = self.health_client.get_aggregated_metrics(
            self._user_id, hours_back=hours
        )

        # Check if we have data
        if not aggregated:
            return (
                f"I don't have any health data for {period}. "
                "Make sure your watch or health device is connected and syncing."
            )

        # Calculate overall score
        health_score = self.analytics.calculate_overall_health_score(
            aggregated_metrics=aggregated
        )

        # Generate summary
        summary = self.analytics.format_health_summary(health_score, period)

        logger.info(
            f"Health summary generated for user {self._user_id}: "
            f"Score={health_score['overall_score']}, Status={health_score['status']}, "
            f"Period={period}"
        )

        return summary

    @function_tool
    async def get_specific_metric(
        self,
        metric_type: str,
        period: str,
    ) -> str:
        """
        Get information about a specific health metric.

        Args:
            metric_type: The health metric to query (e.g., "heartRate", "steps", "bloodPressure")
            period: MUST be one of: "today", "this_week", "this_month", "last_month"
        """
        if not self._user_id:
            logger.error("User ID not set for get_specific_metric")
            return "Cannot access health data without user identification."

        # Validate period
        valid_periods = ["today", "this_week", "this_month", "last_month"]
        if period not in valid_periods:
            return (
                f"I can only show health data for: today, this week, this month, or last month. "
                f"For specific dates like October, please use the Health History screen in the app."
            )

        # Calculate hours based on period
        period_hours = {
            "today": 24,
            "this_week": 168,  # 7 days
            "this_month": 720,  # 30 days
            "last_month": 720,  # 30 days (approximate)
        }
        hours = period_hours[period]

        # Fetch data
        data = self.health_client.get_health_data(
            self._user_id, hours_back=hours, metric_type=metric_type
        )

        if not data:
            return f"I don't have any {self._format_metric_name(metric_type)} data for {period}."

        # Get latest value
        latest = data[0]
        value = latest.get("value")
        unit = latest.get("unit", "")
        timestamp = latest.get("timestamp")
        source = latest.get("source", "")

        # Score it
        metric_score = self.analytics.calculate_metric_score(metric_type, value)

        # Calculate average if we have multiple readings
        if len(data) > 1:
            values = [
                item.get("value") for item in data if item.get("value") is not None
            ]
            average = sum(values) / len(values)
            avg_text = f"Your average is {self._format_value(average, unit)}. "
        else:
            avg_text = ""

        # Format response
        time_desc = self._format_timestamp(timestamp)
        value_text = self._format_value(value, unit)

        response = (
            f"Your latest {self._format_metric_name(metric_type)} is {value_text} "
            f"from {time_desc}"
        )

        if source:
            response += f" (from {source})"

        response += f". {avg_text}"

        # Add status assessment
        if metric_score["status"] == "excellent":
            response += "This is excellent!"
        elif metric_score["status"] == "good":
            response += "This is in the normal range."
        elif metric_score["status"] == "low":
            response += f"This is lower than normal. {metric_score['message']}."
        elif metric_score["status"] == "high":
            response += f"This is higher than normal. {metric_score['message']}."
        elif metric_score["status"] == "alert":
            response += f"⚠️ {metric_score['message']}."

        logger.info(
            f"Specific metric query: {metric_type}={value} for user {self._user_id}, period={period}"
        )

        return response

    def _format_value(self, value: float, unit: str) -> str:
        """Format a metric value with its unit."""
        if unit == "BEATS_PER_MINUTE":
            return f"{int(value)} bpm"
        elif unit == "PERCENT":
            return f"{int(value)}%"
        elif unit in ["MILLIGRAMS_PER_DECILITER", "MG_DL"]:
            return f"{int(value)} mg/dL"
        elif unit == "STEPS":
            return f"{int(value)} steps"
        elif unit in ["CALORIES", "KILOCALORIES"]:
            return f"{int(value)} calories"
        elif unit in ["KILOMETERS", "KM"]:
            return f"{value:.1f} km"
        elif unit in ["MILES", "MI"]:
            return f"{value:.1f} miles"
        elif unit in ["HOURS", "HR"]:
            return f"{value:.1f} hours"
        elif unit == "MILLISECONDS":
            return f"{value:.1f} ms"
        else:
            return f"{value:.1f} {unit.lower()}"

    def _format_metric_name(self, metric_type: str) -> str:
        """Convert metric type to human-readable name."""
        name_map = {
            "heartRate": "heart rate",
            "restingHeartRate": "resting heart rate",
            "bloodOxygen": "blood oxygen",
            "bloodGlucose": "blood glucose",
            "steps": "step count",
            "activeEnergyBurned": "calories burned",
            "walkingRunningDistance": "distance walked",
            "sleepDeep": "deep sleep",
            "sleepLight": "light sleep",
            "sleepRem": "REM sleep",
            "sleepAwake": "time awake",
            "hrvRmssd": "heart rate variability (RMSSD)",
            "hrvSdnn": "heart rate variability (SDNN)",
            "walkingHeartRate": "walking heart rate",
            "irregularHeartRate": "irregular heart rhythm alert",
            "highHeartRate": "high heart rate alert",
            "lowHeartRate": "low heart rate alert",
            "atrialFibrillationBurden": "atrial fibrillation burden",
        }
        return name_map.get(metric_type, metric_type)

    def _format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp to human-readable."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.utcnow()
            delta = now - dt.replace(tzinfo=None)

            if delta.total_seconds() < 300:  # 5 minutes
                return "just now"
            elif delta.total_seconds() < 3600:  # 1 hour
                minutes = int(delta.total_seconds() / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif delta.total_seconds() < 86400:  # 24 hours
                hours = int(delta.total_seconds() / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(delta.total_seconds() / 86400)
                return f"{days} day{'s' if days != 1 else ''} ago"
        except:
            return "recently"
