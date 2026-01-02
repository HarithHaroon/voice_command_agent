"""
ClientTimeTracker - Maintains accurate client time throughout a session.

Tracks the offset between client and server time at connection,
then calculates accurate client time on demand.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ClientTimeTracker:
    """Tracks client time accurately throughout a session."""

    def __init__(self):
        self._client_time_at_connect: Optional[datetime] = None

        self._server_time_at_connect: Optional[datetime] = None

        self._timezone_offset_minutes: int = 0

        self._is_initialized: bool = False

    def initialize(self, client_time_iso: str, timezone_offset_minutes: int = 0):
        """
        Initialize with client time from session_init.

        Args:
            client_time_iso: Client's local time in ISO format (e.g., "2025-11-24T14:30:00")
            timezone_offset_minutes: Client's timezone offset from UTC in minutes
        """
        try:
            # Validate input - check if it's actually an ISO timestamp
            if (
                not client_time_iso
                or len(client_time_iso) < 10
                or "T" not in client_time_iso
            ):
                logger.warning(
                    f"Invalid client_time_iso format: '{client_time_iso}'. "
                    f"Expected ISO format like '2025-11-24T14:30:00'. Using server time instead."
                )
                # Fallback to server time
                now = datetime.now(timezone.utc)

                self._client_time_at_connect = now

                self._server_time_at_connect = now

                self._timezone_offset_minutes = 0

                self._is_initialized = True

                return

            # Parse ISO timestamp
            self._client_time_at_connect = datetime.fromisoformat(client_time_iso)

            self._server_time_at_connect = datetime.now(timezone.utc)  # ✅ Fixed

            self._timezone_offset_minutes = timezone_offset_minutes

            self._is_initialized = True

            logger.info(
                f"ClientTimeTracker initialized | "
                f"Client: {self._client_time_at_connect} | "
                f"Server: {self._server_time_at_connect} | "
                f"TZ offset: {timezone_offset_minutes} min"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ClientTimeTracker: {e}")
            # Fallback to server time
            now = datetime.now(timezone.utc)

            self._client_time_at_connect = now

            self._server_time_at_connect = now

            self._timezone_offset_minutes = 0

            self._is_initialized = False

    def get_current_client_time(self) -> datetime:
        """
        Get the accurate current client time.

        Returns:
            Current client local time
        """
        if not self._is_initialized:
            logger.warning("ClientTimeTracker not initialized, using server UTC time")

            return datetime.now(timezone.utc)

        # Calculate elapsed time since connection
        elapsed = datetime.now(timezone.utc) - self._server_time_at_connect

        # Add elapsed to original client time
        current_client_time = self._client_time_at_connect + elapsed

        return current_client_time

    def get_current_date_string(self) -> str:
        """Get current client date as YYYY-MM-DD string."""
        return self.get_current_client_time().strftime("%Y-%m-%d")

    def get_current_time_string(self) -> str:
        """Get current client time as HH:MM string."""
        return self.get_current_client_time().strftime("%H:%M")

    def get_current_datetime_iso(self) -> str:
        """Get current client datetime as ISO string."""
        return self.get_current_client_time().isoformat()

    def get_formatted_datetime(self) -> str:
        """Get human-readable datetime (e.g., 'Monday, November 24, 2025 at 2:30 PM')."""
        return self.get_current_client_time().strftime("%A, %B %d, %Y at %I:%M %p")

    def get_timezone_offset_minutes(self) -> int:
        """Get the client's timezone offset in minutes."""
        return self._timezone_offset_minutes

    def is_initialized(self) -> bool:
        """Check if tracker has been initialized."""
        return self._is_initialized

    def parse_relative_date(self, relative: str) -> str:
        """
        Parse relative date words to YYYY-MM-DD format.

        Args:
            relative: "today", "tomorrow", or day name like "Monday"

        Returns:
            Date string in YYYY-MM-DD format
        """
        current = self.get_current_client_time()

        relative_lower = relative.lower().strip()

        if relative_lower == "today":
            return current.strftime("%Y-%m-%d")

        elif relative_lower == "tomorrow":
            tomorrow = current + timedelta(days=1)

            return tomorrow.strftime("%Y-%m-%d")

        elif relative_lower in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            # Find next occurrence of this day
            day_names = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]

            target_day = day_names.index(relative_lower)

            current_day = current.weekday()

            days_ahead = target_day - current_day

            if days_ahead <= 0:  # Target day is today or in the past this week
                days_ahead += 7

            target_date = current + timedelta(days=days_ahead)

            return target_date.strftime("%Y-%m-%d")

        else:
            # Return as-is if not recognized (might already be a date)
            return relative

    def parse_timezone(tz_string: str):
        """
        Parse timezone from string (handles abbreviations like 'CAT').

        Args:
            tz_string: Timezone string (e.g., 'CAT', 'UTC', 'America/New_York')

        Returns:
            pytz timezone object
        """
        # Map common abbreviations to pytz timezones
        tz_map = {
            "CAT": "Africa/Johannesburg",  # Central Africa Time
            "EAT": "Africa/Nairobi",  # East Africa Time
            "WAT": "Africa/Lagos",  # West Africa Time
            "EST": "America/New_York",
            "PST": "America/Los_Angeles",
            "UTC": "UTC",
            "GMT": "GMT",
        }

        # Try abbreviation map first
        full_tz_name = tz_map.get(tz_string.upper(), tz_string)

        try:
            return pytz.timezone(full_tz_name)
        except Exception as e:
            logger.warning(f"Could not parse timezone '{tz_string}', using UTC: {e}")

            return pytz.UTC
