# SPDX-License-Identifier: MIT

from typing import Any, Literal, Optional, Union

import pendulum

from granular.model.entry import Entry
from granular.model.tracker import Tracker

GranularityType = Literal["day", "week", "month"]


def get_tracker_status_for_date(
    tracker: Tracker,
    entries: list[Entry],
    date: pendulum.Date,
) -> dict[str, Any]:
    """
    Get the status of a tracker for a specific date.
    Returns: {
        "has_entry": bool,
        "entry_count": int,  # For intra_day
        "entries": list[Entry],
        "total_value": Optional[float],  # Sum for quantitative
        "values": list[...],  # All values for the period
    }
    """
    # Get period boundaries for the date
    start, end = get_period_boundaries(tracker["entry_type"], date)

    # Filter entries within the period
    period_entries = [
        entry
        for entry in entries
        if entry["deleted"] is None
        and entry["tracker_id"] == tracker["id"]
        and start <= entry["timestamp"] < end
    ]

    # Calculate total value for quantitative trackers
    total_value: Optional[float] = None
    values: list[Union[int, float, str]] = []

    if tracker["value_type"] == "quantitative":
        total_value = 0.0
        for entry in period_entries:
            if entry["value"] is not None:
                if isinstance(entry["value"], (int, float)):
                    total_value += float(entry["value"])
                    values.append(entry["value"])
    elif tracker["value_type"] == "multi_select":
        for entry in period_entries:
            if entry["value"] is not None:
                values.append(entry["value"])

    return {
        "has_entry": len(period_entries) > 0,
        "entry_count": len(period_entries),
        "entries": period_entries,
        "total_value": total_value if total_value != 0 else None,
        "values": values,
    }


def get_period_boundaries(
    entry_type: str,
    reference: pendulum.DateTime | pendulum.Date,
) -> tuple[pendulum.DateTime, pendulum.DateTime]:
    """
    Get the start and end of the period for a given entry type and timestamp.
    Used for constraint checking and aggregation.
    """
    # Convert Date to DateTime if needed
    if isinstance(reference, pendulum.Date) and not isinstance(
        reference, pendulum.DateTime
    ):
        reference = pendulum.datetime(
            reference.year, reference.month, reference.day, tz="local"
        )

    local_time = reference.in_tz("local")

    if entry_type == "intra_day":
        # No period constraints for intra_day
        start = local_time.start_of("day")
        end = local_time.end_of("day").add(microseconds=1)
    elif entry_type == "daily":
        start = local_time.start_of("day")
        end = local_time.end_of("day").add(microseconds=1)
    elif entry_type == "weekly":
        start = local_time.start_of("week")
        end = local_time.end_of("week").add(microseconds=1)
    elif entry_type == "monthly":
        start = local_time.start_of("month")
        end = local_time.end_of("month").add(microseconds=1)
    elif entry_type == "quarterly":
        # Calculate quarter boundaries
        quarter = (local_time.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        start = local_time.set(month=quarter_start_month, day=1).start_of("day")
        # End of quarter is end of the third month
        end_month = quarter_start_month + 2
        end = local_time.set(month=end_month).end_of("month").add(microseconds=1)
    else:
        # Default to daily
        start = local_time.start_of("day")
        end = local_time.end_of("day").add(microseconds=1)

    return start.in_tz("UTC"), end.in_tz("UTC")


def get_tracker_heatmap_data(
    tracker: Tracker,
    entries: list[Entry],
    days: int = 14,
) -> list[dict[str, Any]]:
    """
    Generate heatmap data for the last N days.
    Returns list of {date, has_entry, entry_count, value, intensity}
    """
    today = pendulum.today("local")
    heatmap_data = []

    for i in range(days - 1, -1, -1):
        date = today.subtract(days=i)
        status = get_tracker_status_for_date(tracker, entries, date)

        # Calculate intensity (0-4) based on value type
        intensity = 0
        if status["has_entry"]:
            if tracker["value_type"] == "checkin":
                intensity = 4  # Binary: checked = full intensity
            elif tracker["value_type"] == "quantitative":
                # Scale intensity based on value if we have min/max
                intensity = 4  # Default to full if no scale defined
            elif tracker["value_type"] == "multi_select":
                if (
                    tracker["scale_min"] is not None
                    and tracker["scale_max"] is not None
                ):
                    # Scale intensity based on value within scale range
                    if status["values"] and isinstance(status["values"][0], int):
                        val = status["values"][0]
                        scale_range = tracker["scale_max"] - tracker["scale_min"]
                        if scale_range > 0:
                            intensity = int(
                                ((val - tracker["scale_min"]) / scale_range) * 4
                            )
                else:
                    intensity = 4
            elif tracker["value_type"] == "pips":
                # Pips: intensity based on total pip count (1-4 = levels, 5+ = max)
                total_pips = status["total_value"] or status["entry_count"]
                if total_pips >= 5:
                    intensity = 4
                elif total_pips >= 1:
                    intensity = max(1, min(4, int(total_pips)))
                else:
                    intensity = 1  # At least show something if has_entry

        heatmap_data.append(
            {
                "date": date,
                "has_entry": status["has_entry"],
                "entry_count": status["entry_count"],
                "total_value": status["total_value"],
                "values": status["values"],
                "intensity": intensity,
            }
        )

    return heatmap_data


def get_tracker_timeline_data(
    tracker: Tracker,
    entries: list[Entry],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
) -> list[dict[str, Any]]:
    """
    Generate timeline data for a tracker across given time slots.

    This generalizes get_tracker_heatmap_data to support day/week/month granularities
    and arbitrary time slot lists (as used by the gantt view).

    Args:
        tracker: The tracker to generate data for
        entries: All entries (will be filtered to this tracker)
        time_slots: List of DateTime representing the start of each time slot
        granularity: "day", "week", or "month"

    Returns:
        List of dicts, one per slot:
        {
            "slot": pendulum.DateTime,
            "has_entry": bool,
            "entry_count": int,
            "total_value": Optional[float],
            "values": list[...],
            "intensity": int (0-4),
        }
    """
    # Filter entries to this tracker
    tracker_entries = [
        e for e in entries if e["deleted"] is None and e["tracker_id"] == tracker["id"]
    ]

    timeline_data: list[dict[str, Any]] = []

    for slot in time_slots:
        # Determine period boundaries based on granularity
        slot_start, slot_end = _get_slot_boundaries(slot, granularity)

        # Filter entries within this slot's period
        period_entries = [
            entry
            for entry in tracker_entries
            if slot_start <= entry["timestamp"] < slot_end
        ]

        # Calculate total value for quantitative and pips trackers
        total_value: Optional[float] = None
        values: list[Union[int, float, str]] = []

        if tracker["value_type"] == "quantitative":
            total_value = 0.0
            for entry in period_entries:
                if entry["value"] is not None:
                    if isinstance(entry["value"], (int, float)):
                        total_value += float(entry["value"])
                        values.append(entry["value"])
            if total_value == 0:
                total_value = None
        elif tracker["value_type"] == "multi_select":
            for entry in period_entries:
                if entry["value"] is not None:
                    values.append(entry["value"])
        elif tracker["value_type"] == "pips":
            # Pips: sum up pip values (each entry value is pip count, default 1)
            total_value = 0.0
            for entry in period_entries:
                if entry["value"] is not None and isinstance(
                    entry["value"], (int, float)
                ):
                    total_value += float(entry["value"])
                    values.append(entry["value"])
                else:
                    # Default to 1 pip per entry if no value
                    total_value += 1.0
                    values.append(1)
            if total_value == 0:
                total_value = None

        # Calculate intensity (0-4) based on value type
        intensity = 0
        has_entry = len(period_entries) > 0

        if has_entry:
            if tracker["value_type"] == "checkin":
                intensity = 4  # Binary: checked = full intensity
            elif tracker["value_type"] == "quantitative":
                intensity = 4  # Default to full if no scale defined
            elif tracker["value_type"] == "multi_select":
                if (
                    tracker["scale_min"] is not None
                    and tracker["scale_max"] is not None
                ):
                    # Scale intensity based on value within scale range
                    if values and isinstance(values[0], int):
                        val = values[0]
                        scale_range = tracker["scale_max"] - tracker["scale_min"]
                        if scale_range > 0:
                            intensity = int(
                                ((val - tracker["scale_min"]) / scale_range) * 4
                            )
                else:
                    intensity = 4
            elif tracker["value_type"] == "pips":
                # Pips: intensity based on total pip count (1-4 = levels, 5+ = max)
                total_pips = total_value or len(period_entries)
                if total_pips >= 5:
                    intensity = 4
                elif total_pips >= 1:
                    intensity = max(1, min(4, int(total_pips)))
                else:
                    intensity = 1  # At least show something if has_entry

        timeline_data.append(
            {
                "slot": slot,
                "has_entry": has_entry,
                "entry_count": len(period_entries),
                "total_value": total_value,
                "values": values,
                "intensity": intensity,
            }
        )

    return timeline_data


def _get_slot_boundaries(
    slot: pendulum.DateTime,
    granularity: GranularityType,
) -> tuple[pendulum.DateTime, pendulum.DateTime]:
    """
    Get the start and end boundaries for a time slot based on granularity.

    Args:
        slot: The start of the time slot
        granularity: "day", "week", or "month"

    Returns:
        Tuple of (start, end) as UTC DateTimes
    """
    local_time = slot.in_tz("local")

    if granularity == "day":
        start = local_time.start_of("day")
        end = local_time.end_of("day").add(microseconds=1)
    elif granularity == "week":
        start = local_time.start_of("week")
        end = local_time.end_of("week").add(microseconds=1)
    else:  # granularity == "month"
        start = local_time.start_of("month")
        end = local_time.end_of("month").add(microseconds=1)

    return start.in_tz("UTC"), end.in_tz("UTC")


def get_tracker_summary(
    tracker: Tracker,
    entries: list[Entry],
    start_date: pendulum.Date,
    end_date: pendulum.Date,
) -> dict[str, Any]:
    """
    Generate summary statistics for a date range.
    Returns: {
        "total_entries": int,
        "days_with_entries": int,
        "values": list[...],  # For quantitative/multi_select
        "entries_by_date": dict[date, list[Entry]],
    }
    """
    entries_by_date: dict[str, list[Entry]] = {}
    all_values: list[Union[int, float, str]] = []
    total_entries = 0
    days_with_entries = 0

    current_date = start_date
    while current_date <= end_date:
        status = get_tracker_status_for_date(tracker, entries, current_date)
        date_str = current_date.to_date_string()

        if status["has_entry"]:
            days_with_entries += 1
            total_entries += status["entry_count"]
            entries_by_date[date_str] = status["entries"]
            all_values.extend(status["values"])
        else:
            entries_by_date[date_str] = []

        current_date = current_date.add(days=1)

    return {
        "total_entries": total_entries,
        "days_with_entries": days_with_entries,
        "values": all_values,
        "entries_by_date": entries_by_date,
    }
