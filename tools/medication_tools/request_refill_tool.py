"""
Request refill tool - Create refill reminder (stub for MVP).
"""

import logging
from typing import List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime, timezone

from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool

logger = logging.getLogger(__name__)


class RequestRefillTool(ServerSideTool):
    """Tool for requesting medication refills (stub - creates TODO)."""

    def __init__(self):
        """Initialize request refill tool."""
        super().__init__("request_refill")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.todos_table = self.dynamodb.Table("medication_todos")

        logger.info(f"RequestRefillTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["request_refill"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.request_refill]

    @function_tool
    async def request_refill(
        self,
        medication_name: Optional[str] = None,
    ) -> str:
        """
        Request a medication refill.

        For MVP: Creates a reminder to call pharmacy.
        Future: Will integrate with pharmacy APIs.

        Args:
            medication_name: Name of medication to refill. If not provided,
                           checks for low supply medications.

        Returns:
            Confirmation message

        Examples:
            - "I'm running low on Lisinopril"
            - "Refill my blood pressure medication"
            - "Order more pills"
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for request_refill tool")
                return "I'm sorry, I couldn't create the refill reminder. Please try again."

            logger.info(
                f"Requesting refill for user {self._user_id}: medication={medication_name}"
            )

            # Find the medication
            medication = await self._find_medication(medication_name)

            if not medication:
                return (
                    "I couldn't find that medication. "
                    "Which medication needs a refill?"
                )

            med_name = medication.get("name")

            med_id = medication.get("medication_id")

            pharmacy = medication.get("pharmacy", "your pharmacy")

            pharmacy_phone = medication.get("pharmacy_phone")

            days_supply = medication.get("days_supply", 0)

            # Calculate days remaining (simplified - assumes daily use)
            # In real system, would calculate from dose_events
            days_remaining = days_supply  # Placeholder

            # Create TODO for refill
            now = datetime.now(timezone.utc)

            todo_id = str(uuid.uuid4())

            todo_item = {
                "todo_id": todo_id,
                "user_id": self._user_id,
                "type": "refill_reminder",
                "status": "pending",
                "priority": "normal" if days_remaining > 7 else "high",
                "data": {
                    "medication_id": med_id,
                    "medication_name": med_name,
                    "pharmacy": pharmacy,
                    "pharmacy_phone": pharmacy_phone or "unknown",
                    "days_remaining": days_remaining,
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            self.todos_table.put_item(Item=todo_item)

            logger.info(f"Created refill TODO: {todo_id}")

            # Build response
            response = f"I've created a reminder to refill your {med_name}. "

            if pharmacy_phone:
                response += f"You can call {pharmacy} at {pharmacy_phone}. "
            else:
                response += f"Please call {pharmacy} when you have a chance. "

            if days_remaining <= 3:
                response += "⚠️ You're running low - try to refill soon!"
            elif days_remaining <= 7:
                response += "You have about a week left."
            else:
                response += "You still have some time."

            return response

        except Exception as e:
            logger.error(f"Error requesting refill: {e}", exc_info=True)

            return "I'm sorry, I couldn't create the refill reminder. Please try again."

    async def _find_medication(self, medication_name: Optional[str]) -> Optional[dict]:
        """Find medication by name."""
        try:
            # Get user's medications
            response = self.medications_table.query(
                KeyConditionExpression=Key("user_id").eq(self._user_id),
                FilterExpression=Attr("is_active").eq(True),
            )

            medications = response.get("Items", [])

            if not medications:
                return None

            # If medication name provided, find it
            if medication_name:
                medication_name_lower = medication_name.lower().strip()
                for med in medications:
                    if medication_name_lower in med.get("name", "").lower():
                        return med
                return None

            # If no name provided, return first low-supply medication
            for med in medications:
                days_supply = med.get("days_supply", 0)
                if days_supply <= 7:
                    return med

            # If none low, return first medication
            return medications[0] if medications else None

        except Exception as e:
            logger.error(f"Error finding medication: {e}")

            return None
