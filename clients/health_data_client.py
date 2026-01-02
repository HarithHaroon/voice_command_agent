"""
Health Data Client - Handles encrypted health data from DynamoDB.
"""

import os
import json
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env.secrets")

logger = logging.getLogger(__name__)


class HealthDataClient:
    """Client for reading and decrypting health data from DynamoDB."""

    TABLE_NAME = "health_data"
    IV_KEY = "aBcDeFgHiJkLmNoP"  # Static IV from Dart code

    def __init__(self, dynamodb_resource=None):
        """Initialize HealthDataClient."""
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
        self._encryption_key = None
        self._lambda_url = os.getenv("HEALTH_ENCRYPTION_LAMBDA_URL")

        logger.info(f"HealthDataClient initialized with table: {self.TABLE_NAME}")

    def _get_encryption_key(self) -> str:
        """
        Get encryption key from Lambda function.
        Caches the key to avoid repeated Lambda calls.
        """
        if self._encryption_key:
            return self._encryption_key

        if not self._lambda_url:
            raise ValueError(
                "HEALTH_ENCRYPTION_LAMBDA_URL not set in environment variables"
            )

        try:
            response = requests.get(self._lambda_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            self._encryption_key = data.get("key")

            if not self._encryption_key:
                raise ValueError("No encryption key in Lambda response")

            logger.info("✅ Encryption key retrieved from Lambda")
            return self._encryption_key

        except Exception as e:
            logger.error(f"Failed to get encryption key from Lambda: {e}")
            raise

    def _decrypt_data(self, encrypted_base64: str, encryption_key: str) -> dict:
        """
        Decrypt health data using AES-CTR encryption (matching Dart's default).

        Args:
            encrypted_base64: Base64-encoded encrypted data
            encryption_key: Encryption key from Lambda

        Returns:
            Decrypted data as dictionary
        """
        try:
            from cryptography.hazmat.primitives.ciphers import modes

            # Prepare key and IV
            key = encryption_key.encode("utf-8")
            iv = self.IV_KEY.encode("utf-8")

            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_base64)

            # Create cipher with CTR mode
            cipher = Cipher(
                algorithms.AES(key), modes.CTR(iv), backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            decrypted_bytes = decryptor.update(encrypted_bytes) + decryptor.finalize()

            # 🆕 Strip trailing null bytes and whitespace
            decrypted_bytes = decrypted_bytes.rstrip(
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
            )
            decrypted_bytes = decrypted_bytes.rstrip()

            # Parse JSON
            decrypted_json = decrypted_bytes.decode("utf-8")

            # 🆕 Find where JSON actually ends
            # Sometimes there's garbage after the closing }
            try:
                # Try to parse as-is first
                return json.loads(decrypted_json)
            except json.JSONDecodeError as e:
                # If it fails, try to find the last valid JSON object
                logger.warning(
                    f"JSON has extra data, attempting to extract valid JSON: {e}"
                )

                # Find the last closing brace
                last_brace = decrypted_json.rfind("}")
                if last_brace != -1:
                    clean_json = decrypted_json[: last_brace + 1]
                    return json.loads(clean_json)
                else:
                    raise

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed: {e}")
            logger.error(f"Decrypted string (first 500 chars): {decrypted_json[:500]}")
            logger.error(f"Decrypted string (last 100 chars): {decrypted_json[-100:]}")
            raise
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def get_health_data(
        self,
        user_id: str,
        hours_back: int = 24,
        metric_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get health data for a user within a timeframe.

        Args:
            user_id: Elderly user ID
            hours_back: How many hours of data to retrieve
            metric_type: Optional filter by type (heartRate, steps, etc.)

        Returns:
            List of decrypted health data items, each containing:
            {id, type, value, unit, timestamp, dateFrom, dateTo,
             source, deviceId, deviceName, metadata}
        """
        try:
            # Get encryption key
            encryption_key = self._get_encryption_key()

            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours_back)

            # Query DynamoDB
            query_params = {
                "KeyConditionExpression": Key("elderly_user_id").eq(user_id)
                & Key("timestamp").between(start_time.isoformat(), end_time.isoformat())
            }

            # Add type filter if specified
            if metric_type:
                from boto3.dynamodb.conditions import Attr

                query_params["FilterExpression"] = Attr("type").eq(metric_type)

            response = self.table.query(**query_params)
            items = response.get("Items", [])

            logger.info(
                f"Retrieved {len(items)} health records for user {user_id} "
                f"(last {hours_back} hours)"
            )

            # Decrypt each item
            decrypted_items = []
            for item in items:
                try:
                    decrypted_data = self._decrypt_data(
                        item["encrypted_data"], encryption_key
                    )
                    decrypted_items.append(decrypted_data)

                except Exception as e:
                    logger.error(f"Failed to decrypt item {item.get('timestamp')}: {e}")
                    continue

            # Sort by timestamp descending (most recent first)
            decrypted_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            return decrypted_items

        except ClientError as e:
            logger.error(f"DynamoDB query failed: {e}")
            raise

    def get_latest_metric(
        self, user_id: str, metric_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent value for a specific metric.

        Args:
            user_id: Elderly user ID
            metric_type: Type of metric (heartRate, steps, etc.)

        Returns:
            Latest metric data or None
        """
        data = self.get_health_data(user_id, hours_back=24, metric_type=metric_type)

        if not data:
            return None

        # Return most recent (already sorted)
        return data[0]

    def get_aggregated_metrics(
        self, user_id: str, hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Get aggregated health metrics for analysis.

        Args:
            user_id: Elderly user ID
            hours_back: Hours of data to analyze

        Returns:
            Dictionary with aggregated metrics by type:
            {
                'heartRate': {
                    'latest': 75,
                    'average': 72,
                    'min': 65,
                    'max': 85,
                    'count': 20,
                    'unit': 'BEATS_PER_MINUTE'
                },
                ...
            }
        """
        all_data = self.get_health_data(user_id, hours_back=hours_back)

        # Group by type
        metrics_by_type = {}
        for item in all_data:
            metric_type = item.get("type")
            if metric_type not in metrics_by_type:
                metrics_by_type[metric_type] = []
            metrics_by_type[metric_type].append(item)

        # Calculate aggregations
        aggregated = {}
        for metric_type, items in metrics_by_type.items():
            values = [
                item.get("value") for item in items if item.get("value") is not None
            ]

            if values:
                aggregated[metric_type] = {
                    "latest": values[0],  # Most recent (already sorted)
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "unit": items[0].get("unit", ""),
                    "source": items[0].get("source", ""),
                }

        logger.info(f"Aggregated {len(aggregated)} metric types")
        return aggregated

    def get_aggregated_metrics_by_date(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get aggregated health metrics for a specific date range.

        Args:
            user_id: Elderly user ID
            start_date: Start datetime
            end_date: End datetime

        Returns:
            Dictionary with aggregated metrics by type
        """
        try:
            # Get encryption key
            encryption_key = self._get_encryption_key()

            # Query DynamoDB with absolute date range
            query_params = {
                "KeyConditionExpression": Key("elderly_user_id").eq(user_id)
                & Key("timestamp").between(start_date.isoformat(), end_date.isoformat())
            }

            response = self.table.query(**query_params)
            items = response.get("Items", [])

            logger.info(
                f"Retrieved {len(items)} health records for user {user_id} "
                f"between {start_date.date()} and {end_date.date()}"
            )

            # Decrypt each item
            decrypted_items = []
            for item in items:
                try:
                    decrypted_data = self._decrypt_data(
                        item["encrypted_data"], encryption_key
                    )
                    decrypted_items.append(decrypted_data)

                except Exception as e:
                    logger.error(f"Failed to decrypt item {item.get('timestamp')}: {e}")
                    continue

            # Sort by timestamp descending (most recent first)
            decrypted_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Group by type
            metrics_by_type = {}
            for item in decrypted_items:
                metric_type = item.get("type")
                if metric_type not in metrics_by_type:
                    metrics_by_type[metric_type] = []
                metrics_by_type[metric_type].append(item)

            # Calculate aggregations
            aggregated = {}
            for metric_type, items in metrics_by_type.items():
                values = [
                    item.get("value") for item in items if item.get("value") is not None
                ]

                if values:
                    aggregated[metric_type] = {
                        "latest": values[0],  # Most recent
                        "average": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                        "unit": items[0].get("unit", ""),
                        "source": items[0].get("source", ""),
                    }

            logger.info(f"Aggregated {len(aggregated)} metric types")
            return aggregated

        except ClientError as e:
            logger.error(f"DynamoDB query failed: {e}")
            raise

    def get_health_data_by_date(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        metric_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get health data for a specific date range.

        Args:
            user_id: Elderly user ID
            start_date: Start datetime
            end_date: End datetime
            metric_type: Optional filter by type

        Returns:
            List of decrypted health data items
        """
        try:
            # Get encryption key
            encryption_key = self._get_encryption_key()

            # Query DynamoDB
            query_params = {
                "KeyConditionExpression": Key("elderly_user_id").eq(user_id)
                & Key("timestamp").between(start_date.isoformat(), end_date.isoformat())
            }

            # Add type filter if specified
            if metric_type:
                from boto3.dynamodb.conditions import Attr

                query_params["FilterExpression"] = Attr("type").eq(metric_type)

            response = self.table.query(**query_params)
            items = response.get("Items", [])

            logger.info(
                f"Retrieved {len(items)} health records for user {user_id} "
                f"between {start_date.date()} and {end_date.date()}"
            )

            # Decrypt each item
            decrypted_items = []
            for item in items:
                try:
                    decrypted_data = self._decrypt_data(
                        item["encrypted_data"], encryption_key
                    )
                    decrypted_items.append(decrypted_data)

                except Exception as e:
                    logger.error(f"Failed to decrypt item {item.get('timestamp')}: {e}")
                    continue

            # Sort by timestamp descending
            decrypted_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            return decrypted_items

        except ClientError as e:
            logger.error(f"DynamoDB query failed: {e}")
            raise
