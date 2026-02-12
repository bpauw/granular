# SPDX-License-Identifier: MIT

from typing import Any, Literal, Optional, Union

import pendulum

from granular.model.entry import Entry
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.tracker import Tracker

GranularityType = Literal["day", "week", "month"]


def get_slot_boundaries(
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


def get_tracker_timeline_data(
    tracker: Tracker,
    entries: list[Entry],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
) -> list[dict[str, Any]]:
    """
    Generate timeline data for a tracker across given time slots.

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
        slot_start, slot_end = get_slot_boundaries(slot, granularity)

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


def get_tasks_timeline_data(
    tasks: list[Task],
    time_audits: list[TimeAudit],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
) -> list[dict[str, Any]]:
    """
    Generate timeline data for tasks and time audits across given time slots.

    A slot has activity if:
    - A task was completed on that date (task["completed"] falls within the slot)
    - A time audit exists for that date (time_audit["start"] falls within the slot)

    Args:
        tasks: List of tasks (should be pre-filtered for deleted)
        time_audits: List of time audits (should be pre-filtered for deleted)
        time_slots: List of DateTime representing the start of each time slot
        granularity: "day", "week", or "month"

    Returns:
        List of dicts, one per slot:
        {
            "slot": pendulum.DateTime,
            "has_entry": bool,
            "completed_task_count": int,
            "time_audit_count": int,
            "total_count": int,
            "intensity": int (0-4),
        }
    """
    timeline_data: list[dict[str, Any]] = []

    for slot in time_slots:
        slot_start, slot_end = get_slot_boundaries(slot, granularity)

        # Count tasks completed in this slot
        completed_task_count = 0
        for task in tasks:
            if task["completed"] is not None:
                # Convert to UTC for comparison
                completed_utc = task["completed"].in_tz("UTC")
                if slot_start <= completed_utc < slot_end:
                    completed_task_count += 1

        # Count time audits that started in this slot
        time_audit_count = 0
        for time_audit in time_audits:
            if time_audit["start"] is not None:
                start_utc = time_audit["start"].in_tz("UTC")
                if slot_start <= start_utc < slot_end:
                    time_audit_count += 1

        total_count = completed_task_count + time_audit_count
        has_entry = total_count > 0

        # Calculate intensity (0-4) based on activity count
        intensity = 0
        if has_entry:
            if total_count >= 5:
                intensity = 4
            elif total_count >= 3:
                intensity = 3
            elif total_count >= 2:
                intensity = 2
            else:
                intensity = 1

        timeline_data.append(
            {
                "slot": slot,
                "has_entry": has_entry,
                "completed_task_count": completed_task_count,
                "time_audit_count": time_audit_count,
                "total_count": total_count,
                "intensity": intensity,
            }
        )

    return timeline_data
