# SPDX-License-Identifier: MIT

import os
import re
import subprocess
import tempfile
from typing import Optional

import pendulum
import typer

from granular.time import datetime_from_str_utc


def parse_datetime(datetime_param: Optional[str | int]) -> Optional[pendulum.DateTime]:
    if datetime_param is None:
        return None

    datetime = str(datetime_param)

    # Match YYYY-MM-DD format (with optional time component)
    if re.match(r"\d{4}-\d{2}-\d{2}", datetime):
        return datetime_from_str_utc(datetime)

    # Match (H)H:mm format (time only, use today's date)
    time_match = re.match(r"^(\d{1,2}):(\d{2})$", datetime)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))

        # Validate hour and minute ranges
        if hour < 0 or hour > 23:
            raise typer.BadParameter(f"Hour must be between 0 and 23, got {hour}")
        if minute < 0 or minute > 59:
            raise typer.BadParameter(f"Minute must be between 0 and 59, got {minute}")

        # Create datetime with today's date in local timezone, then convert to UTC
        pendulum_date_time = pendulum.today("local").set(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        pendulum_date_time = pendulum_date_time.in_tz("UTC")
        return pendulum_date_time

    # Match numeric input for relative days (e.g., "1", "-1", "365")
    if re.match(r"^-?\d+$", datetime):
        try:
            days_offset = int(datetime)
            pendulum_date_time = pendulum.today().add(days=days_offset).start_of("day")
            pendulum_date_time = pendulum_date_time.in_tz("UTC")
            return pendulum_date_time
        except Exception as e:
            raise typer.BadParameter(f"Invalid day offset: {e}")

    if datetime == "now" or datetime == "n":
        pendulum_date_time = pendulum.now()
        pendulum_date_time = pendulum_date_time.in_tz("UTC")
        return pendulum_date_time
    if datetime == "today" or datetime == "t":
        pendulum_date_time = pendulum.today().start_of("day")
        pendulum_date_time = pendulum_date_time.in_tz("UTC")
        return pendulum_date_time
    if datetime == "yesterday" or datetime == "y":
        pendulum_date_time = pendulum.yesterday().start_of("day")
        pendulum_date_time = pendulum_date_time.in_tz("UTC")
        return pendulum_date_time
    if datetime == "tomorrow" or datetime == "o":
        pendulum_date_time = pendulum.tomorrow().start_of("day")
        pendulum_date_time = pendulum_date_time.in_tz("UTC")
        return pendulum_date_time
    raise typer.BadParameter("Incorrect datetime format")


def parse_time(time_str: Optional[str]) -> Optional[tuple[int, int]]:
    """
    Parse a time string in (H)H:mm format and return a tuple of (hour, minute).

    Args:
        time_str: Time string in format like "8:00", "17:30", etc.

    Returns:
        Tuple of (hour, minute) or None if time_str is None

    Raises:
        typer.BadParameter: If the time format is invalid or values are out of range
    """
    if time_str is None:
        return None

    # Match (H)H:mm format
    time_match = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if not time_match:
        raise typer.BadParameter(
            f"Time must be in HH:mm format (e.g., 8:00 or 17:30), got '{time_str}'"
        )

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))

    # Validate hour and minute ranges
    if hour < 0 or hour > 23:
        raise typer.BadParameter(f"Hour must be between 0 and 23, got {hour}")
    if minute < 0 or minute > 59:
        raise typer.BadParameter(f"Minute must be between 0 and 59, got {minute}")

    return (hour, minute)


def parse_id_list(id_param: str) -> list[int]:
    """
    Parse a single ID, comma-separated list of IDs, or ranges of IDs.

    Args:
        id_param: A single ID (e.g., "1"), comma-separated list (e.g., "1,2,3"),
                  range (e.g., "1-5"), or mixed (e.g., "1,3-5,8")

    Returns:
        List of integer IDs (sorted and deduplicated)

    Raises:
        typer.BadParameter: If any ID is not a valid integer or range format is invalid
    """
    # Split by comma and strip whitespace
    id_strings = [s.strip() for s in id_param.split(",")]

    # Convert to integers, handling ranges
    ids: list[int] = []
    for id_str in id_strings:
        if not id_str:
            continue

        # Check if it's a range (contains hyphen)
        if "-" in id_str:
            # Parse range format: "start-end"
            range_parts = id_str.split("-")
            if len(range_parts) != 2:
                raise typer.BadParameter(
                    f"Invalid range format: '{id_str}' (expected format: 'start-end')"
                )

            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                raise typer.BadParameter(
                    f"Invalid range: '{id_str}' contains non-integer values"
                )

            # Validate range
            if start > end:
                raise typer.BadParameter(
                    f"Invalid range: '{id_str}' (start must be <= end)"
                )

            # Add all IDs in range (inclusive)
            ids.extend(range(start, end + 1))
        else:
            # Single ID
            try:
                ids.append(int(id_str))
            except ValueError:
                raise typer.BadParameter(
                    f"Invalid ID: '{id_str}' is not a valid integer"
                )

    if len(ids) == 0:
        raise typer.BadParameter("No valid IDs provided")

    # Remove duplicates and sort
    return sorted(set(ids))


def open_editor_for_text(initial_text: Optional[str] = None) -> Optional[str]:
    """
    Open the user's preferred editor to edit note text.
    Returns the edited text with trailing newlines removed, or None if empty.
    """
    # Get the editor from environment, default to nano
    editor = os.environ.get("EDITOR", "nano")

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt") as tf:
        # Write initial text if provided
        if initial_text is not None:
            tf.write(initial_text)
            tf.flush()

        subprocess.run([editor, tf.name], check=True)
        tf.seek(0)
        text = tf.read()
        if not text.strip():
            return None
        # Remove trailing newlines but preserve internal empty lines
        return text.rstrip("\n")
