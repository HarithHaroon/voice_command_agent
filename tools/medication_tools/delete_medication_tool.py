"""
Delete medication tool - Remove medication from user's list.
"""

import logging
from typing import Optional, List
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timezone

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from helpers.data_channel_sender import DataChannelSender

logger = logging.getLogger(__name__)


class DeleteMedicationTool(ServerSideTool):
    """Tool for deleting medications."""

    def __init__(self):
        """Initialize delete medication tool."""
        super().__init__("delete_medication")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        logger.info(f"DeleteMedicationTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["delete_medication"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.delete_medication]

    from helpers.data_channel_sender import DataChannelSender

    @function_tool
    async def delete_medication(
        self,
        medication_name: str,
        confirm: bool = False,
    ) -> str:
        """
        Delete a medication from the user's list.

        IMPORTANT: This is a destructive action. Use with caution.

        Args:
            medication_name: Name of medication to delete
            confirm: Must be True to actually delete (safety check)

        Returns:
            Confirmation message or warning

        Examples:
            - "Delete my Aspirin"
            - "Remove Ibuprofen from my list"
            - "Stop taking Metformin" (Note: should confirm with doctor!)
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for delete_medication tool")
                return "I'm sorry, I couldn't delete the medication. Please try again."

            logger.info(
                f"Deleting medication for user {self._user_id}: {medication_name}"
            )

            # Find the medication
            medication = await self._find_medication(medication_name)

            if not medication:
                return f"I couldn't find '{medication_name}' in your medications."

            medication_id = medication.get("medication_id")
            current_name = medication.get("name")
            criticality = medication.get("criticality", "routine")

            # Safety check for critical medications
            if criticality in ["critical", "life_sustaining"] and not confirm:
                return (
                    f"⚠️ {current_name} is marked as a critical medication. "
                    "Stopping this medication could be dangerous. "
                    "Please consult your doctor before removing it. "
                    "Are you sure you want to delete it?"
                )

            # Ask for confirmation if not provided
            if not confirm:
                return (
                    f"Are you sure you want to delete {current_name}? "
                    "This will remove all reminders and history for this medication. "
                    "Please say 'yes, delete it' to confirm."
                )

            # Soft delete: mark as inactive instead of actually deleting
            now = datetime.now(timezone.utc)

            self.medications_table.update_item(
                Key={
                    "user_id": self._user_id,
                    "medication_id": medication_id,
                },
                UpdateExpression="SET is_active = :inactive, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":inactive": False,
                    ":updated_at": now.isoformat(),
                },
            )

            # Deactivate schedules
            schedules_response = self.schedules_table.query(
                KeyConditionExpression=Key("medication_id").eq(medication_id)
            )

            schedules = schedules_response.get("Items", [])

            for schedule in schedules:
                schedule_id = schedule.get("schedule_id")

                self.schedules_table.update_item(
                    Key={
                        "medication_id": medication_id,
                        "schedule_id": schedule_id,
                    },
                    UpdateExpression="SET is_active = :inactive, updated_at = :updated_at",
                    ExpressionAttributeValues={
                        ":inactive": False,
                        ":updated_at": now.isoformat(),
                    },
                )

            logger.info(f"Deleted (deactivated) medication: {medication_id}")

            # ========== SEND DATA CHANNEL EVENT ==========
            if self._session:
                await DataChannelSender.send_medication_event(
                    session=self._session,
                    action="medication_deleted",
                    medication_data={
                        "name": current_name,
                        "medication_id": medication_id,
                        "criticality": criticality,
                    },
                )
            # ============================================

            # Build response
            response = f"Removed {current_name} from your medications. "

            if criticality in ["critical", "life_sustaining", "important"]:
                response += "⚠️ Please make sure your doctor knows you've stopped this medication."
            else:
                response += "All reminders for this medication have been cancelled."

            return response

        except Exception as e:
            logger.error(f"Error deleting medication: {e}", exc_info=True)
            return "I'm sorry, I couldn't delete the medication. Please try again."

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
