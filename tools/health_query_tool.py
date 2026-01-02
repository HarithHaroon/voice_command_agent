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
        return ["get_health_summary", "get_morning_summary", "get_specific_metric"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [
            self.get_health_summary,
            self.get_morning_summary,
            self.get_specific_metric,
        ]

    @function_tool
    async def get_health_summary(
        self, timeframe: str = "24hours", start_date: str = "", end_date: str = ""
    ) -> str:
        """Get health summary for a timeframe."""
        if not self._user_id:
            logger.error("User ID not set for get_health_summary")
            return "Cannot access health data without user identification."

        from datetime import datetime, timedelta

        # Calculate date range
        if timeframe == "custom" and start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)

                # Add time to end date to include full day
                end = end.replace(hour=23, minute=59, second=59)

                if end <= start:
                    return "End date must be after start date."

                logger.info(f"Custom date range: {start_date} to {end_date}")

                # 🆕 USE NEW METHOD WITH ABSOLUTE DATES
                aggregated = self.health_client.get_aggregated_metrics_by_date(
                    self._user_id, start_date=start, end_date=end
                )

            except ValueError as e:
                return f"Invalid date format. Please use YYYY-MM-DD format. Error: {e}"
        else:
            # Standard timeframes (relative to now)
            hours_map = {"24hours": 24, "week": 168, "month": 720}
            hours = hours_map.get(timeframe, 24)

            # Use old method for relative timeframes
            aggregated = self.health_client.get_aggregated_metrics(
                self._user_id, hours_back=hours
            )

        # ✅ SINGLE CHECK FOR NO DATA
        if not aggregated:
            if timeframe == "custom":
                return (
                    f"I don't have any health data between {start_date} and {end_date}. "
                    "Make sure your watch or health device was connected and syncing during that period."
                )
            else:
                return (
                    f"I don't have any health data from the last {timeframe}. "
                    "Make sure your watch or health device is connected and syncing."
                )

        # Calculate overall score
        health_score = self.analytics.calculate_overall_health_score(
            aggregated_metrics=aggregated
        )

        # Generate summary with custom message for date ranges
        if timeframe == "custom":
            summary = self.analytics.format_health_summary(
                health_score, f"{start_date} to {end_date}"
            )
            logger.info(
                f"Health summary generated for user {self._user_id}: "
                f"Score={health_score['overall_score']}, Status={health_score['status']}, "
                f"DateRange={start_date} to {end_date}"
            )
        else:
            summary = self.analytics.format_health_summary(health_score, timeframe)
            hours = hours_map.get(timeframe, 24)  # Define hours here for logging
            logger.info(
                f"Health summary generated for user {self._user_id}: "
                f"Score={health_score['overall_score']}, Status={health_score['status']}, "
                f"Hours={hours}"
            )

        return summary

    @function_tool
    async def get_morning_summary(self) -> str:
        """
        Get morning health check summary.

        Returns:
            Morning greeting with health summary
        """
        if not self._user_id:
            logger.error("User ID not set for get_morning_summary")
            return (
                "Good morning! Cannot access health data without user identification."
            )

        try:
            # Get last 24 hours of data
            aggregated = self.health_client.get_aggregated_metrics(
                self._user_id, hours_back=24
            )

            if not aggregated:
                return (
                    "Good morning! I don't have health data from the last 24 hours. "
                    "Make sure your devices are syncing properly."
                )

            # Calculate score
            health_score = self.analytics.calculate_overall_health_score(
                aggregated_metrics=aggregated
            )

            # Generate friendly morning summary
            summary = self.analytics.generate_morning_summary(health_score)

            logger.info(
                f"Morning summary generated for user {self._user_id}: "
                f"Score={health_score['overall_score']}"
            )

            return summary

        except Exception as e:
            logger.error(f"Morning summary failed: {e}", exc_info=True)
            return (
                "Good morning! I'm having trouble accessing your health data right now."
            )

    @function_tool
    async def get_specific_metric(
        self,
        metric_type: str,
        timeframe: str = "24hours",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Get information about a specific health metric."""
        if not self._user_id:
            logger.error("User ID not set for get_specific_metric")
            return "Cannot access health data without user identification."

        from datetime import datetime

        # Calculate date range
        if timeframe == "custom" and start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)

                # Add time to end date to include full day
                end = end.replace(hour=23, minute=59, second=59)

                if end <= start:
                    return "End date must be after start date."

                # 🆕 USE NEW METHOD WITH ABSOLUTE DATES
                data = self.health_client.get_health_data_by_date(
                    self._user_id,
                    start_date=start,
                    end_date=end,
                    metric_type=metric_type,
                )
            except ValueError as e:
                return f"Invalid date format. Please use YYYY-MM-DD format. Error: {e}"
        else:
            # Standard timeframes
            hours_map = {"24hours": 24, "week": 168, "month": 720}
            hours = hours_map.get(timeframe, 24)

            # Use old method for relative timeframes
            data = self.health_client.get_health_data(
                self._user_id, hours_back=hours, metric_type=metric_type
            )

        if not data:
            if timeframe == "custom":
                return f"I don't have any {metric_type} data between {start_date} and {end_date}."
            else:
                return f"I don't have any {metric_type} data for the last {timeframe}."

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
            f"Specific metric query: {metric_type}={value} for user {self._user_id}"
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
