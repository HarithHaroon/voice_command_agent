"""
Confirm dose tool - Mark medication dose as taken.
"""

import logging
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime, timezone

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from helpers.data_channel_sender import DataChannelSender

logger = logging.getLogger(__name__)


class ConfirmDoseTool(ServerSideTool):
    """Tool for confirming medication doses as taken."""

    def __init__(self):
        """Initialize confirm dose tool."""
        super().__init__("confirm_dose")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        self.dose_events_table = self.dynamodb.Table("medication_dose_events")

        logger.info(f"ConfirmDoseTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["confirm_dose"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.confirm_dose]

    from helpers.data_channel_sender import DataChannelSender

    @function_tool
    async def confirm_dose(
        self,
        medication_name: Optional[str] = None,
        time_period: Optional[str] = None,
    ) -> str:
        """
        Confirm that a medication dose was taken.

        Args:
            medication_name: Name of medication (e.g., "Lisinopril").
                        If not provided, confirms most recent pending dose.
            time_period: When it was scheduled (e.g., "morning", "8am", "now").
                        If not provided, uses current time.

        Returns:
            Confirmation message

        Examples:
            - "I took it" → confirms most recent dose
            - "I took my Lisinopril" → confirms Lisinopril dose
            - "I took my morning pills" → confirms morning doses
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for confirm_dose tool")
                return "I'm sorry, I couldn't log your medication. Please try again."

            logger.info(
                f"Confirming dose for user {self._user_id}: "
                f"medication={medication_name}, time={time_period}"
            )

            # Find the dose to confirm
            dose_info = await self._find_dose_to_confirm(medication_name, time_period)

            if not dose_info:
                return (
                    "I couldn't find a pending dose to confirm. "
                    "Which medication did you take?"
                )

            medication_id = dose_info["medication_id"]

            medication_name = dose_info["medication_name"]

            scheduled_time = dose_info["scheduled_time"]

            # Log the dose event
            now = datetime.now(timezone.utc)

            dose_event_id = str(uuid.uuid4())

            user_medication_key = f"{self._user_id}#{medication_id}"

            user_status_key = f"{self._user_id}#taken"

            # Determine if dose is late
            scheduled_dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))

            time_diff = (now - scheduled_dt).total_seconds() / 60  # minutes

            status = "taken" if time_diff <= 30 else "late"

            dose_event = {
                "dose_event_id": dose_event_id,
                "user_id": self._user_id,
                "medication_id": medication_id,
                "user_medication_key": user_medication_key,
                "user_status_key": user_status_key,
                "scheduled_time": scheduled_time,
                "actual_time": now.isoformat(),
                "status": status,
                "method": "voice",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.dose_events_table.put_item(Item=dose_event)

            logger.info(f"Logged dose event: {dose_event_id}")

            # ========== SEND DATA CHANNEL EVENT ==========
            if self._session:
                await DataChannelSender.send_medication_event(
                    session=self._session,
                    action="dose_confirmed",
                    medication_data={
                        "name": medication_name,
                        "scheduled_time": scheduled_time,
                        "actual_time": now.isoformat(),
                        "status": status,
                    },
                )
            # ============================================

            # Build response
            actual_time_str = now.strftime("%I:%M %p").lstrip("0")

            if status == "late":
                minutes_late = int(time_diff)
                return (
                    f"Got it! I've logged your {medication_name} at {actual_time_str}. "
                    f"That's {minutes_late} minutes late, but better late than never!"
                )
            else:
                return f"Great! I've logged your {medication_name} at {actual_time_str}. Keep it up!"

        except Exception as e:
            logger.error(f"Error confirming dose: {e}", exc_info=True)

            return "I'm sorry, I couldn't log your medication. Please try again."

    async def _find_dose_to_confirm(
        self, medication_name: Optional[str], time_period: Optional[str]
    ) -> Optional[dict]:
        """
        Find the dose that should be confirmed.

        Returns dict with medication_id, medication_name, scheduled_time
        """
        try:
            now = datetime.now(timezone.utc)

            # Get user's medications
            response = self.medications_table.query(
                KeyConditionExpression=Key("user_id").eq(self._user_id),
                FilterExpression=Attr("is_active").eq(True),
            )

            medications = response.get("Items", [])

            if not medications:
                return None

            # If medication name provided, filter to that medication
            if medication_name:
                medication_name_lower = medication_name.lower().strip()

                medications = [
                    m
                    for m in medications
                    if medication_name_lower in m.get("name", "").lower()
                ]

                if not medications:
                    return None

            # For each medication, find scheduled doses around current time
            candidates = []

            for med in medications:
                medication_id = med.get("medication_id")

                name = med.get("name")

                # Get schedules
                schedules = await self._get_schedules(medication_id)

                for schedule in schedules:
                    times = schedule.get("times", [])

                    for time_str in times:
                        # Check if this time matches the time_period
                        if time_period and not self._matches_time_period(
                            time_str, time_period
                        ):
                            continue

                        # Calculate scheduled datetime for today
                        scheduled_time = self._calculate_scheduled_time(time_str, now)

                        # Check if this dose is within the last 2 hours
                        time_diff = (now - scheduled_time).total_seconds() / 60

                        if -30 <= time_diff <= 120:  # 30 min early to 2 hours late
                            # Check if already confirmed
                            already_confirmed = await self._is_dose_confirmed(
                                medication_id, scheduled_time.isoformat()
                            )

                            if not already_confirmed:
                                candidates.append(
                                    {
                                        "medication_id": medication_id,
                                        "medication_name": name,
                                        "scheduled_time": scheduled_time.isoformat(),
                                        "time_diff": abs(time_diff),
                                    }
                                )

            # Return the closest match
            if candidates:
                candidates.sort(key=lambda x: x["time_diff"])
                return candidates[0]

            return None

        except Exception as e:
            logger.error(f"Error finding dose: {e}")

            return None

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

    def _matches_time_period(self, time_str: str, time_period: str) -> bool:
        """Check if time_str matches the time_period description."""
        time_period_lower = time_period.lower().strip()

        # Parse time
        hour = int(time_str.split(":")[0])

        # Morning: 5am-11am
        if "morning" in time_period_lower:
            return 5 <= hour < 12

        # Afternoon: 12pm-5pm
        if "afternoon" in time_period_lower:
            return 12 <= hour < 17

        # Evening: 5pm-9pm
        if "evening" in time_period_lower:
            return 17 <= hour < 21

        # Night: 9pm-5am
        if "night" in time_period_lower:
            return hour >= 21 or hour < 5

        # Specific time mentioned
        if (
            time_str in time_period_lower
            or time_str.replace(":", "") in time_period_lower
        ):
            return True

        # Default: matches any
        return True

    def _calculate_scheduled_time(
        self, time_str: str, reference_time: datetime
    ) -> datetime:
        """Calculate scheduled datetime for a given time string."""
        hour, minute = map(int, time_str.split(":"))

        scheduled = reference_time.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

        return scheduled

    async def _is_dose_confirmed(self, medication_id: str, scheduled_time: str) -> bool:
        """Check if a dose has already been confirmed."""
        try:
            user_medication_key = f"{self._user_id}#{medication_id}"

            response = self.dose_events_table.get_item(
                Key={
                    "user_medication_key": user_medication_key,
                    "scheduled_time": scheduled_time,
                }
            )

            return "Item" in response

        except Exception as e:
            logger.debug(f"Dose not found (not confirmed): {e}")

            return False
