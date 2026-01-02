"""
Edit medication tool - Modify existing medication details.
"""

import logging
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from helpers.data_channel_sender import DataChannelSender

logger = logging.getLogger(__name__)


class EditMedicationTool(ServerSideTool):
    """Tool for editing existing medications."""

    def __init__(self):
        """Initialize edit medication tool."""
        super().__init__("edit_medication")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        logger.info(f"EditMedicationTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["edit_medication"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.edit_medication]

    from helpers.data_channel_sender import DataChannelSender

    @function_tool
    async def edit_medication(
        self,
        medication_name: str,
        new_dosage: Optional[str] = None,
        new_times: Optional[List[str]] = None,
        new_frequency: Optional[str] = None,
        new_instructions: Optional[str] = None,
    ) -> str:
        """
        Edit an existing medication.

        Args:
            medication_name: Name of medication to edit
            new_dosage: New dosage (e.g., "20mg"). Leave None to keep current.
            new_times: New schedule times (e.g., ["08:00", "20:00"]). Leave None to keep current.
            new_frequency: New frequency description. Leave None to keep current.
            new_instructions: New instructions. Leave None to keep current.

        Returns:
            Confirmation message

        Examples:
            - "Change my Lisinopril to 20mg"
            - "Update my blood pressure medication to 8am and 8pm"
            - "Change Metformin instructions to take with food"
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for edit_medication tool")
                return "I'm sorry, I couldn't edit the medication. Please try again."

            logger.info(
                f"Editing medication for user {self._user_id}: {medication_name}"
            )

            # Find the medication
            medication = await self._find_medication(medication_name)

            if not medication:
                return f"I couldn't find '{medication_name}' in your medications. Please check the name."

            medication_id = medication.get("medication_id")
            current_name = medication.get("name")
            now = datetime.now(timezone.utc)

            # Track what was changed
            changes = []

            # Update medication record if needed
            if new_dosage or new_instructions:
                update_expr_parts = ["updated_at = :updated_at"]
                expr_attr_values = {":updated_at": now.isoformat()}

                if new_dosage:
                    update_expr_parts.append("dosage = :dosage")
                    expr_attr_values[":dosage"] = new_dosage
                    changes.append(f"dosage to {new_dosage}")

                if new_instructions:
                    update_expr_parts.append("instructions = :instructions")
                    expr_attr_values[":instructions"] = new_instructions
                    changes.append("instructions")

                self.medications_table.update_item(
                    Key={
                        "user_id": self._user_id,
                        "medication_id": medication_id,
                    },
                    UpdateExpression="SET " + ", ".join(update_expr_parts),
                    ExpressionAttributeValues=expr_attr_values,
                )

                logger.info(f"Updated medication record: {medication_id}")

            # Update schedule if needed
            if new_times or new_frequency:
                # Get existing schedules
                schedules_response = self.schedules_table.query(
                    KeyConditionExpression=Key("medication_id").eq(medication_id)
                )
                schedules = schedules_response.get("Items", [])

                if schedules:
                    schedule = schedules[0]  # Update first schedule
                    schedule_id = schedule.get("schedule_id")

                    update_expr_parts = ["updated_at = :updated_at"]
                    expr_attr_values = {":updated_at": now.isoformat()}

                    if new_times:
                        update_expr_parts.append("times = :times")
                        expr_attr_values[":times"] = new_times
                        times_str = self._format_times(new_times)
                        changes.append(f"schedule to {times_str}")

                    if new_frequency:
                        update_expr_parts.append("frequency = :frequency")
                        expr_attr_values[":frequency"] = new_frequency
                        changes.append(f"frequency to {new_frequency}")

                    self.schedules_table.update_item(
                        Key={
                            "medication_id": medication_id,
                            "schedule_id": schedule_id,
                        },
                        UpdateExpression="SET " + ", ".join(update_expr_parts),
                        ExpressionAttributeValues=expr_attr_values,
                    )

                    logger.info(f"Updated schedule: {schedule_id}")

            # ========== SEND DATA CHANNEL EVENT ==========
            if self._session and changes:
                await DataChannelSender.send_medication_event(
                    session=self._session,
                    action="medication_updated",
                    medication_data={
                        "name": current_name,
                        "medication_id": medication_id,
                        "changes": changes,
                        "new_dosage": new_dosage,
                        "new_times": new_times,
                        "new_frequency": new_frequency,
                    },
                )
            # ============================================

            # Build response
            if changes:
                changes_str = ", ".join(changes)
                return f"Updated {current_name}: changed {changes_str}."
            else:
                return f"No changes made to {current_name}."

        except Exception as e:
            logger.error(f"Error editing medication: {e}", exc_info=True)
            return "I'm sorry, I couldn't edit the medication. Please try again."

    async def _find_medication(self, medication_name: str) -> Optional[dict]:
        """Find medication by name."""
        try:
            medication_name_lower = medication_name.lower().strip()

            # Get user's medications
            response = self.medications_table.query(
                KeyConditionExpression=Key("user_id").eq(self._user_id),
                FilterExpression=Attr("is_active").eq(True),
            )

            medications = response.get("Items", [])

            # Find by name
            for med in medications:
                if medication_name_lower in med.get("name", "").lower():
                    return med

            return None

        except Exception as e:
            logger.error(f"Error finding medication: {e}")

            return None

    def _format_times(self, times: List[str]) -> str:
        """Format times list into natural language."""
        if len(times) == 1:
            return times[0]
        elif len(times) == 2:
            return f"{times[0]} and {times[1]}"
        else:
            return ", ".join(times[:-1]) + f", and {times[-1]}"
