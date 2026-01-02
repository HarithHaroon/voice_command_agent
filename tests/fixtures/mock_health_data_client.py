"""
Mock Health Data Client for testing.
Returns test data instead of querying DynamoDB.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from tests.fixtures.test_data import TestDataFixtures

logger = logging.getLogger(__name__)


class MockHealthDataClient:
    """Mock health data client that returns test fixtures"""

    def __init__(self, user_id: str = "test_user_123"):
        self.user_id = user_id
        self.test_data = TestDataFixtures.get_health_data(user_id)
        logger.info(
            f"MockHealthDataClient initialized with {len(self.test_data)} records"
        )

    async def query_health_data(
        self,
        metric_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Query mock health data.

        Filters test data by metric type and date range.
        """
        logger.info(
            f"Querying mock health data: {metric_type}, {start_date} to {end_date}"
        )

        # Filter by metric type
        filtered = [r for r in self.test_data if r["type"] == metric_type]

        # Filter by date range if provided
        if start_date:
            filtered = [
                r
                for r in filtered
                if datetime.fromisoformat(r["timestamp"]) >= start_date
            ]

        if end_date:
            filtered = [
                r
                for r in filtered
                if datetime.fromisoformat(r["timestamp"]) <= end_date
            ]

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply limit
        result = filtered[:limit]

        logger.info(f"Mock query returned {len(result)} records")
        return result

    async def get_latest_metric(self, metric_type: str) -> Optional[Dict[str, Any]]:
        """Get latest value for a metric type"""
        results = await self.query_health_data(metric_type, limit=1)
        return results[0] if results else None

    async def get_metrics_for_period(
        self,
        metric_type: str,
        period: str,  # "today", "this_week", "this_month", "last_month"
    ) -> List[Dict[str, Any]]:
        """Get metrics for a specific period"""
        now = datetime.now()

        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == "this_week":
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == "this_month":
            start_date = now - timedelta(days=30)
            end_date = now
        elif period == "last_month":
            start_date = now - timedelta(days=60)
            end_date = now - timedelta(days=30)
        else:
            # Default to today
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now

        return await self.query_health_data(
            metric_type=metric_type, start_date=start_date, end_date=end_date
        )
