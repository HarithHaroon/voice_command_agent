"""
Skip dose tool - Mark medication dose as skipped.
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


class SkipDoseTool(ServerSideTool):
    """Tool for marking medication doses as skipped."""

    def __init__(self):
        """Initialize skip dose tool."""
        super().__init__("skip_dose")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        self.dose_events_table = self.dynamodb.Table("medication_dose_events")

        logger.info(f"SkipDoseTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["skip_dose"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.skip_dose]

    from helpers.data_channel_sender import DataChannelSender

    @function_tool
    async def skip_dose(
        self,
        medication_name: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str:
        """
        Mark a medication dose as skipped.

        Args:
            medication_name: Name of medication to skip. If not provided, skips most recent.
            reason: Optional reason for skipping

        Returns:
            Confirmation message

        Examples:
            - "Skip this dose"
            - "Skip my Lisinopril"
            - "I'll take it later"
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for skip_dose tool")
                return "I'm sorry, I couldn't skip the medication. Please try again."

            logger.info(
                f"Skipping dose for user {self._user_id}: medication={medication_name}"
            )

            # Find the dose to skip
            dose_info = await self._find_dose_to_skip(medication_name)

            if not dose_info:
                return (
                    "I couldn't find a pending dose to skip. "
                    "Which medication would you like to skip?"
                )

            medication_id = dose_info["medication_id"]
            medication_name = dose_info["medication_name"]
            scheduled_time = dose_info["scheduled_time"]
            criticality = dose_info.get("criticality", "routine")

            # Log the skipped dose event
            now = datetime.now(timezone.utc)
            dose_event_id = str(uuid.uuid4())
            user_medication_key = f"{self._user_id}#{medication_id}"
            user_status_key = f"{self._user_id}#skipped"

            dose_event = {
                "dose_event_id": dose_event_id,
                "user_id": self._user_id,
                "medication_id": medication_id,
                "user_medication_key": user_medication_key,
                "user_status_key": user_status_key,
                "scheduled_time": scheduled_time,
                "actual_time": None,  # Not taken
                "status": "skipped",
                "method": "voice",
                "notes": reason or "",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.dose_events_table.put_item(Item=dose_event)

            logger.info(f"Logged skipped dose: {dose_event_id}")

            # ========== SEND DATA CHANNEL EVENT ==========
            if self._session:
                await DataChannelSender.send_medication_event(
                    session=self._session,
                    action="dose_skipped",
                    medication_data={
                        "name": medication_name,
                        "scheduled_time": scheduled_time,
                        "reason": reason or "",
                        "criticality": criticality,
                    },
                )
            # ============================================

            # Build response based on criticality
            response = f"Okay, I've marked your {medication_name} as skipped. "

            if criticality in ["critical", "life_sustaining"]:
                response += (
                    "This is an important medication. Is everything alright? "
                    "Would you like me to notify your caregiver?"
                )
            elif criticality == "important":
                response += "Is everything okay? Let me know if you need help."
            else:
                response += "No problem."

            return response

        except Exception as e:
            logger.error(f"Error skipping dose: {e}", exc_info=True)
            return "I'm sorry, I couldn't skip the medication. Please try again."

    async def _find_dose_to_skip(
        self, medication_name: Optional[str]
    ) -> Optional[dict]:
        """
        Find the dose that should be skipped.

        Returns dict with medication_id, medication_name, scheduled_time, criticality
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

                criticality = med.get("criticality", "routine")

                # Get schedules
                schedules = await self._get_schedules(medication_id)

                for schedule in schedules:
                    times = schedule.get("times", [])

                    for time_str in times:
                        # Calculate scheduled datetime for today
                        scheduled_time = self._calculate_scheduled_time(time_str, now)

                        # Check if this dose is within the last 2 hours or next 30 min
                        time_diff = (now - scheduled_time).total_seconds() / 60

                        if -30 <= time_diff <= 120:  # 30 min early to 2 hours late
                            # Check if already logged (taken or skipped)
                            already_logged = await self._is_dose_logged(
                                medication_id, scheduled_time.isoformat()
                            )

                            if not already_logged:
                                candidates.append(
                                    {
                                        "medication_id": medication_id,
                                        "medication_name": name,
                                        "scheduled_time": scheduled_time.isoformat(),
                                        "criticality": criticality,
                                        "time_diff": abs(time_diff),
                                    }
                                )

            # Return the closest match
            if candidates:
                candidates.sort(key=lambda x: x["time_diff"])
                return candidates[0]

            return None

        except Exception as e:
            logger.error(f"Error finding dose to skip: {e}")

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

    def _calculate_scheduled_time(
        self, time_str: str, reference_time: datetime
    ) -> datetime:
        """Calculate scheduled datetime for a given time string."""
        hour, minute = map(int, time_str.split(":"))

        scheduled = reference_time.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

        return scheduled

    async def _is_dose_logged(self, medication_id: str, scheduled_time: str) -> bool:
        """Check if a dose has already been logged (taken or skipped)."""
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
            logger.debug(f"Dose not found (not logged): {e}")

            return False
