"""
Check adherence tool - Calculate medication adherence percentage.
"""

import logging
from typing import List, Dict, Any
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone, timedelta

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool

logger = logging.getLogger(__name__)


class CheckAdherenceTool(ServerSideTool):
    """Tool for checking medication adherence."""

    def __init__(self):
        """Initialize check adherence tool."""
        super().__init__("check_adherence")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        self.dose_events_table = self.dynamodb.Table("medication_dose_events")

        logger.info(f"CheckAdherenceTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["check_adherence"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.check_adherence]

    @function_tool
    async def check_adherence(
        self,
        period: str = "week",
    ) -> str:
        """
        Calculate medication adherence percentage.

        Args:
            period: Time period to check:
                - "today" - Today only
                - "week" - Last 7 days
                - "month" - Last 30 days

        Returns:
            Adherence report

        Examples:
            - "How am I doing with my medications?"
            - "Show me my adherence"
            - "Am I taking my pills on time?"
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for check_adherence tool")

                return "I'm sorry, I couldn't check your adherence. Please try again."

            logger.info(f"Checking adherence for user {self._user_id}: period={period}")

            # Calculate date range
            now = datetime.now(timezone.utc)

            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_name = "today"
            elif period == "week":
                start_date = now - timedelta(days=7)
                period_name = "this week"
            elif period == "month":
                start_date = now - timedelta(days=30)
                period_name = "this month"
            else:
                start_date = now - timedelta(days=7)
                period_name = "this week"

            # Get all scheduled doses in period
            scheduled_doses = await self._get_scheduled_doses(start_date, now)

            if not scheduled_doses:
                return f"You don't have any scheduled medications for {period_name}."

            # Get dose events
            taken_count = 0

            missed_count = 0

            skipped_count = 0

            missed_details = []

            for dose in scheduled_doses:
                status = await self._get_dose_status(dose)

                if status in ["taken", "late"]:
                    taken_count += 1
                elif status == "skipped":
                    skipped_count += 1
                elif status == "missed":
                    missed_count += 1
                    missed_details.append(dose)

            total_doses = len(scheduled_doses)

            adherence_pct = (taken_count / total_doses * 100) if total_doses > 0 else 0

            # Build response
            response_parts = []

            # Overall adherence
            if adherence_pct >= 95:
                emoji = "🌟"
                message = "Excellent!"
            elif adherence_pct >= 85:
                emoji = "✅"
                message = "Great job!"
            elif adherence_pct >= 75:
                emoji = "👍"
                message = "Pretty good!"
            else:
                emoji = "⚠️"
                message = "Let's work on this."

            response_parts.append(
                f"{emoji} {message} Your adherence {period_name} is {adherence_pct:.0f}%."
            )

            # Breakdown
            response_parts.append(
                f"\nYou took {taken_count} of {total_doses} scheduled doses."
            )

            if skipped_count > 0:
                response_parts.append(
                    f"You skipped {skipped_count} dose{'s' if skipped_count > 1 else ''}."
                )

            if missed_count > 0:
                response_parts.append(
                    f"You missed {missed_count} dose{'s' if missed_count > 1 else ''}."
                )

                # Show details of missed doses
                if missed_count <= 3:
                    response_parts.append("\nMissed doses:")
                    for dose in missed_details:
                        med_name = dose["medication_name"]
                        scheduled_dt = datetime.fromisoformat(
                            dose["scheduled_time"].replace("Z", "+00:00")
                        )
                        day = scheduled_dt.strftime("%A")
                        time = scheduled_dt.strftime("%I:%M %p").lstrip("0")
                        response_parts.append(f"  • {med_name} on {day} at {time}")

            # Encouragement
            if adherence_pct >= 95:
                response_parts.append("\nKeep up the excellent work!")
            elif adherence_pct >= 85:
                response_parts.append("\nYou're doing great! Keep it up!")
            elif adherence_pct >= 75:
                response_parts.append("\nYou're on the right track. Let's aim for 90%!")
            else:
                response_parts.append(
                    "\nLet's work together to improve. Would you like to talk about what's making it difficult?"
                )

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error checking adherence: {e}", exc_info=True)

            return "I'm sorry, I couldn't check your adherence. Please try again."

    async def _get_scheduled_doses(
        self, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get all scheduled doses in a time range."""
        doses = []

        # Get user's medications
        response = self.medications_table.query(
            KeyConditionExpression=Key("user_id").eq(self._user_id),
            FilterExpression=Attr("is_active").eq(True),
        )

        medications = response.get("Items", [])

        for med in medications:
            medication_id = med.get("medication_id")

            name = med.get("name")

            # Get schedules
            schedules = await self._get_schedules(medication_id)

            for schedule in schedules:
                times = schedule.get("times", [])

                for time_str in times:
                    # Generate scheduled times for each day in range
                    current = start_time
                    while current < end_time:
                        scheduled_time = self._calculate_scheduled_time(
                            time_str, current
                        )

                        if start_time <= scheduled_time < end_time:
                            doses.append(
                                {
                                    "medication_id": medication_id,
                                    "medication_name": name,
                                    "scheduled_time": scheduled_time.isoformat(),
                                }
                            )

                        current += timedelta(days=1)

        return doses

    async def _get_schedules(self, medication_id: str) -> List[dict]:
        """Get schedules for a medication."""
        try:
            response = self.schedules_table.query(
                KeyConditionExpression=Key("medication_id").eq(medication_id)
            )

            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")

            return []

    def _calculate_scheduled_time(
        self, time_str: str, reference_time: datetime
    ) -> datetime:
        """Calculate scheduled datetime for a given time string."""
        hour, minute = map(int, time_str.split(":"))

        scheduled = reference_time.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

        return scheduled

    async def _get_dose_status(self, dose: Dict[str, Any]) -> str:
        """Check if a dose was taken, missed, skipped, or is pending."""
        try:
            medication_id = dose["medication_id"]

            scheduled_time = dose["scheduled_time"]

            user_medication_key = f"{self._user_id}#{medication_id}"

            response = self.dose_events_table.get_item(
                Key={
                    "user_medication_key": user_medication_key,
                    "scheduled_time": scheduled_time,
                }
            )

            if "Item" in response:
                return response["Item"].get("status", "unknown")

            # Check if missed (more than 2 hours past scheduled time)
            now = datetime.now(timezone.utc)

            scheduled_dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))

            time_diff = (now - scheduled_dt).total_seconds() / 3600

            if time_diff > 2:
                return "missed"

            return "pending"

        except Exception as e:
            logger.debug(f"Error checking dose status: {e}")

            return "pending"
