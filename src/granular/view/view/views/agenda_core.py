# SPDX-License-Identifier: MIT

"""
Shared rendering logic for agenda-style day-by-day views.

This module contains the core rendering functions used by both the agenda view
and the story view. It handles:
- Day header rendering with date styling
- Entity display formatting (tasks, events, timespans, time audits, logs, notes, entries)
- Chronological item sorting within days
"""

from typing import Optional

import pendulum
from rich.console import Console
from rich.text import Text

from granular.color import (
    COMPLETED_TASK_COLOR,
    LOG_META_COLOR,
    NOTE_META_COLOR,
    TIME_AUDIT_META_COLOR,
)
from granular.model.entity_id import EntityId
from granular.model.entry import Entry
from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.model.tracker import Tracker
from granular.repository.id_map import ID_MAP_REPO
from granular.view.view.util import is_task_completed, task_state


def filter_audits_for_day(
    time_audits: list[TimeAudit], date: pendulum.DateTime
) -> list[TimeAudit]:
    """
    Filter time audits to only those that overlap with the specified date.

    Args:
        time_audits: List of all time audits
        date: The date to filter for (should be start of day in local timezone)

    Returns:
        List of time audits that overlap with the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_audits = []
    for audit in time_audits:
        if audit["start"] is None or audit["deleted"] is not None:
            continue

        audit_start = audit["start"].in_tz("local")
        audit_end = audit["end"].in_tz("local") if audit["end"] is not None else None

        # Include audit if it overlaps with the day
        if audit_end is None:
            # Open-ended audit
            if audit_start <= day_end:
                filtered_audits.append(audit)
        elif audit_start <= day_end and audit_end >= day_start:
            filtered_audits.append(audit)

    return filtered_audits


def filter_events_for_day(events: list[Event], date: pendulum.DateTime) -> list[Event]:
    """
    Filter events to only those that overlap with the specified date.

    Args:
        events: List of all events
        date: The date to filter for (should be start of day in local timezone)

    Returns:
        List of events that overlap with the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_events = []
    for event in events:
        if event["deleted"] is not None:
            continue

        event_start = event["start"]

        # Handle all-day events
        if event["all_day"]:
            # All-day events are stored at midnight UTC for the intended date
            # Compare the UTC date with the UTC version of the requested local date
            event_start_utc_day = event_start.start_of("day")
            day_start_utc = day_start.in_tz("UTC").start_of("day")
            if event_start_utc_day == day_start_utc:
                filtered_events.append(event)
        else:
            # Timed events - convert to local for comparison
            event_start_local = event_start.in_tz("local")
            event_end_local = (
                event["end"].in_tz("local")
                if event["end"] is not None
                else event_start_local.add(hours=1)
            )

            # Include event if it overlaps with the day
            if event_start_local <= day_end and event_end_local >= day_start:
                filtered_events.append(event)

    return filtered_events


def filter_entries_for_day(
    entries: list[Entry], date: pendulum.DateTime
) -> list[Entry]:
    """
    Filter tracker entries to only those that occurred on the specified date.

    Args:
        entries: List of all entries
        date: The date to filter for (should be start of day in local timezone)

    Returns:
        List of entries that occurred on the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_entries = []
    for entry in entries:
        if entry["deleted"] is not None:
            continue

        # Convert entry timestamp to local timezone for comparison
        entry_timestamp = entry["timestamp"].in_tz("local")

        # Include entry if its timestamp is within the day
        if entry_timestamp >= day_start and entry_timestamp <= day_end:
            filtered_entries.append(entry)

    return filtered_entries


def filter_active_timespans_for_day(
    timespans: list[Timespan], date: pendulum.DateTime
) -> list[Timespan]:
    """
    Filter timespans to only those that are currently active on the specified date.
    A timespan is active on a day if:
    1. It has no end time (ongoing) and started on or before the day, OR
    2. It has start and end times that overlap with the day

    Args:
        timespans: List of all timespans
        date: The date to filter for (should be start of day in local timezone)

    Returns:
        List of active timespans that overlap with the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_timespans: list[Timespan] = []
    for timespan in timespans:
        if timespan["start"] is None or timespan["deleted"] is not None:
            continue

        # Convert start to local timezone
        timespan_start = timespan["start"].in_tz("local")

        # Case 1: Ongoing timespan (no end time)
        if timespan["end"] is None:
            # Include if it started on or before this day
            if timespan_start <= day_end:
                filtered_timespans.append(timespan)
        # Case 2: Timespan with both start and end
        else:
            timespan_end = timespan["end"].in_tz("local")
            # Include if the timespan overlaps with this day
            if timespan_start <= day_end and timespan_end >= day_start:
                filtered_timespans.append(timespan)

    return filtered_timespans


def filter_tasks_for_scheduled_or_due(
    tasks: list[Task],
    date: pendulum.DateTime,
    include_scheduled: bool = True,
    include_due: bool = True,
) -> list[Task]:
    """
    Filter tasks to only those that have a scheduled or due date on the specified date.

    Args:
        tasks: List of all tasks
        date: The date to filter for (should be start of day in local timezone)
        include_scheduled: Whether to include tasks with scheduled dates
        include_due: Whether to include tasks with due dates

    Returns:
        List of tasks with scheduled or due date on the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_tasks = []
    for task in tasks:
        if task["deleted"] is not None:
            continue

        # Check scheduled date
        if include_scheduled and task["scheduled"] is not None:
            task_scheduled_local = task["scheduled"].in_tz("local").start_of("day")
            if task_scheduled_local >= day_start and task_scheduled_local <= day_end:
                filtered_tasks.append(task)
                continue

        # Check due date
        if include_due and task["due"] is not None:
            task_due_local = task["due"].in_tz("local").start_of("day")
            if task_due_local >= day_start and task_due_local <= day_end:
                filtered_tasks.append(task)

    return filtered_tasks


def filter_logs_for_day(logs: list[Log], date: pendulum.DateTime) -> list[Log]:
    """
    Filter logs that occurred on the given day.

    Args:
        logs: List of all logs
        date: The day to filter for

    Returns:
        List of logs that occurred on the given day, sorted by timestamp
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered = []
    for log in logs:
        if log["timestamp"] is not None:
            log_time_local = log["timestamp"].in_tz("local")
            if day_start <= log_time_local <= day_end:
                filtered.append(log)

    # Sort by timestamp
    filtered.sort(
        key=lambda log: log["timestamp"]
        if log["timestamp"] is not None
        else pendulum.datetime(1970, 1, 1)
    )

    return filtered


def filter_notes_for_day(notes: list[Note], date: pendulum.DateTime) -> list[Note]:
    """
    Filter notes that occurred on the given day.

    Args:
        notes: List of all notes
        date: The day to filter for

    Returns:
        List of notes that occurred on the given day, sorted by timestamp
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered = []
    for note in notes:
        if note["timestamp"] is not None:
            note_time_local = note["timestamp"].in_tz("local")
            if day_start <= note_time_local <= day_end:
                filtered.append(note)

    # Sort by timestamp
    filtered.sort(
        key=lambda note: note["timestamp"]
        if note["timestamp"] is not None
        else pendulum.datetime(1970, 1, 1)
    )

    return filtered


def get_log_entity_name(
    log: Log,
    tasks: list[Task],
    events: list[Event],
    time_audits: list[TimeAudit],
) -> str:
    """
    Get the name of the entity associated with a log entry with ID prefix.

    Args:
        log: The log entry
        tasks: List of all tasks
        events: List of all events
        time_audits: List of all time audits

    Returns:
        The name/description of the associated entity with ID prefix (e.g., "t:123 description"),
        or empty string if none
    """
    if log["reference_type"] is None or log["reference_id"] is None:
        return ""

    ref_type = log["reference_type"]
    ref_id = log["reference_id"]

    if ref_type == "task":
        matching_tasks = [t for t in tasks if t["id"] == ref_id]
        if matching_tasks:
            desc = matching_tasks[0].get("description", "")
            name = desc if desc is not None else ""
            mapped_id = ID_MAP_REPO.associate_id("tasks", ref_id)
            return f"t:{mapped_id} {name}" if name else f"t:{mapped_id}"
    elif ref_type == "event":
        matching_events = [e for e in events if e["id"] == ref_id]
        if matching_events:
            title = matching_events[0].get("title", "")
            name = title if title is not None else ""
            mapped_id = ID_MAP_REPO.associate_id("events", ref_id)
            return f"e:{mapped_id} {name}" if name else f"e:{mapped_id}"
    elif ref_type == "time_audit":
        matching_audits = [ta for ta in time_audits if ta["id"] == ref_id]
        if matching_audits:
            desc = matching_audits[0].get("description", "")
            name = desc if desc is not None else ""
            mapped_id = ID_MAP_REPO.associate_id("time_audits", ref_id)
            return f"a:{mapped_id} {name}" if name else f"a:{mapped_id}"

    return ""


def render_day_header(
    console: Console, date: pendulum.DateTime, show_empty: bool = True
) -> None:
    """
    Render a day header with appropriate styling.

    Args:
        console: Rich console to print to
        date: The date to render header for
        show_empty: Whether to render anything (for conditional rendering)
    """
    if not show_empty:
        return

    date_str = date.format("YYYY-MM-DD ddd")
    today = pendulum.now("local").start_of("day")
    is_today = date == today
    day_of_week = date.day_of_week
    is_weekend = day_of_week in (5, 6)  # Saturday=5, Sunday=6 in pendulum

    if is_today:
        console.print(
            f"\n• [bold black on bright_cyan]{date_str}[/bold black on bright_cyan]"
        )
    elif is_weekend:
        console.print(f"\n• [bold white on orange4]{date_str}[/bold white on orange4]")
    else:
        console.print(f"\n• [bold]{date_str}[/bold]")


def render_timespans(
    console: Console, timespans: list[Timespan], date: pendulum.DateTime
) -> None:
    """
    Render timespans for a given day.

    Args:
        console: Rich console to print to
        timespans: Filtered timespans for the day
        date: The current date being rendered
    """
    for timespan in timespans:
        description = timespan.get("description", "[no description]")
        if description is None:
            description = "[no description]"
        color = timespan.get("color", "white")
        if color is None:
            color = "white"

        timespan_id_raw = timespan.get("id")
        if timespan_id_raw is not None:
            timespan_id = str(ID_MAP_REPO.associate_id("timespans", timespan_id_raw))
        else:
            timespan_id = ""

        # Format date range
        if timespan["start"] is not None:
            timespan_start_local = timespan["start"].in_tz("local")
            start_date_str = timespan_start_local.format("MMM DD")
        else:
            start_date_str = "???"

        if timespan["end"] is not None:
            timespan_end_local = timespan["end"].in_tz("local")
            end_date_str = timespan_end_local.format("MMM DD")
            date_range = f"{start_date_str}-{end_date_str}"
        else:
            date_range = f"{start_date_str}-"

        line = Text()
        line.append("  ", style="")  # Indentation
        line.append("➜ ", style=color)  # Colored arrow emoji
        line.append(f"{date_range} ", style="dim")
        line.append(f"{timespan_id} ", style=color)
        line.append(description, style=color)

        console.print(line)


def render_tasks(
    console: Console,
    tasks: list[Task],
    all_tasks: list[Task],
    date: pendulum.DateTime,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
) -> None:
    """
    Render tasks for a given day.

    Args:
        console: Rich console to print to
        tasks: Filtered tasks for the day
        all_tasks: All tasks (for checking clones)
        date: The current date being rendered
        show_scheduled_tasks: Whether to show scheduled label
        show_due_tasks: Whether to show due label
    """
    for task in tasks:
        description = task.get("description", "[no description]")
        if description is None:
            description = "[no description]"
        color = task.get("color", "white")
        if color is None:
            color = "white"

        # Apply dark grey color to completed tasks
        if is_task_completed(task):
            task_style = COMPLETED_TASK_COLOR
        else:
            task_style = color

        state = task_state(task, all_tasks)
        task_id_raw = task.get("id")
        if task_id_raw is not None:
            task_id = str(ID_MAP_REPO.associate_id("tasks", task_id_raw))
        else:
            task_id = ""
        line = Text()
        line.append("  ", style="")  # Indentation
        line.append(f"{state} ", style=task_style)
        line.append(f"{task_id} ", style=task_style)
        line.append(description, style=task_style)

        # Add label for scheduled vs due
        if show_scheduled_tasks and task["scheduled"] is not None:
            task_scheduled_local = task["scheduled"].in_tz("local").start_of("day")
            if task_scheduled_local >= date and task_scheduled_local <= date.end_of(
                "day"
            ):
                line.append(" (scheduled)", style="dim")
        if show_due_tasks and task["due"] is not None:
            task_due_local = task["due"].in_tz("local").start_of("day")
            if task_due_local >= date and task_due_local <= date.end_of("day"):
                line.append(" (due)", style="dim")

        console.print(line)


def render_events(console: Console, events: list[Event]) -> None:
    """
    Render events for a given day.

    Args:
        console: Rich console to print to
        events: Filtered events for the day
    """
    for event in events:
        title = event.get("title", "[no title]")
        if title is None:
            title = "[no title]"
        color = event.get("color", "white")
        if color is None:
            color = "white"

        event_id_raw = event.get("id")
        if event_id_raw is not None:
            event_id = str(ID_MAP_REPO.associate_id("events", event_id_raw))
        else:
            event_id = ""
        line = Text()
        line.append("  ", style="")  # Indentation

        # Check if all-day event
        if event["all_day"]:
            line.append("■ ", style=color)
            line.append(f"{event_id} ", style=color)
            line.append(title, style=color)
            line.append(" (all day)", style="dim")
        else:
            # Timed event - show time
            event_start = event["start"].in_tz("local")
            event_end = (
                event["end"].in_tz("local")
                if event["end"] is not None
                else event_start.add(hours=1)
            )
            time_str = event_start.format("HH:mm")
            end_time_str = event_end.format("HH:mm")

            line.append("■ ", style=color)
            line.append(f"{time_str}-{end_time_str} ", style="dim")
            line.append(f"{event_id} ", style=color)
            line.append(title, style=color)

        console.print(line)


def render_entries(
    console: Console,
    entries: list[Entry],
    trackers: list[Tracker],
) -> None:
    """
    Render tracker entries for a given day.

    Args:
        console: Rich console to print to
        entries: Filtered entries for the day
        trackers: All trackers (for getting tracker info)
    """
    # Build tracker lookup
    tracker_by_id: dict[EntityId, Tracker] = {}
    for tracker in trackers:
        if tracker["id"] is not None:
            tracker_by_id[tracker["id"]] = tracker

    for entry in entries:
        tracker_info = tracker_by_id.get(entry["tracker_id"])
        if tracker_info is None:
            continue

        color = tracker_info.get("color", "white") or "white"
        tracker_name = tracker_info.get("name", "") or ""
        value_type = tracker_info.get("value_type", "pips") or "pips"
        unit = tracker_info.get("unit", "") or ""

        entry_id_raw = entry.get("id")
        if entry_id_raw is not None:
            entry_id = str(ID_MAP_REPO.associate_id("entries", entry_id_raw))
        else:
            entry_id = ""

        timestamp_str = entry["timestamp"].in_tz("local").format("HH:mm")

        line = Text()
        line.append("  ", style="")  # Indentation
        line.append("• ", style="dim")
        line.append(f"E  [{timestamp_str}] ", style="dim")
        line.append(f"{tracker_name}: ", style="dim")
        line.append(f"{entry_id} ", style=color)

        # Render value based on value_type
        value = entry.get("value")
        if value_type == "checkin":
            line.append("✓", style=color)
        elif value_type == "quantitative":
            if isinstance(value, int | float):
                if value == int(value):
                    display_val = str(int(value))
                else:
                    display_val = f"{value:.1f}"
                if unit:
                    line.append(f"{display_val}{unit}", style=color)
                else:
                    line.append(display_val, style=color)
        elif value_type == "multi_select":
            if value is not None:
                line.append(str(value), style=color)
        else:  # pips
            if isinstance(value, int):
                pips = "●" * min(value, 5)
                if value > 5:
                    pips += f"+{value - 5}"
                line.append(pips, style=color)
            else:
                line.append("●", style=color)

        console.print(line)


def render_chronological_items(
    console: Console,
    logs: list[Log],
    notes: list[Note],
    time_audits: list[TimeAudit],
    tasks: list[Task],
    events: list[Event],
    limit_note_lines: Optional[int] = None,
    time_audit_meta_color: str = TIME_AUDIT_META_COLOR,
    log_meta_color: str = LOG_META_COLOR,
    note_meta_color: str = NOTE_META_COLOR,
) -> None:
    """
    Render logs, notes, and time audits chronologically interleaved.

    Args:
        console: Rich console to print to
        logs: Filtered logs for the day
        notes: Filtered notes for the day
        time_audits: Filtered time audits for the day
        tasks: All tasks (for entity name lookup)
        events: All events (for entity name lookup)
        limit_note_lines: Maximum number of lines to display per note
        time_audit_meta_color: Color for time audit metadata
        log_meta_color: Color for log metadata
        note_meta_color: Color for note metadata
    """
    # Combine and sort chronologically
    log_note_items: list[tuple[str, Log | Note | TimeAudit]] = []
    for log in logs:
        log_note_items.append(("log", log))
    for note in notes:
        log_note_items.append(("note", note))
    for time_audit in time_audits:
        log_note_items.append(("time_audit", time_audit))

    # Sort by timestamp (use start time for time audits)
    def get_sort_key(
        item: tuple[str, Log | Note | TimeAudit],
    ) -> pendulum.DateTime:
        item_type, item_data = item
        if item_type == "time_audit":
            # Type narrowing for time audit
            start = item_data.get("start")
            if isinstance(start, pendulum.DateTime):
                return start
            return pendulum.datetime(1970, 1, 1)
        else:
            # Type narrowing for log/note
            timestamp = item_data.get("timestamp")
            if isinstance(timestamp, pendulum.DateTime):
                return timestamp
            return pendulum.datetime(1970, 1, 1)

    log_note_items.sort(key=get_sort_key)

    for item_type, item in log_note_items:
        if item_type == "log":
            log_item: Log = item  # type: ignore[assignment]
            _render_log_item(
                console, log_item, tasks, events, time_audits, log_meta_color
            )
        elif item_type == "note":
            note_item: Note = item  # type: ignore[assignment]
            _render_note_item(
                console,
                note_item,
                tasks,
                events,
                time_audits,
                limit_note_lines,
                note_meta_color,
            )
        else:  # time_audit
            time_audit_item: TimeAudit = item  # type: ignore[assignment]
            _render_time_audit_item(console, time_audit_item, time_audit_meta_color)


def _render_log_item(
    console: Console,
    log_item: Log,
    tasks: list[Task],
    events: list[Event],
    time_audits: list[TimeAudit],
    log_meta_color: str,
) -> None:
    """Render a single log item."""
    line = Text()
    line.append("  ", style="")  # Indentation
    line.append("• ", style=log_meta_color)

    # Add L prefix and timestamp in square brackets
    if log_item["timestamp"] is not None:
        timestamp_str = log_item["timestamp"].in_tz("local").format("HH:mm")
        line.append(f"L  [{timestamp_str}] ", style=log_meta_color)
    else:
        line.append("L  [--:--] ", style=log_meta_color)

    # Get associated entity name (task, event, or time_audit)
    entity_name = get_log_entity_name(log_item, tasks, events, time_audits)
    # Truncate to 30 characters
    if len(entity_name) > 30:
        entity_name = entity_name[:27] + "..."
    # Pad to 30 characters if shorter
    entity_name = entity_name.ljust(30)

    line.append(entity_name, style=log_meta_color)
    line.append(": ", style=log_meta_color)

    # Add log ID before log text
    log_id_raw = log_item.get("id")
    if log_id_raw is not None:
        log_id = str(ID_MAP_REPO.associate_id("logs", log_id_raw))
    else:
        log_id = ""
    log_color = log_item.get("color", "")
    # Determine style: use log's color if available, otherwise default
    log_text_style = log_color if log_color is not None and log_color != "" else ""

    if log_id:
        line.append(f"{log_id} ", style=log_text_style)

    # Add log text
    log_text = log_item.get("text", "")
    if log_text is None:
        log_text = ""

    # Strip trailing newlines
    log_text = log_text.rstrip("\n")

    # Split log text by lines
    log_lines = log_text.split("\n") if log_text else [""]

    # Calculate the indentation for continuation lines
    # Format: "  • L [HH:MM] entity_name________________ : ID "
    prefix_len = (
        len("L  [HH:mm] ") if log_item["timestamp"] is not None else len("L  [--:--] ")
    )
    indent_width = (
        2  # initial indent
        + 2  # bullet and space "• "
        + prefix_len  # "L [HH:MM] "
        + 30  # entity name (padded)
        + 2  # ": "
        + (len(log_id) + 1 if log_id else 0)  # log ID and space
    )
    continuation_indent = " " * indent_width

    # Print first line with full prefix
    line.append(log_lines[0] if log_lines else "", style=log_text_style)
    console.print(line)

    # Print remaining continuation lines with proper indentation
    for continuation_line in log_lines[1:]:
        cont_line = Text(continuation_indent)
        cont_line.append(continuation_line, style=log_text_style)
        console.print(cont_line)


def _render_note_item(
    console: Console,
    note_item: Note,
    tasks: list[Task],
    events: list[Event],
    time_audits: list[TimeAudit],
    limit_note_lines: Optional[int],
    note_meta_color: str,
) -> None:
    """Render a single note item."""
    # Add N prefix and timestamp in square brackets
    if note_item["timestamp"] is not None:
        timestamp_str = note_item["timestamp"].in_tz("local").format("HH:mm")
        prefix = f"N  [{timestamp_str}] "
    else:
        prefix = "N  [--:--] "

    # Get associated entity name (task, event, or time_audit)
    entity_name = get_log_entity_name(note_item, tasks, events, time_audits)
    # Truncate to 30 characters
    if len(entity_name) > 30:
        entity_name = entity_name[:27] + "..."
    # Pad to 30 characters if shorter
    entity_name = entity_name.ljust(30)

    # Add note ID before note text
    note_id_raw = note_item.get("id")
    if note_id_raw is not None:
        note_id = str(ID_MAP_REPO.associate_id("notes", note_id_raw))
        id_str = f"{note_id} "
    else:
        id_str = ""

    # Get note text and split into lines
    note_text = note_item.get("text", "")
    if note_text is None:
        note_text = ""

    # Strip trailing newlines
    note_text = note_text.rstrip("\n")

    # Split note text by lines
    note_lines = note_text.split("\n") if note_text else [""]

    # Limit lines if limit_note_lines is set
    if limit_note_lines is not None and len(note_lines) > limit_note_lines:
        note_lines = note_lines[:limit_note_lines]

    # Calculate the indentation for continuation lines
    # Format: "  • L [HH:MM] entity_name________________ : ID "
    indent_width = (
        2  # initial indent
        + 2  # bullet and space "• "
        + len(prefix)  # "N [HH:MM] "
        + 30  # entity name (padded)
        + 2  # ": "
        + len(id_str)  # note ID and space
    )
    continuation_indent = " " * indent_width

    # Check if note has external file path
    external_file_path = note_item.get("external_file_path")

    # Print first line with full prefix
    first_line = Text()
    first_line.append("  ", style="")  # Indentation
    first_line.append("• ", style=note_meta_color)
    first_line.append(prefix, style=note_meta_color)
    first_line.append(entity_name, style=note_meta_color)
    first_line.append(": ", style=note_meta_color)
    first_line.append(id_str, style="")

    if external_file_path:
        # If external file path exists, print it on the first line
        first_line.append(external_file_path, style="dim")
        console.print(first_line)
        # Print all note content lines with indentation
        for content_line in note_lines:
            line = Text(continuation_indent)
            line.append(content_line)
            console.print(line)
    else:
        # No external file path - print first line of note on ID line
        first_line.append(note_lines[0] if note_lines else "", style="")
        console.print(first_line)
        # Print remaining continuation lines with proper indentation
        for continuation_line in note_lines[1:]:
            line = Text(continuation_indent)
            line.append(continuation_line)
            console.print(line)


def _render_time_audit_item(
    console: Console,
    time_audit_item: TimeAudit,
    time_audit_meta_color: str,
) -> None:
    """Render a single time audit item."""
    line = Text()
    line.append("  ", style="")  # Indentation
    line.append("• ", style=time_audit_meta_color)

    # Format time range with zero-padded hours and minutes
    start_time = time_audit_item["start"]
    end_time = time_audit_item["end"]

    if start_time is not None:
        start_local = start_time.in_tz("local")
        start_str = start_local.format("HH:mm")
    else:
        start_str = "--:--"

    if end_time is not None:
        end_local = end_time.in_tz("local")
        end_str = end_local.format("HH:mm")
    else:
        # Blank space same length as time
        end_str = "     "

    time_range = f"TA [{start_str}-{end_str}] "
    line.append(time_range, style=time_audit_meta_color)

    # Calculate and display total time
    if start_time is not None:
        if end_time is not None:
            duration = end_time - start_time
        else:
            # Ongoing time audit - calculate to now
            duration = pendulum.now("UTC") - start_time

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        duration_str = f"{hours:02d}:{minutes:02d} "
        line.append(duration_str, style=time_audit_meta_color)
    else:
        line.append("--:-- ", style=time_audit_meta_color)

    # Add time audit ID
    ta_id_raw = time_audit_item.get("id")
    if ta_id_raw is not None:
        ta_id = str(ID_MAP_REPO.associate_id("time_audits", ta_id_raw))
    else:
        ta_id = ""
    color = time_audit_item.get("color", "white")
    if color is None:
        color = "white"

    if ta_id:
        line.append(f"{ta_id} ", style=color)

    # Add description
    description = time_audit_item.get("description", "")
    if description is None:
        description = "[no description]"
    line.append(description, style=color)

    console.print(line)


def render_agenda_day(
    console: Console,
    date: pendulum.DateTime,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    timespans: list[Timespan],
    logs: list[Log],
    notes: list[Note],
    entries: Optional[list[Entry]] = None,
    trackers: Optional[list[Tracker]] = None,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_events: bool = True,
    show_timespans: bool = True,
    show_logs: bool = False,
    show_notes: bool = False,
    show_time_audits: bool = False,
    show_entries: bool = False,
    limit_note_lines: Optional[int] = None,
    time_audit_meta_color: str = TIME_AUDIT_META_COLOR,
    log_meta_color: str = LOG_META_COLOR,
    note_meta_color: str = NOTE_META_COLOR,
) -> bool:
    """
    Render a single day in agenda format.

    Args:
        console: Rich console to print to
        date: The date to render
        time_audits: All time audits (will be filtered for this day)
        events: All events (will be filtered for this day)
        tasks: All tasks (will be filtered for this day)
        timespans: All timespans (will be filtered for this day)
        logs: All logs (will be filtered for this day)
        notes: All notes (will be filtered for this day)
        entries: All tracker entries (will be filtered for this day)
        trackers: All trackers (for rendering entries)
        show_scheduled_tasks: Whether to show scheduled tasks
        show_due_tasks: Whether to show due tasks
        show_events: Whether to show events
        show_timespans: Whether to show timespans
        show_logs: Whether to show logs
        show_notes: Whether to show notes
        show_time_audits: Whether to show time audits
        show_entries: Whether to show tracker entries
        limit_note_lines: Maximum number of lines per note
        time_audit_meta_color: Color for time audit metadata
        log_meta_color: Color for log metadata
        note_meta_color: Color for note metadata

    Returns:
        True if any content was rendered, False if the day was empty
    """
    # Filter entities for this day
    filtered_events = filter_events_for_day(events, date) if show_events else []
    filtered_tasks = filter_tasks_for_scheduled_or_due(
        tasks, date, show_scheduled_tasks, show_due_tasks
    )
    filtered_timespans = (
        filter_active_timespans_for_day(timespans, date) if show_timespans else []
    )
    filtered_logs = filter_logs_for_day(logs, date) if show_logs else []
    filtered_notes = filter_notes_for_day(notes, date) if show_notes else []
    filtered_time_audits = (
        filter_audits_for_day(time_audits, date) if show_time_audits else []
    )
    filtered_entries = (
        filter_entries_for_day(entries or [], date) if show_entries else []
    )

    # Sort events by start time
    all_day_events = [e for e in filtered_events if e["all_day"]]
    timed_events = [e for e in filtered_events if not e["all_day"]]
    timed_events.sort(key=lambda e: e["start"])
    filtered_events = all_day_events + timed_events

    # Check if there's any content for this day
    has_content = (
        bool(filtered_events)
        or bool(filtered_tasks)
        or bool(filtered_timespans)
        or bool(filtered_logs)
        or bool(filtered_notes)
        or bool(filtered_time_audits)
        or bool(filtered_entries)
    )

    if not has_content:
        return False

    # Render the day
    render_day_header(console, date)

    if show_timespans and filtered_timespans:
        render_timespans(console, filtered_timespans, date)

    if filtered_tasks:
        render_tasks(
            console, filtered_tasks, tasks, date, show_scheduled_tasks, show_due_tasks
        )

    if filtered_events:
        render_events(console, filtered_events)

    if show_entries and filtered_entries and trackers:
        render_entries(console, filtered_entries, trackers)

    if show_logs or show_notes or show_time_audits:
        render_chronological_items(
            console,
            filtered_logs,
            filtered_notes,
            filtered_time_audits,
            tasks,
            events,
            limit_note_lines,
            time_audit_meta_color,
            log_meta_color,
            note_meta_color,
        )

    return True
