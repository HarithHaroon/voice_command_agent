"""
View medications tool - List all user's medications.
"""

import logging
from typing import List, Dict, Any
import boto3
from boto3.dynamodb.conditions import Key, Attr

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool

logger = logging.getLogger(__name__)


class ViewMedicationsTool(ServerSideTool):
    """Tool for viewing user's medications."""

    def __init__(self):
        """Initialize view medications tool."""
        super().__init__("view_medications")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        logger.info(f"ViewMedicationsTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["view_medications"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.view_medications]

    @function_tool
    async def view_medications(self) -> str:
        """
        View all active medications for the user.

        Returns natural language description of all medications.
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for view_medications tool")

                return (
                    "I'm sorry, I couldn't retrieve your medications. Please try again."
                )

            logger.info(f"Viewing medications for user: {self._user_id}")

            # Query DynamoDB for user's medications
            response = self.medications_table.query(
                KeyConditionExpression=Key("user_id").eq(self._user_id),
                FilterExpression=Attr("is_active").eq(True),
            )

            medications = response.get("Items", [])

            if not medications:
                return "You don't have any medications in your list yet. Would you like to add one?"

            # Build natural language response
            response_parts = [
                f"You're taking {len(medications)} medication{'s' if len(medications) > 1 else ''}:"
            ]

            for med in medications:
                name = med.get("name", "Unknown")

                dosage = med.get("dosage", "")

                medication_id = med.get("medication_id")

                # Get schedules for this medication
                schedules = await self._get_schedules(medication_id)

                if schedules:
                    times_str = self._format_times(schedules)

                    response_parts.append(f"- {name} {dosage} {times_str}")
                else:
                    response_parts.append(f"- {name} {dosage}")

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error viewing medications: {e}", exc_info=True)

            return "I'm sorry, I couldn't retrieve your medications right now. Please try again."

    async def _get_schedules(self, medication_id: str) -> List[Dict[str, Any]]:
        """Get schedules for a medication."""
        try:
            response = self.schedules_table.query(
                KeyConditionExpression=Key("medication_id").eq(medication_id)
            )

            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
            return []

    def _format_times(self, schedules: List[Dict[str, Any]]) -> str:
        """Format schedule times into natural language."""
        if not schedules:
            return ""

        schedule = schedules[0]  # Use first schedule

        times = schedule.get("times", [])

        frequency = schedule.get("frequency", "")

        if not times:
            return f"({frequency})" if frequency else ""

        # Format times
        if len(times) == 1:
            return f"at {times[0]}"
        elif len(times) == 2:
            return f"at {times[0]} and {times[1]}"
        else:
            return f"{len(times)} times daily"
