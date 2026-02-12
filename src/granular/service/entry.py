# SPDX-License-Identifier: MIT

from typing import Optional, Union

import pendulum

from granular.model.entry import Entry
from granular.model.tracker import Tracker
from granular.service.tracker import get_period_boundaries
from granular.template.entry import get_entry_template
from granular.time import now_utc


class EntryValidationError(Exception):
    """Raised when entry validation fails."""

    pass


def validate_entry_allowed(
    tracker: Tracker,
    timestamp: pendulum.DateTime,
    existing_entries: list[Entry],
) -> bool:
    """
    Check if a new entry is allowed based on entry_type constraints.

    - intra_day: Always allowed
    - daily: Max 1 per calendar day
    - weekly: Max 1 per calendar week (Mon-Sun)
    - monthly: Max 1 per calendar month
    - quarterly: Max 1 per calendar quarter

    Returns True if entry is allowed, raises EntryValidationError if not.
    """
    entry_type = tracker["entry_type"]

    # intra_day allows unlimited entries
    if entry_type == "intra_day":
        return True

    # Get period boundaries
    start, end = get_period_boundaries(entry_type, timestamp)

    # Check if any non-deleted entry exists in this period for this tracker
    for entry in existing_entries:
        if (
            entry["deleted"] is None
            and entry["tracker_id"] == tracker["id"]
            and start <= entry["timestamp"] < end
        ):
            period_name = {
                "daily": "day",
                "weekly": "week",
                "monthly": "month",
                "quarterly": "quarter",
            }.get(entry_type, "period")
            raise EntryValidationError(
                f"An entry already exists for this {period_name}. "
                f"Tracker '{tracker['name']}' allows only one entry per {period_name}."
            )

    return True


def validate_entry_value(
    tracker: Tracker,
    value: Optional[Union[int, float, str]],
) -> bool:
    """
    Validate that the value matches the tracker's value_type.

    - checkin: value should be None
    - quantitative: value should be int or float
    - multi_select with scale: value should be int within scale_min..scale_max
    - multi_select with options: value should be str in options list
    - pips: value should be a positive integer

    Returns True if valid, raises EntryValidationError if not.
    """
    value_type = tracker["value_type"]

    if value_type == "checkin":
        if value is not None:
            raise EntryValidationError(
                f"Checkin trackers should not have a value. Got: {value}"
            )
        return True

    elif value_type == "quantitative":
        if value is None:
            raise EntryValidationError("Quantitative trackers require a numeric value.")
        if not isinstance(value, (int, float)):
            raise EntryValidationError(
                f"Quantitative trackers require a numeric value. Got: {type(value).__name__}"
            )
        return True

    elif value_type == "pips":
        if value is None:
            raise EntryValidationError("Pips trackers require an integer value.")
        if not isinstance(value, int):
            raise EntryValidationError(
                f"Pips trackers require an integer value. Got: {type(value).__name__}"
            )
        if value < 1:
            raise EntryValidationError(
                f"Pips value must be a positive integer (>= 1). Got: {value}"
            )
        return True

    elif value_type == "multi_select":
        if value is None:
            raise EntryValidationError("Multi-select trackers require a value.")

        # Check if using numeric scale
        if tracker["scale_min"] is not None and tracker["scale_max"] is not None:
            if not isinstance(value, int):
                raise EntryValidationError(
                    f"Scale-based multi-select requires an integer value. Got: {type(value).__name__}"
                )
            if not (tracker["scale_min"] <= value <= tracker["scale_max"]):
                raise EntryValidationError(
                    f"Value {value} is outside the scale range "
                    f"({tracker['scale_min']}-{tracker['scale_max']})."
                )
            return True

        # Check if using named options
        if tracker["options"] is not None:
            if not isinstance(value, str):
                raise EntryValidationError(
                    f"Option-based multi-select requires a string value. Got: {type(value).__name__}"
                )
            if value not in tracker["options"]:
                raise EntryValidationError(
                    f"Value '{value}' is not a valid option. "
                    f"Valid options: {', '.join(tracker['options'])}"
                )
            return True

        raise EntryValidationError(
            "Multi-select tracker has no scale or options defined."
        )

    raise EntryValidationError(f"Unknown value_type: {value_type}")


def create_entry_for_tracker(
    tracker: Tracker,
    timestamp: Optional[pendulum.DateTime],
    value: Optional[Union[int, float, str]],
    add_tags: Optional[list[str]] = None,
) -> Entry:
    """
    Create an entry, inheriting project/tags/color from tracker and active context.
    """
    entry = get_entry_template()

    # Set tracker reference
    if tracker["id"] is None:
        raise ValueError("Tracker must have an ID")
    entry["tracker_id"] = tracker["id"]

    # Set timestamp
    entry["timestamp"] = timestamp if timestamp is not None else now_utc()

    # Set value
    entry["value"] = value

    # Inherit from tracker
    entry["project"] = tracker["project"]
    entry["color"] = tracker["color"]

    # Handle tags: inherit from tracker and add additional tags
    entry_tags = tracker["tags"] if tracker["tags"] is not None else []
    entry_tags = list(entry_tags)  # Make a copy

    if add_tags is not None:
        for tag in add_tags:
            if tag not in entry_tags:
                entry_tags.append(tag)

    entry["tags"] = entry_tags if len(entry_tags) > 0 else None

    return entry


def parse_entry_value(
    tracker: Tracker,
    value_str: Optional[str],
) -> Optional[Union[int, float, str]]:
    """
    Parse a string value into the appropriate type based on tracker's value_type.
    """
    if value_str is None:
        return None

    value_type = tracker["value_type"]

    if value_type == "checkin":
        return None

    elif value_type == "quantitative":
        # Try to parse as int first, then float
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                raise EntryValidationError(
                    f"Cannot parse '{value_str}' as a number for quantitative tracker."
                )

    elif value_type == "pips":
        # Parse as integer for pips
        try:
            return int(value_str)
        except ValueError:
            raise EntryValidationError(
                f"Cannot parse '{value_str}' as an integer for pips tracker."
            )

    elif value_type == "multi_select":
        # If scale-based, parse as int
        if tracker["scale_min"] is not None and tracker["scale_max"] is not None:
            try:
                return int(value_str)
            except ValueError:
                raise EntryValidationError(
                    f"Cannot parse '{value_str}' as an integer for scale-based tracker."
                )
        # If option-based, keep as string
        if tracker["options"] is not None:
            return value_str

    return value_str
