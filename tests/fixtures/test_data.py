"""
Test data fixtures for multi-agent testing.
Provides mock data for health metrics, reminders, etc.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
import uuid


class TestDataFixtures:
    """Mock data for testing"""

    @staticmethod
    def get_health_data(user_id: str = "test_user_123") -> List[Dict[str, Any]]:
        """
        Generate mock health data for testing.

        Returns sample data for the last 7 days to support
        "today", "this_week", "this_month" queries.

        Matches actual DynamoDB schema with encrypted_data field.
        """
        now = datetime.now()
        health_records = []

        # Generate data for last 7 days
        for days_ago in range(7):
            timestamp_obj = now - timedelta(days=days_ago)
            timestamp_iso = timestamp_obj.isoformat()
            created_at = now.isoformat()

            # Heart rate data
            health_records.append(
                {
                    "elderly_user_id": user_id,
                    "timestamp": timestamp_iso,
                    "created_at": created_at,
                    "type": "heartRate",
                    "unit": "bpm",
                    "encrypted_data": json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "type": "heartRate",
                            "value": 72 + (days_ago * 2),
                            "unit": "bpm",
                            "timestamp": timestamp_iso,
                            "dateFrom": timestamp_iso,
                            "dateTo": timestamp_iso,
                            "source": "appleWatch",
                            "deviceId": "watch_001",
                            "deviceName": "Apple Watch Series 8",
                            "metadata": {},
                        }
                    ),
                }
            )

            # Blood pressure data
            health_records.append(
                {
                    "elderly_user_id": user_id,
                    "timestamp": timestamp_iso,
                    "created_at": created_at,
                    "type": "bloodPressure",
                    "unit": "mmHg",
                    "encrypted_data": json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "type": "bloodPressure",
                            "value": 120,  # Systolic
                            "unit": "mmHg",
                            "timestamp": timestamp_iso,
                            "dateFrom": timestamp_iso,
                            "dateTo": timestamp_iso,
                            "source": "appleWatch",
                            "deviceId": "watch_001",
                            "deviceName": "Apple Watch Series 8",
                            "metadata": {
                                "diastolic": 80
                            },  # Secondary value in metadata
                        }
                    ),
                }
            )

            # Steps data
            health_records.append(
                {
                    "elderly_user_id": user_id,
                    "timestamp": timestamp_iso,
                    "created_at": created_at,
                    "type": "steps",
                    "unit": "steps",
                    "encrypted_data": json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "type": "steps",
                            "value": 6000 + (days_ago * 500),
                            "unit": "steps",
                            "timestamp": timestamp_iso,
                            "dateFrom": timestamp_iso,
                            "dateTo": timestamp_iso,
                            "source": "appleWatch",
                            "deviceId": "watch_001",
                            "deviceName": "Apple Watch Series 8",
                            "metadata": {},
                        }
                    ),
                }
            )

            # Blood oxygen data
            health_records.append(
                {
                    "elderly_user_id": user_id,
                    "timestamp": timestamp_iso,
                    "created_at": created_at,
                    "type": "bloodOxygen",
                    "unit": "%",
                    "encrypted_data": json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "type": "bloodOxygen",
                            "value": 98,
                            "unit": "%",
                            "timestamp": timestamp_iso,
                            "dateFrom": timestamp_iso,
                            "dateTo": timestamp_iso,
                            "source": "appleWatch",
                            "deviceId": "watch_001",
                            "deviceName": "Apple Watch Series 8",
                            "metadata": {},
                        }
                    ),
                }
            )

            # Sleep deep data
            health_records.append(
                {
                    "elderly_user_id": user_id,
                    "timestamp": timestamp_iso,
                    "created_at": created_at,
                    "type": "sleepDeep",
                    "unit": "hours",
                    "encrypted_data": json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "type": "sleepDeep",
                            "value": 1.5,
                            "unit": "hours",
                            "timestamp": timestamp_iso,
                            "dateFrom": timestamp_iso,
                            "dateTo": timestamp_iso,
                            "source": "appleWatch",
                            "deviceId": "watch_001",
                            "deviceName": "Apple Watch Series 8",
                            "metadata": {},
                        }
                    ),
                }
            )

        return health_records

    @staticmethod
    def get_reminders(user_id: str = "test_user_123") -> List[Dict[str, Any]]:
        """Generate mock reminders for testing"""
        now = datetime.now()

        return [
            {
                "user_id": user_id,
                "reminder_id": "reminder_001",
                "title": "Take morning medication",
                "scheduled_date": now.strftime("%Y-%m-%d"),
                "scheduled_time": "09:00",
                "recurrence": "daily",
                "completed": False,
                "notes": "With breakfast",
            },
            {
                "user_id": user_id,
                "reminder_id": "reminder_002",
                "title": "Call my son",
                "scheduled_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
                "scheduled_time": "15:00",
                "recurrence": "once",
                "completed": False,
                "notes": "",
            },
            {
                "user_id": user_id,
                "reminder_id": "reminder_003",
                "title": "Doctor appointment",
                "scheduled_date": (now + timedelta(days=3)).strftime("%Y-%m-%d"),
                "scheduled_time": "10:30",
                "recurrence": "once",
                "completed": False,
                "notes": "Bring medication list",
            },
        ]
