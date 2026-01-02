"""
Add medication tool - Add new medication with schedule and interaction checking.
"""

import logging
from typing import List, Dict, Any, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
from datetime import datetime, timezone
from livekit.agents import function_tool
from tools.server_side_tool import ServerSideTool
from helpers.data_channel_sender import DataChannelSender


logger = logging.getLogger(__name__)


class AddMedicationTool(ServerSideTool):
    """Tool for adding new medications with drug interaction checking."""

    def __init__(self):
        """Initialize add medication tool."""
        super().__init__("add_medication")

        import os

        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.dynamodb = boto3.resource("dynamodb", region_name=aws_region)

        self.medications_table = self.dynamodb.Table("medication_records")

        self.schedules_table = self.dynamodb.Table("medication_schedules")

        self.interactions_table = self.dynamodb.Table("medication_interactions")

        logger.info(f"AddMedicationTool initialized with region: {aws_region}")

    def get_tool_methods(self) -> List[str]:
        """Return list of tool method names."""
        return ["add_medication"]

    def get_tool_functions(self) -> List:
        """Return list of function_tool decorated methods."""
        return [self.add_medication]

    @function_tool
    async def add_medication(
        self,
        name: str,
        dosage: str,
        times: List[str],
        frequency: str = "daily",
        days: Optional[List[str]] = None,
        with_food: bool = False,
        instructions: Optional[str] = None,
        criticality: str = "routine",
    ) -> str:
        """
        Add a new medication with schedule.

        Args:
            name: Medication name (e.g., "Lisinopril")
            dosage: Dosage (e.g., "10mg")
            times: List of times (e.g., ["08:00", "20:00"])
            frequency: How often (e.g., "twice daily", "daily")
            days: Which days (e.g., ["Monday", "Wednesday"] or None for daily)
            with_food: Whether to take with food
            instructions: Special instructions
            criticality: routine/important/critical/life_sustaining

        Returns:
            Success message or interaction warning
        """
        try:
            if not self._user_id:
                logger.error("User ID not set for add_medication tool")

                return "I'm sorry, I couldn't add the medication. Please try again."

            logger.info(f"Adding medication '{name}' for user: {self._user_id}")

            # Step 1: Check drug interactions
            interaction = await self._check_interactions(name)

            if interaction:
                severity = interaction.get("severity", "unknown")

                description = interaction.get("description", "")

                recommendation = interaction.get("recommendation", "")

                if severity in ["major", "contraindicated"]:
                    return f"⚠️ WARNING: {severity.upper()} interaction found!\n\n{description}\n\n{recommendation}\n\nI strongly recommend consulting your doctor before adding this medication. Should I add it anyway?"
                elif severity == "moderate":
                    return f"⚠️ Moderate interaction found: {description}\n\n{recommendation}\n\nShould I still add this medication?"

            # Step 2: Create medication record
            medication_id = str(uuid.uuid4())

            now = datetime.now(timezone.utc).isoformat()

            medication_item = {
                "user_id": self._user_id,
                "medication_id": medication_id,
                "name": name,
                "dosage": dosage,
                "form": "pill",  # Default, can be enhanced later
                "instructions": instructions or "",
                "criticality": criticality,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "created_by": "voice",
                "refills_remaining": 0,
                "quantity": 30,  # Default
                "days_supply": 30,  # Default
            }

            self.medications_table.put_item(Item=medication_item)

            logger.info(f"Created medication record: {medication_id}")

            # Step 3: Create schedule
            schedule_id = str(uuid.uuid4())

            schedule_item = {
                "schedule_id": schedule_id,
                "medication_id": medication_id,
                "user_id": self._user_id,
                "times": times,
                "days": days or ["daily"],
                "frequency": frequency,
                "with_food": with_food,
                "special_instructions": instructions or "",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }

            self.schedules_table.put_item(Item=schedule_item)

            logger.info(f"Created schedule: {schedule_id}")

            # Step 4: Build response
            times_str = self._format_times(times)

            response = f"Added {name} {dosage} to your medications. "

            if with_food:
                response += "Take with food. "

            response += f"Reminders set for {times_str}"

            if days and days != ["daily"]:
                days_str = ", ".join(days)

                response += f" on {days_str}"
            else:
                response += " daily"

            response += "."

            if not interaction:
                response += " No interactions found with your other medications."

            # Send event to mobile app
            if self._session:
                await DataChannelSender.send_medication_event(
                    session=self._session,
                    action="medication_added",
                    medication_data={
                        "name": name,
                        "dosage": dosage,
                        "times": times,
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error adding medication: {e}", exc_info=True)

            return "I'm sorry, I couldn't add the medication. Please try again."

    async def _check_interactions(
        self, new_medication: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if new medication interacts with existing medications.

        Returns:
            Interaction dict if found, None otherwise
        """
        try:
            # Get user's existing medications
            response = self.medications_table.query(
                KeyConditionExpression=Key("user_id").eq(self._user_id),
                FilterExpression=Attr("is_active").eq(True),
            )

            existing_meds = response.get("Items", [])

            new_med_lower = new_medication.lower().strip()

            # Check against each existing medication
            for existing_med in existing_meds:
                existing_name = existing_med.get("name", "").lower().strip()

                # Check interaction both ways (A→B and B→A)
                interaction = await self._query_interaction(
                    new_med_lower, existing_name
                )

                if interaction:
                    return interaction

                interaction = await self._query_interaction(
                    existing_name, new_med_lower
                )
                if interaction:
                    return interaction

            return None

        except Exception as e:
            logger.error(f"Error checking interactions: {e}")

            return None

    async def _query_interaction(
        self, medication_1: str, medication_2: str
    ) -> Optional[Dict[str, Any]]:
        """Query interaction table for specific pair."""
        try:
            response = self.interactions_table.get_item(
                Key={
                    "medication_name_1": medication_1,
                    "medication_name_2": medication_2,
                }
            )
            return response.get("Item")
        except Exception as e:
            logger.debug(f"No interaction found for {medication_1} + {medication_2}")

            return None

    def _format_times(self, times: List[str]) -> str:
        """Format times list into natural language."""
        if len(times) == 1:
            return times[0]
        elif len(times) == 2:
            return f"{times[0]} and {times[1]}"
        else:
            return ", ".join(times[:-1]) + f", and {times[-1]}"
