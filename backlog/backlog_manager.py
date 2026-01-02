"""
BacklogManager - Core logic for managing backlog items in DynamoDB.

Handles all CRUD operations for user reminders and tasks.
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")
load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)


class BacklogManager:
    """Manages backlog items (reminders/tasks) in DynamoDB."""

    TABLE_NAME = "BacklogItems"
    GSI_NAME = "ScheduledTimeIndex"

    def __init__(self, dynamodb_resource=None):
        """
        Initialize BacklogManager.

        Args:
            dynamodb_resource: Optional boto3 DynamoDB resource.
                               If None, creates one from environment variables.
        """
        if dynamodb_resource is None:
            self.dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
        else:
            self.dynamodb = dynamodb_resource

        self.table = self.dynamodb.Table(self.TABLE_NAME)
        logger.info(f"BacklogManager initialized with table: {self.TABLE_NAME}")

    def add_item(
        self,
        user_id: str,
        title: str,
        scheduled_datetime: datetime,
        remind_before_minutes: int = 15,
        recurrence: str = "once",
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Add a new backlog item.

        Args:
            user_id: User identifier
            title: What to remind about (e.g., "call my son")
            scheduled_datetime: When the task is due
            remind_before_minutes: How early to remind (default 15)
            recurrence: "once", "daily", "weekly", or "monthly"
            notes: Optional additional context

        Returns:
            The created item dictionary
        """
        item_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "user_id": user_id,
            "item_id": item_id,
            "title": title,
            "scheduled_time": scheduled_datetime.isoformat(),
            "remind_before_minutes": remind_before_minutes,
            "recurrence": recurrence,
            "is_active": True,
            "is_completed": False,
            "completed_at": None,
            "notes": notes,
            "created_at": now.isoformat(),
            "last_reminded_at": None,
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Added backlog item: {item_id} for user {user_id}")
            return item

        except ClientError as e:
            logger.error(f"Failed to add backlog item: {e}")
            raise

    def get_item(self, user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single backlog item.

        Args:
            user_id: User identifier
            item_id: Item identifier

        Returns:
            Item dictionary or None if not found
        """
        try:
            response = self.table.get_item(Key={"user_id": user_id, "item_id": item_id})
            return response.get("Item")

        except ClientError as e:
            logger.error(f"Failed to get backlog item: {e}")
            raise

    def delete_item(self, user_id: str, item_id: str) -> bool:
        """
        Hard delete a backlog item (permanently remove from DynamoDB).

        Args:
            user_id: User identifier
            item_id: Item identifier

        Returns:
            True if successful
        """
        try:
            self.table.delete_item(Key={"user_id": user_id, "item_id": item_id})
            logger.info(f"Deleted backlog item: {item_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete backlog item: {e}")
            raise

    def get_upcoming_items(
        self, user_id: str, hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming active items within a time window.

        Args:
            user_id: User identifier
            hours_ahead: How many hours ahead to look (default 24)

        Returns:
            List of upcoming items sorted by scheduled_time
        """
        now = datetime.utcnow()
        future_cutoff = now + timedelta(hours=hours_ahead)

        try:
            # Query using GSI for efficient time-based retrieval
            response = self.table.query(
                IndexName=self.GSI_NAME,
                KeyConditionExpression=(
                    Key("user_id").eq(user_id)
                    & Key("scheduled_time").between(
                        now.isoformat(), future_cutoff.isoformat()
                    )
                ),
                FilterExpression=Attr("is_active").eq(True)
                & Attr("is_completed").eq(False),
            )

            items = response.get("Items", [])

            # logger.info(
            #     f"Found {len(items)} upcoming items for user {user_id} "
            #     f"(next {hours_ahead} hours)"
            # )

            return items

        except ClientError as e:
            logger.error(f"Failed to get upcoming items: {e}")
            raise

    def get_due_reminders(
        self, user_id: str, current_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get items that are due for reminder announcement.

        An item is due if: current_time >= (scheduled_time - remind_before_minutes)
        AND it hasn't been reminded in the last 5 minutes.

        Args:
            user_id: User identifier
            current_time: Current time (defaults to utcnow)

        Returns:
            List of items that should be announced now
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Get items scheduled within the next 24 hours
        # (wider window to catch various remind_before_minutes values)
        upcoming = self.get_upcoming_items(user_id, hours_ahead=24)

        due_items = []
        for item in upcoming:
            scheduled_time = datetime.fromisoformat(item["scheduled_time"])
            remind_before = timedelta(minutes=int(item.get("remind_before_minutes", 0)))
            remind_at_time = scheduled_time - remind_before

            # Check if it's time to remind
            if current_time >= remind_at_time:
                # Check if already reminded recently (within 5 minutes)
                last_reminded = item.get("last_reminded_at")
                if last_reminded:
                    last_reminded_time = datetime.fromisoformat(last_reminded)
                    if (current_time - last_reminded_time) < timedelta(minutes=5):
                        continue  # Skip - already reminded recently

                due_items.append(item)

        # logger.info(f"Found {len(due_items)} due reminders for user {user_id}")

        return due_items

    def update_reminded_timestamp(self, user_id: str, item_id: str) -> bool:
        """
        Update the last_reminded_at timestamp for an item.

        Args:
            user_id: User identifier
            item_id: Item identifier

        Returns:
            True if successful
        """
        now = datetime.utcnow()

        try:
            self.table.update_item(
                Key={"user_id": user_id, "item_id": item_id},
                UpdateExpression="SET last_reminded_at = :time",
                ExpressionAttributeValues={":time": now.isoformat()},
            )
            logger.info(f"Updated reminded timestamp for item: {item_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to update reminded timestamp: {e}")
            raise

    def list_all_active(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active (non-deleted) reminders for a user.

        Args:
            user_id: User identifier

        Returns:
            List of all active items sorted by scheduled_time
        """
        try:
            response = self.table.query(
                IndexName=self.GSI_NAME,
                KeyConditionExpression=Key("user_id").eq(user_id),
                FilterExpression=Attr("is_active").eq(True)
                & Attr("is_completed").eq(False),
            )

            items = response.get("Items", [])

            logger.info(f"Found {len(items)} active items for user {user_id}")

            return items

        except ClientError as e:
            logger.error(f"Failed to list active items: {e}")
            raise

    def complete_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """
        Mark an item as complete.
        For recurring items, automatically creates the next occurrence.

        Args:
            user_id: User identifier
            item_id: Item identifier

        Returns:
            Dictionary with completion result and optional next_item
        """
        # Get the item first
        item = self.get_item(user_id, item_id)

        if not item:
            raise ValueError(f"Item not found: {item_id}")

        now = datetime.utcnow()

        # Mark as completed
        try:
            self.table.update_item(
                Key={"user_id": user_id, "item_id": item_id},
                UpdateExpression="SET is_completed = :completed, completed_at = :time",
                ExpressionAttributeValues={
                    ":completed": True,
                    ":time": now.isoformat(),
                },
            )
            logger.info(f"Completed backlog item: {item_id}")

        except ClientError as e:
            logger.error(f"Failed to complete item: {e}")
            raise

        result = {
            "completed_item": item,
            "next_item": None,
        }

        # If recurring, create next occurrence
        recurrence = item.get("recurrence", "once")

        if recurrence != "once":
            current_scheduled = datetime.fromisoformat(item["scheduled_time"])

            next_scheduled = self._calculate_next_occurrence(
                current_scheduled, recurrence
            )

            next_item = self.add_item(
                user_id=user_id,
                title=item["title"],
                scheduled_datetime=next_scheduled,
                remind_before_minutes=item.get("remind_before_minutes", 15),
                recurrence=recurrence,
                notes=item.get("notes", ""),
            )

            result["next_item"] = next_item

            logger.info(
                f"Created next occurrence for recurring item: {next_item['item_id']} "
                f"scheduled for {next_scheduled.isoformat()}"
            )

        return result

    def _calculate_next_occurrence(
        self, current_time: datetime, recurrence: str
    ) -> datetime:
        """
        Calculate the next scheduled time based on recurrence type.

        Args:
            current_time: Current scheduled datetime
            recurrence: "daily", "weekly", or "monthly"

        Returns:
            Next occurrence datetime
        """
        if recurrence == "daily":
            return current_time + timedelta(days=1)

        elif recurrence == "weekly":
            return current_time + timedelta(weeks=1)

        elif recurrence == "monthly":
            return current_time + relativedelta(months=1)

        else:
            # Default to daily if unknown
            logger.warning(
                f"Unknown recurrence type: {recurrence}, defaulting to daily"
            )
            return current_time + timedelta(days=1)

    def find_item_by_title(
        self, user_id: str, title_search: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find an active item by partial title match.
        Useful for completing/deleting items by description.

        Args:
            user_id: User identifier
            title_search: Partial title to search for (case-insensitive)

        Returns:
            First matching item or None
        """
        items = self.list_all_active(user_id)

        title_lower = title_search.lower()

        for item in items:
            if title_lower in item["title"].lower():
                return item

        return None

    def get_items_by_timeframe(
        self, user_id: str, timeframe: str, current_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get items filtered by human-readable timeframe.

        Args:
            user_id: User identifier
            timeframe: "today", "tomorrow", "week", or "all"
            current_time: Optional current time (for client timezone accuracy)

        Returns:
            List of items matching the timeframe
        """
        if current_time is None:
            current_time = datetime.utcnow()

        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        today_end = today_start + timedelta(days=1)

        tomorrow_end = today_start + timedelta(days=2)

        week_end = today_start + timedelta(days=7)

        if timeframe == "all":
            return self.list_all_active(user_id)

        # Get all active items first
        all_items = self.list_all_active(user_id)

        filtered = []
        for item in all_items:
            scheduled = datetime.fromisoformat(item["scheduled_time"])

            if timeframe == "today":
                if today_start <= scheduled < today_end:
                    filtered.append(item)
            elif timeframe == "tomorrow":
                if today_end <= scheduled < tomorrow_end:
                    filtered.append(item)
            elif timeframe == "week":
                if today_start <= scheduled < week_end:
                    filtered.append(item)

        return filtered
