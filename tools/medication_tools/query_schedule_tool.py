"""
Query schedule tool - Show upcoming medication doses.
"""

import logging
from typing import List, Dict, Any
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone, timedelta

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool

logger = logging.getLogger(__name__)


class QueryScheduleTool(ServerSideTool):
    """Tool for querying medication schedules."""

    def __init__(self):
        """Initialize query schedule tool."""
        super().__init__("query_schedule")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        self.dose_events_table = self.dynamodb.Table("medication_dose_events")

        logger.info(f"QueryScheduleTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["query_schedule"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.query_schedule]

    @function_tool
    async def query_schedule(
        self,
        timeframe: str = "today",
    ) -> str:
        """
        Show upcoming medication doses.

        Args:
            timeframe: When to show doses for:
                - "today" - All doses for today
                - "next" - Next upcoming dose
                - "tomorrow" - Tomorrow's doses
                - "week" - This week's schedule

        Returns:
            Schedule information

        Examples:
            - "What medications do I take today?"
            - "When is my next dose?"
            - "What's my schedule for tomorrow?"
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for query_schedule tool")
                return "I'm sorry, I couldn't retrieve your schedule. Please try again."

            logger.info(
                f"Querying schedule for user {self._user_id}: timeframe={timeframe}"
            )

            if timeframe == "next":
                return await self._get_next_dose()
            elif timeframe == "today":
                return await self._get_today_schedule()
            elif timeframe == "tomorrow":
                return await self._get_tomorrow_schedule()
            elif timeframe == "week":
                return await self._get_week_schedule()
            else:
                return await self._get_today_schedule()

        except Exception as e:
            logger.error(f"Error querying schedule: {e}", exc_info=True)

            return "I'm sorry, I couldn't retrieve your schedule. Please try again."

    async def _get_next_dose(self) -> str:
        """Get the next upcoming dose."""
        now = datetime.now(timezone.utc)

        upcoming = await self._get_upcoming_doses(now, hours=24)

        if not upcoming:
            return "You don't have any upcoming doses in the next 24 hours."

        # Sort by time
        upcoming.sort(key=lambda x: x["scheduled_time"])

        next_dose = upcoming[0]

        medication_name = next_dose["medication_name"]

        dosage = next_dose["dosage"]

        scheduled_dt = datetime.fromisoformat(
            next_dose["scheduled_time"].replace("Z", "+00:00")
        )

        # Format time
        time_str = scheduled_dt.strftime("%I:%M %p").lstrip("0")

        # Calculate time until
        time_until = scheduled_dt - now

        hours = int(time_until.total_seconds() / 3600)

        minutes = int((time_until.total_seconds() % 3600) / 60)

        if hours > 0:
            time_until_str = (
                f"in {hours} hour{'s' if hours > 1 else ''} and {minutes} minutes"
            )
        elif minutes > 0:
            time_until_str = f"in {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            time_until_str = "right now"

        return f"Your next medication is {medication_name} {dosage} at {time_str} ({time_until_str})."

    async def _get_today_schedule(self) -> str:
        """Get all doses for today."""
        now = datetime.now(timezone.utc)

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        end_of_day = start_of_day + timedelta(days=1)

        doses = await self._get_doses_in_range(start_of_day, end_of_day)

        if not doses:
            return "You don't have any medications scheduled for today."

        # Group by status
        taken = []

        pending = []

        missed = []

        for dose in doses:
            status = await self._get_dose_status(dose)
            if status == "taken":
                taken.append(dose)
            elif status == "missed":
                missed.append(dose)
            else:
                pending.append(dose)

        # Build response
        total = len(doses)

        response_parts = [f"Today you have {total} dose{'s' if total > 1 else ''}:"]

        if taken:
            response_parts.append(f"\n✅ Taken ({len(taken)}):")
            for dose in taken:
                time_str = self._format_dose_time(dose["scheduled_time"])
                response_parts.append(
                    f"  • {dose['medication_name']} {dose['dosage']} at {time_str}"
                )

        if pending:
            response_parts.append(f"\n⏰ Upcoming ({len(pending)}):")
            for dose in pending:
                time_str = self._format_dose_time(dose["scheduled_time"])
                response_parts.append(
                    f"  • {dose['medication_name']} {dose['dosage']} at {time_str}"
                )

        if missed:
            response_parts.append(f"\n❌ Missed ({len(missed)}):")
            for dose in missed:
                time_str = self._format_dose_time(dose["scheduled_time"])
                response_parts.append(
                    f"  • {dose['medication_name']} {dose['dosage']} at {time_str}"
                )

        return "\n".join(response_parts)

    async def _get_tomorrow_schedule(self) -> str:
        """Get all doses for tomorrow."""
        now = datetime.now(timezone.utc)

        tomorrow_start = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        tomorrow_end = tomorrow_start + timedelta(days=1)

        doses = await self._get_doses_in_range(tomorrow_start, tomorrow_end)

        if not doses:
            return "You don't have any medications scheduled for tomorrow."

        response_parts = [
            f"Tomorrow you have {len(doses)} dose{'s' if len(doses) > 1 else ''}:"
        ]

        for dose in doses:
            time_str = self._format_dose_time(dose["scheduled_time"])
            response_parts.append(
                f"• {dose['medication_name']} {dose['dosage']} at {time_str}"
            )

        return "\n".join(response_parts)

    async def _get_week_schedule(self) -> str:
        """Get summary of this week's schedule."""
        now = datetime.now(timezone.utc)

        week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=7)

        doses = await self._get_doses_in_range(week_start, week_end)

        if not doses:
            return "You don't have any medications scheduled for this week."

        # Group by day
        by_day: Dict[str, List] = {}
        for dose in doses:
            scheduled_dt = datetime.fromisoformat(
                dose["scheduled_time"].replace("Z", "+00:00")
            )
            day_key = scheduled_dt.strftime("%A")

            if day_key not in by_day:
                by_day[day_key] = []
            by_day[day_key].append(dose)

        response_parts = [f"This week you have {len(doses)} total doses:"]

        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]:
            if day in by_day:
                day_doses = by_day[day]
                response_parts.append(f"\n{day} ({len(day_doses)} doses):")
                for dose in day_doses[:3]:  # Show first 3
                    time_str = self._format_dose_time(dose["scheduled_time"])
                    response_parts.append(
                        f"  • {dose['medication_name']} at {time_str}"
                    )
                if len(day_doses) > 3:
                    response_parts.append(f"  • ... and {len(day_doses) - 3} more")

        return "\n".join(response_parts)

    async def _get_doses_in_range(
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

            dosage = med.get("dosage", "")

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
                                    "dosage": dosage,
                                    "scheduled_time": scheduled_time.isoformat(),
                                }
                            )

                        current += timedelta(days=1)

        return doses

    async def _get_upcoming_doses(
        self, from_time: datetime, hours: int
    ) -> List[Dict[str, Any]]:
        """Get upcoming doses from a specific time."""
        end_time = from_time + timedelta(hours=hours)

        return await self._get_doses_in_range(from_time, end_time)

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
        """Check if a dose was taken, missed, or is pending."""
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

    def _format_dose_time(self, iso_time: str) -> str:
        """Format ISO time to readable format."""
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))

        return dt.strftime("%I:%M %p").lstrip("0")
