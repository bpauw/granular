# SPDX-License-Identifier: MIT

from typing import Optional

import pendulum
from rich.console import Console, Group
from rich.padding import Padding
from rich.text import Text

from granular.model.entity_id import EntityId
from granular.color import COMPLETED_TASK_COLOR
from granular.model.entry import Entry
from granular.model.event import Event
from granular.model.granularity_type import GranularityType
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.model.tracker import Tracker
from granular.repository.id_map import ID_MAP_REPO
from granular.service.heatmap import (
    get_tasks_timeline_data,
    get_tracker_timeline_data,
)
from granular.view.view.util import is_task_completed, task_state
from granular.view.view.views.header import header
from granular.view.view.views.heatmap_core import (
    build_heatmap_row,
    get_tasks_symbol,
    get_tracker_symbol,
)


def gantt_view(
    active_context: str,
    report_name: str,
    timespans: list[Timespan],
    events: list[Event] = [],
    tasks: list[Task] = [],
    trackers: list[Tracker] = [],
    entries: list[Entry] = [],
    start: Optional[pendulum.DateTime] = None,
    end: Optional[pendulum.DateTime] = None,
    granularity: GranularityType = "day",
    show_tasks: bool = False,
    show_timespans: bool = True,
    show_events: bool = True,
    show_trackers: bool = False,
    left_column_width: int = 40,
) -> None:
    """
    Display timespans, events, and trackers on a gantt chart timeline.

    Only timespans and events that overlap with the visible timeline range are displayed.
    Deleted timespans/events and those without start dates are excluded.
    Trackers are displayed as heatmap rows showing entry intensity per time slot.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        timespans: List of timespans to display (will be filtered for visibility)
        events: List of events to display (will be filtered for visibility)
        tasks: List of tasks to display under timespans (defaults to empty list)
        trackers: List of trackers to display (defaults to empty list)
        entries: List of entries for trackers (defaults to empty list)
        start: Start date for the timeline (defaults to earliest timespan/event start)
        end: End date for the timeline (defaults to latest timespan/event end)
        granularity: Time granularity - "day", "week", or "month" (defaults to "day")
        show_tasks: Whether to show tasks under each timespan (defaults to False)
        show_timespans: Whether to show timespans (defaults to True)
        show_events: Whether to show events (defaults to True)
        show_trackers: Whether to show trackers (defaults to False)
        left_column_width: Width of left column for item names (defaults to 40)
    """
    header(active_context, report_name)

    console = Console()

    # Filter out deleted timespans and events
    timespans = [ts for ts in timespans if ts["deleted"] is None]
    events = [ev for ev in events if ev["deleted"] is None]

    # Filter out deleted and archived trackers
    valid_trackers = [
        t for t in trackers if t["deleted"] is None and t["archived"] is None
    ]

    # Filter out timespans and events without start dates
    valid_timespans = [ts for ts in timespans if ts["start"] is not None]
    valid_events = [ev for ev in events if ev["start"] is not None]

    # Check if we have anything to display
    has_tasks = show_tasks and len(tasks) > 0
    has_timespans = show_timespans and len(valid_timespans) > 0
    has_events = show_events and len(valid_events) > 0
    has_trackers = show_trackers and len(valid_trackers) > 0

    if not has_tasks and not has_timespans and not has_events and not has_trackers:
        console.print("\n[dim]No timespans, events, or trackers to display[/dim]\n")
        return

    # Determine the timeline range from timespans, events, and tracker entries
    if start is None:
        start_dates: list[pendulum.DateTime] = []
        if has_timespans:
            start_dates.extend(
                [ts["start"] for ts in valid_timespans if ts["start"] is not None]
            )
        if has_events:
            start_dates.extend(
                [ev["start"] for ev in valid_events if ev["start"] is not None]
            )
        if has_trackers:
            # Include entry timestamps for trackers
            tracker_ids = {t["id"] for t in valid_trackers}
            entry_timestamps = [
                e["timestamp"]
                for e in entries
                if e["deleted"] is None and e["tracker_id"] in tracker_ids
            ]
            start_dates.extend(entry_timestamps)
        if start_dates:
            start = min(start_dates)
        else:
            console.print("\n[dim]No start dates found[/dim]\n")
            return

    if end is None:
        end_dates: list[pendulum.DateTime] = []
        if has_timespans:
            end_dates.extend(
                [ts["end"] for ts in valid_timespans if ts["end"] is not None]
            )
            # Add start dates as fallback for timespans without end dates
            end_dates.extend(
                [ts["start"] for ts in valid_timespans if ts["start"] is not None]
            )
        if has_events:
            end_dates.extend(
                [ev["end"] for ev in valid_events if ev["end"] is not None]
            )
            # Add start dates as fallback for events without end dates
            end_dates.extend(
                [ev["start"] for ev in valid_events if ev["start"] is not None]
            )
        if has_trackers:
            # Include entry timestamps for trackers
            tracker_ids = {t["id"] for t in valid_trackers}
            entry_timestamps = [
                e["timestamp"]
                for e in entries
                if e["deleted"] is None and e["tracker_id"] in tracker_ids
            ]
            end_dates.extend(entry_timestamps)
        if end_dates:
            end = max(end_dates)
        else:
            # If we still don't have an end date, use start as fallback
            end = start if start is not None else pendulum.now("local")

    # Ensure we're working with local timezone
    # At this point start and end are guaranteed to be not None due to above logic
    assert start is not None
    assert end is not None
    start_local: pendulum.DateTime = start.in_tz("local").start_of("day")
    end_local: pendulum.DateTime = end.in_tz("local").end_of("day")

    # Filter timespans to only those visible in the timeline range
    visible_timespans = []
    if show_timespans:
        for ts in valid_timespans:
            ts_start = ts["start"]  # Guaranteed not None due to valid_timespans filter
            ts_end = ts["end"]
            assert ts_start is not None

            ts_start_local = ts_start.in_tz("local")
            ts_end_local = ts_end.in_tz("local") if ts_end is not None else None

            # Check if timespan overlaps with the timeline range
            if ts_end_local is not None:
                # Timespan has an end date - check for overlap
                overlaps = ts_start_local <= end_local and ts_end_local >= start_local
            else:
                # Timespan has no end date (ongoing) - check if it starts before timeline ends
                overlaps = ts_start_local <= end_local

            if overlaps:
                visible_timespans.append(ts)

    # Filter events to only those visible in the timeline range
    # AND whose start date falls within the timeline range (so they will actually be printed)
    visible_events = []
    if show_events:
        for ev in valid_events:
            ev_start = ev["start"]  # Guaranteed not None due to valid_events filter
            assert ev_start is not None

            ev_start_local = ev_start.in_tz("local")

            # Check if event start is within the timeline range
            # Only events whose start date is within the range will have a marker printed
            if ev_start_local >= start_local and ev_start_local <= end_local:
                visible_events.append(ev)

    # Sort visible timespans by start date ascending
    visible_timespans.sort(key=lambda ts: ts["start"] or pendulum.DateTime.min)

    # Sort visible events by start date ascending
    visible_events.sort(key=lambda ev: ev["start"] or pendulum.DateTime.min)

    # Continue to render empty gantt chart even if no visible items

    # Generate time slots based on granularity
    time_slots = _generate_time_slots(start_local, end_local, granularity)

    # Get terminal width and calculate available space for timeline
    terminal_width = console.width
    available_width = terminal_width - left_column_width

    # Determine which slots to show headers for based on available width
    slots_to_show = _determine_slots_to_show(time_slots, available_width, granularity)

    # Display date range header
    date_range_str = (
        f"{start_local.format('YYYY-MM-DD')} to {end_local.format('YYYY-MM-DD')}"
    )
    console.print(f"\n[bold]{date_range_str}[/bold] (granularity: {granularity})\n")

    # Build the gantt chart
    chart_elements = []

    # Calculate slot widths for header
    slot_widths = _calculate_slot_widths(time_slots, granularity, slots_to_show)

    # Add date header rows (may include year row for month granularity)
    header_rows = _build_date_header(
        time_slots, granularity, slots_to_show, slot_widths, left_column_width
    )
    for header_row in header_rows:
        chart_elements.append(header_row)

    # Add separator line with alternating backgrounds
    separator = Text("─" * left_column_width, style="dim")
    prev_slot_has_label = False
    for i in range(len(time_slots)):
        width = slot_widths[i]
        current_slot_has_label = i in slots_to_show

        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # If both current and previous slots have labels, the width includes a leading separator space
        if current_slot_has_label and prev_slot_has_label:
            # Add separator space without background
            separator.append("─", style="dim")
            # Add the remaining width with background
            if bg_style:
                separator.append("─" * (width - 1), style="dim" + bg_style)
            else:
                separator.append("─" * (width - 1), style="dim")
        else:
            # No leading separator, apply background to full width
            if bg_style:
                separator.append("─" * width, style="dim" + bg_style)
            else:
                separator.append("─" * width, style="dim")

        prev_slot_has_label = current_slot_has_label

    chart_elements.append(separator)

    # Add tracker rows (trackers are displayed first, above events and timespans)
    if show_trackers:
        for tracker in valid_trackers:
            tracker_row = _build_tracker_row(
                tracker,
                entries,
                time_slots,
                granularity,
                slot_widths,
                slots_to_show,
                left_column_width,
            )
            chart_elements.append(tracker_row)

    # Add each event row (events are displayed before timespans)
    for event in visible_events:
        event_row = _build_event_row(
            event,
            time_slots,
            granularity,
            slot_widths,
            slots_to_show,
            left_column_width,
        )
        chart_elements.append(event_row)

    # Separate tasks into standalone and timespan-associated
    standalone_tasks = []

    if show_tasks:
        # Filter tasks with due or scheduled dates that are not associated with a timespan
        # and whose dates fall within the visible timeline range
        for task in tasks:
            if (
                task["deleted"] is None
                and task["timespan_id"] is None
                and (task["due"] is not None or task["scheduled"] is not None)
            ):
                # Check if the task's due or scheduled date is within the timeline range
                task_in_range = False
                if task["due"] is not None:
                    task_date = task["due"].in_tz("local")
                    if task_date >= start_local and task_date <= end_local:
                        task_in_range = True
                if not task_in_range and task["scheduled"] is not None:
                    task_date = task["scheduled"].in_tz("local")
                    if task_date >= start_local and task_date <= end_local:
                        task_in_range = True
                if task_in_range:
                    standalone_tasks.append(task)

        # Sort standalone tasks by due date (or scheduled date if no due) ascending
        standalone_tasks.sort(
            key=lambda t: t["due"] or t["scheduled"] or pendulum.DateTime.min
        )

    # Add standalone task rows (tasks not associated with a timespan but with due/scheduled dates)
    for task in standalone_tasks:
        task_row = _build_standalone_task_row(
            task,
            tasks,
            time_slots,
            granularity,
            slot_widths,
            slots_to_show,
            left_column_width,
        )
        chart_elements.append(task_row)

    # Add each timespan row
    for timespan in visible_timespans:
        timespan_row = _build_timespan_row(
            timespan,
            time_slots,
            granularity,
            slot_widths,
            slots_to_show,
            left_column_width,
        )
        chart_elements.append(timespan_row)

        # Add task rows if show_tasks is enabled
        if show_tasks:
            task_rows = _build_task_rows(
                timespan["id"],
                tasks,
                left_column_width,
                time_slots,
                granularity,
                slot_widths,
                slots_to_show,
            )
            for task_row in task_rows:
                chart_elements.append(task_row)

    # Render the gantt chart
    chart = Group(*chart_elements)
    console.print(Padding(chart, (0, 0, 1, 0)))
    console.print()


def tasks_heatmap_view(
    active_context: str,
    report_name: str,
    tasks: list[Task],
    time_audits: list[TimeAudit],
    start: Optional[pendulum.DateTime] = None,
    end: Optional[pendulum.DateTime] = None,
    granularity: GranularityType = "day",
    left_column_width: int = 40,
    projects: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
) -> None:
    """
    Display a heatmap showing task completions and time audit activity.

    Shows one row per project/tag specified, plus a total row if no filters.
    Each row shows markers for each day where:
    - A task was completed
    - A time audit exists

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        tasks: List of tasks (should be pre-filtered for deleted)
        time_audits: List of time audits (should be pre-filtered for deleted)
        start: Start date for the timeline (defaults to N days ago)
        end: End date for the timeline (defaults to today)
        granularity: Time granularity - "day", "week", or "month" (defaults to "day")
        left_column_width: Width of left column for item names (defaults to 40)
        projects: List of projects to show separate rows for (None shows all)
        tags: List of tags to show separate rows for (None shows all)
    """
    header(active_context, report_name)

    console = Console()

    # Default to today if no end date
    if end is None:
        end = pendulum.today("local")
    if start is None:
        start = end.subtract(days=13)  # Default to 14 days

    # Ensure we're working with local timezone
    start_local: pendulum.DateTime = start.in_tz("local").start_of("day")
    end_local: pendulum.DateTime = end.in_tz("local").end_of("day")

    # Generate time slots based on granularity
    time_slots = _generate_time_slots(start_local, end_local, granularity)

    if not time_slots:
        console.print("\n[dim]No time slots to display[/dim]\n")
        return

    # Get terminal width and calculate available space for timeline
    terminal_width = console.width
    available_width = terminal_width - left_column_width

    # Determine which slots to show headers for based on available width
    slots_to_show = _determine_slots_to_show(time_slots, available_width, granularity)

    # Display date range header
    date_range_str = (
        f"{start_local.format('YYYY-MM-DD')} to {end_local.format('YYYY-MM-DD')}"
    )
    console.print(f"\n[bold]{date_range_str}[/bold] (granularity: {granularity})\n")

    # Build the heatmap chart
    chart_elements = []

    # Calculate slot widths for header
    slot_widths = _calculate_slot_widths(time_slots, granularity, slots_to_show)

    # Add date header rows (may include year row for month granularity)
    header_rows = _build_date_header(
        time_slots, granularity, slots_to_show, slot_widths, left_column_width
    )
    for header_row in header_rows:
        chart_elements.append(header_row)

    # Add separator line with alternating backgrounds
    separator = Text("─" * left_column_width, style="dim")
    prev_slot_has_label = False
    for i in range(len(time_slots)):
        width = slot_widths[i]
        current_slot_has_label = i in slots_to_show

        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # If both current and previous slots have labels, the width includes a leading separator space
        if current_slot_has_label and prev_slot_has_label:
            # Add separator space without background
            separator.append("─", style="dim")
            # Add the remaining width with background
            if bg_style:
                separator.append("─" * (width - 1), style="dim" + bg_style)
            else:
                separator.append("─" * (width - 1), style="dim")
        else:
            # No leading separator, apply background to full width
            if bg_style:
                separator.append("─" * width, style="dim" + bg_style)
            else:
                separator.append("─" * width, style="dim")

        prev_slot_has_label = current_slot_has_label

    chart_elements.append(separator)

    # Build list of rows to display
    rows_to_display: list[tuple[str, str, list[Task], list[TimeAudit]]] = []

    # Add rows for each project if specified
    if projects is not None:
        for proj in projects:
            proj_tasks = [t for t in tasks if t["project"] == proj]
            proj_time_audits = [ta for ta in time_audits if ta["project"] == proj]
            rows_to_display.append((proj, "cyan", proj_tasks, proj_time_audits))

    # Add rows for each tag if specified
    if tags is not None:
        for tag_name in tags:
            tag_tasks = [
                t for t in tasks if t["tags"] is not None and tag_name in t["tags"]
            ]
            tag_time_audits = [
                ta
                for ta in time_audits
                if ta["tags"] is not None and tag_name in ta["tags"]
            ]
            rows_to_display.append((tag_name, "magenta", tag_tasks, tag_time_audits))

    # If no projects or tags specified, show a single "Tasks Activity" row
    if not rows_to_display:
        rows_to_display.append(("Tasks Activity", "cyan", tasks, time_audits))

    # Add heatmap rows
    for label, color, row_tasks, row_time_audits in rows_to_display:
        tasks_row = _build_tasks_heatmap_row(
            label=f"    {label}",
            color=color,
            tasks=row_tasks,
            time_audits=row_time_audits,
            time_slots=time_slots,
            granularity=granularity,
            slot_widths=slot_widths,
            slots_to_show=slots_to_show,
            left_column_width=left_column_width,
        )
        chart_elements.append(tasks_row)

    # Render the heatmap chart
    chart = Group(*chart_elements)
    console.print(Padding(chart, (0, 0, 1, 0)))
    console.print()


def _generate_time_slots(
    start: pendulum.DateTime, end: pendulum.DateTime, granularity: GranularityType
) -> list[pendulum.DateTime]:
    """
    Generate a list of time slots from start to end based on granularity.

    Args:
        start: Start datetime
        end: End datetime
        granularity: "day", "week", or "month"

    Returns:
        List of datetime objects representing each time slot
    """
    slots = []
    current = start

    while current <= end:
        slots.append(current)
        if granularity == "day":
            current = current.add(days=1)
        elif granularity == "week":
            current = current.add(weeks=1)
        elif granularity == "month":
            current = current.add(months=1)

    return slots


def _determine_slots_to_show(
    time_slots: list[pendulum.DateTime],
    available_width: int,
    granularity: GranularityType,
) -> set[int]:
    """
    Determine which time slot indices should display headers based on available width.

    If all slots fit, show all headers. Otherwise, use an elision strategy:
    - For day granularity: show weekends, then week starts, then month starts
    - For week granularity: show month starts
    - For month granularity: show year starts

    Args:
        time_slots: List of all time slots
        available_width: Available character width for the timeline
        granularity: "day", "week", or "month"

    Returns:
        Set of indices for slots that should show headers
    """
    total_slots = len(time_slots)

    # If everything fits, show all headers
    if total_slots <= available_width:
        return set(range(total_slots))

    # Otherwise, apply elision strategy based on granularity
    slots_to_show: set[int] = set()

    if granularity == "day":
        # Strategy 1: Show weekends (Saturday and Sunday)
        for i, slot in enumerate(time_slots):
            if slot.day_of_week in [5, 6]:  # Saturday=5, Sunday=6 in pendulum
                slots_to_show.add(i)

        # If still too many, switch to week starts (Mondays)
        if len(slots_to_show) > available_width:
            slots_to_show = set()
            for i, slot in enumerate(time_slots):
                if slot.day_of_week == 0:  # Monday=0
                    slots_to_show.add(i)

        # If still too many, switch to month starts
        if len(slots_to_show) > available_width:
            slots_to_show = set()
            for i, slot in enumerate(time_slots):
                if slot.day == 1:  # First day of month
                    slots_to_show.add(i)

    elif granularity == "week":
        # Show month starts
        for i, slot in enumerate(time_slots):
            # Show if this week contains the first day of a month
            week_start = slot.start_of("week")
            week_end = slot.end_of("week")
            if week_start.month != week_end.month or slot.day <= 7:
                slots_to_show.add(i)

        # If still too many, show only first week of each month
        if len(slots_to_show) > available_width:
            slots_to_show = set()
            for i, slot in enumerate(time_slots):
                if slot.day <= 7:
                    slots_to_show.add(i)

    elif granularity == "month":
        # Show year starts (January)
        for i, slot in enumerate(time_slots):
            if slot.month == 1:
                slots_to_show.add(i)

        # If still too many, show every other year
        if len(slots_to_show) > available_width:
            slots_to_show = set()
            for i, slot in enumerate(time_slots):
                if slot.month == 1 and slot.year % 2 == 0:
                    slots_to_show.add(i)

    # Always show first and last slot for context
    if time_slots:
        slots_to_show.add(0)
        slots_to_show.add(len(time_slots) - 1)

    return slots_to_show


def _calculate_slot_widths(
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slots_to_show: set[int],
) -> list[int]:
    """
    Calculate the display width for each time slot in the header.

    Args:
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slots_to_show: Set of indices for slots that should show headers

    Returns:
        List of widths (in characters) for each slot
    """
    widths = []
    prev_was_label = False

    for i, slot in enumerate(time_slots):
        if i in slots_to_show:
            if granularity == "day":
                label = slot.format("DD")
            elif granularity == "week":
                label = str(slot.week_of_year)
            else:  # month
                label = slot.format("MMM")

            # Width is label length + 1 space after (or before if prev was also a label)
            width = len(label)
            if prev_was_label:
                width += 1  # Add space before this label
            prev_was_label = True
        else:
            # Just 1 character for empty slots
            width = 1
            prev_was_label = False

        widths.append(width)

    return widths


def _build_date_header(
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> list[Text]:
    """
    Build the date header rows showing time slots.

    For month granularity, adds a year row above when year changes occur.
    For week granularity, adds year and month rows above when rollovers occur.

    Args:
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        List of Rich Text objects with the date header rows
    """
    rows: list[Text] = []

    # For day granularity, check if we need year and month rows
    if granularity == "day":
        year_row = _build_day_year_row(
            time_slots, slots_to_show, slot_widths, left_column_width
        )
        if year_row is not None:
            rows.append(year_row)

        month_row = _build_day_month_row(
            time_slots, slots_to_show, slot_widths, left_column_width
        )
        if month_row is not None:
            rows.append(month_row)

    # For week granularity, check if we need year and month rows
    if granularity == "week":
        year_row = _build_week_year_row(
            time_slots, slots_to_show, slot_widths, left_column_width
        )
        if year_row is not None:
            rows.append(year_row)

        month_row = _build_week_month_row(
            time_slots, slots_to_show, slot_widths, left_column_width
        )
        if month_row is not None:
            rows.append(month_row)

    # For month granularity, check if we need a year row
    if granularity == "month":
        year_row = _build_year_row(
            time_slots, slots_to_show, slot_widths, left_column_width
        )
        if year_row is not None:
            rows.append(year_row)

    # Build the main date header row
    header = Text()

    # Add left padding for the description column
    header.append(" " * left_column_width)

    # Get today's date for comparison
    today = pendulum.now("local").start_of("day")
    current_week_start = today.start_of("week")
    current_month_start = today.start_of("month")

    # Add each date label - use appropriate format based on granularity
    prev_was_label = False
    for i, slot in enumerate(time_slots):
        width = slot_widths[i]

        # Determine background style for alternating day columns (only for day granularity)
        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        if i in slots_to_show:
            if granularity == "day":
                # Show day of month (01-31)
                label = slot.format("DD")
            elif granularity == "week":
                # Show week number (1-53)
                label = str(slot.week_of_year)
            else:  # month
                # Show month abbreviation
                label = slot.format("MMM")

            # Add space before label if previous slot also had a label
            if prev_was_label:
                header.append(" ")

            # Apply highlighting based on granularity
            if granularity == "day":
                # Check if this is today
                is_today = slot == today
                # Check if this is a weekend
                is_weekend = slot.day_of_week in [
                    pendulum.SATURDAY,
                    pendulum.SUNDAY,
                ]

                if is_today:
                    # For alternating background days, we need to preserve the background
                    # but today's highlighting takes visual precedence
                    base_style = "bold black on bright_cyan"
                    header.append(label, style=base_style)
                elif is_weekend:
                    base_style = "bold white on orange4"
                    header.append(label, style=base_style)
                else:
                    base_style = "bold cyan"
                    if bg_style:
                        header.append(label, style=base_style + bg_style)
                    else:
                        header.append(label, style=base_style)
            elif granularity == "week":
                # Check if this is the current week
                is_current_week = slot.start_of("week") == current_week_start

                if is_current_week:
                    header.append(label, style="bold black on bright_cyan")
                else:
                    header.append(label, style="bold cyan")
            else:  # month
                # Check if this is the current month
                is_current_month = slot.start_of("month") == current_month_start

                if is_current_month:
                    header.append(label, style="bold black on bright_cyan")
                else:
                    header.append(label, style="bold cyan")
            prev_was_label = True
        else:
            # Show spaces for slots without headers with background
            if bg_style:
                header.append(" " * width, style=bg_style)
            else:
                header.append(" " * width)
            prev_was_label = False

    rows.append(header)

    return rows


def _build_day_year_row(
    time_slots: list[pendulum.DateTime],
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> Optional[Text]:
    """
    Build a year header row for day granularity when year rollovers occur.

    The year (YY format) is shown aligned with the first day of each year.

    Args:
        time_slots: List of time slots for the timeline
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        Rich Text object with year labels, or None if no year changes detected
    """
    # Check if there are any year changes
    years_in_view = set()
    for slot in time_slots:
        years_in_view.add(slot.year)

    # If only one year, no need for year row
    if len(years_in_view) <= 1:
        return None

    # Calculate the position where each day starts
    day_positions = []
    pos = 0
    prev_was_label = False
    for i in range(len(time_slots)):
        if i in slots_to_show:
            if prev_was_label:
                pos += 1  # Add separator space
            day_positions.append(pos)
            # Add the day label length
            label = time_slots[i].format("DD")
            pos += len(label)
            prev_was_label = True
        else:
            day_positions.append(pos)
            pos += 1  # Single space for non-shown slots
            prev_was_label = False

    # Total width of the timeline
    total_width = sum(slot_widths)

    # Build year row as a list of characters, then convert to Text
    year_chars = [" "] * total_width

    # Place year labels at the first day of each year
    for i, slot in enumerate(time_slots):
        if i in slots_to_show and slot.day == 1 and slot.month == 1:
            year_label = slot.format("YY")
            start_pos = day_positions[i]

            # Place year label at the day's position
            for j, char in enumerate(year_label):
                if start_pos + j < total_width:
                    year_chars[start_pos + j] = char

    # Convert to Text object with styling
    year_row = Text()
    year_row.append(" " * left_column_width)

    # Add characters with styling for year labels
    i = 0
    while i < total_width:
        if year_chars[i] != " ":
            # Find the extent of this year label
            j = i
            while j < total_width and year_chars[j] != " ":
                j += 1
            year_row.append("".join(year_chars[i:j]), style="bold yellow")
            i = j
        else:
            # Find the extent of spaces
            j = i
            while j < total_width and year_chars[j] == " ":
                j += 1
            year_row.append(" " * (j - i))
            i = j

    return year_row


def _build_day_month_row(
    time_slots: list[pendulum.DateTime],
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> Optional[Text]:
    """
    Build a month header row for day granularity when month rollovers occur.

    The month (MMM format) is shown aligned with the first day of each month.

    Args:
        time_slots: List of time slots for the timeline
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        Rich Text object with month labels, or None if no month changes detected
    """
    # Check if there are any month changes
    months_in_view = set()
    for slot in time_slots:
        months_in_view.add((slot.year, slot.month))

    # If only one month, no need for month row
    if len(months_in_view) <= 1:
        return None

    # Calculate the position where each day starts
    day_positions = []
    pos = 0
    prev_was_label = False
    for i in range(len(time_slots)):
        if i in slots_to_show:
            if prev_was_label:
                pos += 1  # Add separator space
            day_positions.append(pos)
            # Add the day label length
            label = time_slots[i].format("DD")
            pos += len(label)
            prev_was_label = True
        else:
            day_positions.append(pos)
            pos += 1  # Single space for non-shown slots
            prev_was_label = False

    # Total width of the timeline
    total_width = sum(slot_widths)

    # Build month row as a list of characters, then convert to Text
    month_chars = [" "] * total_width

    # Place month labels at the first day of each month
    for i, slot in enumerate(time_slots):
        if i in slots_to_show and slot.day == 1:
            month_label = slot.format("MMM")
            start_pos = day_positions[i]

            # Place month label at the day's position
            for j, char in enumerate(month_label):
                if start_pos + j < total_width:
                    month_chars[start_pos + j] = char

    # Convert to Text object with styling
    month_row = Text()
    month_row.append(" " * left_column_width)

    # Add characters with styling for month labels
    i = 0
    while i < total_width:
        if month_chars[i] != " ":
            # Find the extent of this month label
            j = i
            while j < total_width and month_chars[j] != " ":
                j += 1
            month_row.append("".join(month_chars[i:j]), style="bold magenta")
            i = j
        else:
            # Find the extent of spaces
            j = i
            while j < total_width and month_chars[j] == " ":
                j += 1
            month_row.append(" " * (j - i))
            i = j

    return month_row


def _build_week_year_row(
    time_slots: list[pendulum.DateTime],
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> Optional[Text]:
    """
    Build a year header row for week granularity when year rollovers occur.

    The year (YY format) is shown when a week spans across years.

    Args:
        time_slots: List of time slots for the timeline
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        Rich Text object with year labels, or None if no year changes detected
    """
    # Check if there are any year changes within weeks
    has_year_change = False
    for i, slot in enumerate(time_slots):
        if i in slots_to_show:
            week_start = slot.start_of("week")
            week_end = slot.end_of("week")
            if week_start.year != week_end.year:
                has_year_change = True
                break

    if not has_year_change:
        return None

    # Calculate the position where each week number starts
    week_positions = []
    pos = 0
    prev_was_label = False
    for i in range(len(time_slots)):
        if i in slots_to_show:
            if prev_was_label:
                pos += 1  # Add separator space
            week_positions.append(pos)
            # Add the week number label length
            label = str(time_slots[i].week_of_year)
            pos += len(label)
            prev_was_label = True
        else:
            week_positions.append(pos)
            pos += 1  # Single space for non-shown slots
            prev_was_label = False

    # Total width of the timeline
    total_width = sum(slot_widths)

    # Build year row as a list of characters, then convert to Text
    year_chars = [" "] * total_width

    for i, slot in enumerate(time_slots):
        if i in slots_to_show:
            week_start = slot.start_of("week")
            week_end = slot.end_of("week")

            # Show year label if this week spans across years
            if week_start.year != week_end.year:
                year_label = week_end.format("YY")
                start_pos = week_positions[i]

                # Place year label at the week's position
                for j, char in enumerate(year_label):
                    if start_pos + j < total_width:
                        year_chars[start_pos + j] = char

    # Convert to Text object with styling
    year_row = Text()
    year_row.append(" " * left_column_width)

    # Add characters with styling for year labels
    i = 0
    while i < total_width:
        if year_chars[i] != " ":
            # Find the extent of this year label
            j = i
            while j < total_width and year_chars[j] != " ":
                j += 1
            year_row.append("".join(year_chars[i:j]), style="bold yellow")
            i = j
        else:
            # Find the extent of spaces
            j = i
            while j < total_width and year_chars[j] == " ":
                j += 1
            year_row.append(" " * (j - i))
            i = j

    return year_row


def _build_week_month_row(
    time_slots: list[pendulum.DateTime],
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> Optional[Text]:
    """
    Build a month header row for week granularity when month rollovers occur.

    The month (MMM format) is shown spanning all weeks that belong to that month.

    Args:
        time_slots: List of time slots for the timeline
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        Rich Text object with month labels, or None if no month changes detected
    """
    # Determine which month each week belongs to (using the week's start date)
    week_months = []
    for slot in time_slots:
        # Use the start of the week to determine which month it belongs to
        week_start = slot.start_of("week")
        week_months.append((week_start.year, week_start.month))

    # Check if there are multiple months
    unique_months = set(week_months)
    if len(unique_months) <= 1:
        return None

    # Calculate the position where each week number starts
    week_positions = []
    pos = 0
    prev_was_label = False
    for i in range(len(time_slots)):
        if i in slots_to_show:
            if prev_was_label:
                pos += 1  # Add separator space
            week_positions.append(pos)
            # Add the week number label length
            label = str(time_slots[i].week_of_year)
            pos += len(label)
            prev_was_label = True
        else:
            week_positions.append(pos)
            pos += 1  # Single space for non-shown slots
            prev_was_label = False

    # Total width of the timeline
    total_width = sum(slot_widths)

    # Build month row as a list of characters, then convert to Text
    month_chars = [" "] * total_width

    # Group consecutive weeks by month and place month labels
    current_month = None
    month_start_idx = None

    for i, (year, month) in enumerate(week_months):
        if (year, month) != current_month:
            # If we were tracking a month, place its label
            if current_month is not None and month_start_idx is not None:
                # Find a visible week in this month range to place the label
                for j in range(month_start_idx, i):
                    if j in slots_to_show:
                        month_label = time_slots[j].format("MMM")
                        start_pos = week_positions[j]

                        # Place month label at the first visible week's position
                        for k, char in enumerate(month_label):
                            if start_pos + k < total_width:
                                month_chars[start_pos + k] = char
                        break

            # Start tracking new month
            current_month = (year, month)
            month_start_idx = i

    # Handle the last month
    if current_month is not None and month_start_idx is not None:
        for j in range(month_start_idx, len(week_months)):
            if j in slots_to_show:
                month_label = time_slots[j].format("MMM")
                start_pos = week_positions[j]

                # Place month label at the first visible week's position
                for k, char in enumerate(month_label):
                    if start_pos + k < total_width:
                        month_chars[start_pos + k] = char
                break

    # Convert to Text object with styling
    month_row = Text()
    month_row.append(" " * left_column_width)

    # Add characters with styling for month labels
    i = 0
    while i < total_width:
        if month_chars[i] != " ":
            # Find the extent of this month label
            j = i
            while j < total_width and month_chars[j] != " ":
                j += 1
            month_row.append("".join(month_chars[i:j]), style="bold magenta")
            i = j
        else:
            # Find the extent of spaces
            j = i
            while j < total_width and month_chars[j] == " ":
                j += 1
            month_row.append(" " * (j - i))
            i = j

    return month_row


def _build_year_row(
    time_slots: list[pendulum.DateTime],
    slots_to_show: set[int],
    slot_widths: list[int],
    left_column_width: int,
) -> Optional[Text]:
    """
    Build a year header row for month granularity when year rollovers occur.

    The year (YY format) is aligned with the month label below it.

    Args:
        time_slots: List of time slots for the timeline
        slots_to_show: Set of indices for slots that should show headers
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (for padding)

    Returns:
        Rich Text object with year labels, or None if no year changes detected
    """
    # Check if there are any year changes
    years_in_view = set()
    for i, slot in enumerate(time_slots):
        if i in slots_to_show:
            years_in_view.add(slot.year)

    # If only one year, no need for year row
    if len(years_in_view) <= 1:
        return None

    year_row = Text()
    year_row.append(" " * left_column_width)

    prev_year: Optional[int] = None
    prev_was_label = False

    for i, slot in enumerate(time_slots):
        width = slot_widths[i]

        if i in slots_to_show:
            current_year = slot.year

            # Show year label if year changed from previous month
            if prev_year is not None and current_year != prev_year:
                year_label = slot.format("YY")

                # The width already includes space for the separator if prev_was_label
                # We need to align the year with the month label below
                # Month labels are 3 chars (MMM), year labels are 2 chars (YY)
                # Add an extra space before the year to align with month start
                if prev_was_label:
                    # Width includes the leading space for separation
                    # Layout: [separator space] + [alignment space] + YY + [padding]
                    year_row.append(" ")  # Separator space
                    year_row.append(" ")  # Extra space to align with month
                    year_row.append(year_label, style="bold yellow")
                    remaining = (
                        width - 1 - 1 - len(year_label)
                    )  # width - sep - align - label
                    if remaining > 0:
                        year_row.append(" " * remaining)
                else:
                    # No leading separator space
                    # Layout: [alignment space] + YY + [padding]
                    year_row.append(" ")  # Extra space to align with month
                    year_row.append(year_label, style="bold yellow")
                    remaining = width - 1 - len(year_label)  # width - align - label
                    if remaining > 0:
                        year_row.append(" " * remaining)

                prev_was_label = True
            else:
                # No year change, show spaces
                year_row.append(" " * width)
                prev_was_label = False

            prev_year = current_year
        else:
            # Show spaces for slots without headers
            year_row.append(" " * width)
            prev_was_label = False

    return year_row


def _build_timespan_row(
    timespan: Timespan,
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int = 40,
) -> Text:
    """
    Build a row for a single timespan with its description and timeline.

    Args:
        timespan: The timespan to visualize
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers
        left_column_width: Width of the left column (default 40)

    Returns:
        Rich Text object with the timespan row
    """
    row = Text()

    # Add ID and description (left column)
    ts_id_raw = timespan["id"]
    if ts_id_raw is not None:
        ts_id = str(ID_MAP_REPO.associate_id("timespans", ts_id_raw))
    else:
        ts_id = ""
    description = timespan["description"] or "[no description]"
    color = timespan["color"] or "white"

    # Format the left column: "ID Description"
    left_col = f"{ts_id:>3} {description}"
    if len(left_col) > left_column_width:
        left_col = left_col[: left_column_width - 3] + "..."
    else:
        left_col = left_col.ljust(left_column_width)

    row.append(left_col, style=color)

    # Build the timeline visualization
    ts_start = timespan["start"]
    ts_end = timespan["end"]

    if ts_start is None:
        # No start date, fill with empty spaces
        total_width = sum(slot_widths)
        row.append(" " * total_width)
        return row

    ts_start = ts_start.in_tz("local")
    ts_end_local = ts_end.in_tz("local") if ts_end is not None else None

    # Normalize timespan dates based on granularity for inclusive comparison
    # Using start_of(granularity) for start and end_of(granularity) for end
    # ensures the dates include the full period
    if granularity == "day":
        ts_start_normalized = ts_start.start_of("day")
        ts_end_normalized = (
            ts_end_local.end_of("day") if ts_end_local is not None else None
        )
    elif granularity == "week":
        ts_start_normalized = ts_start.start_of("week")
        ts_end_normalized = (
            ts_end_local.end_of("week") if ts_end_local is not None else None
        )
    else:  # month
        ts_start_normalized = ts_start.start_of("month")
        ts_end_normalized = (
            ts_end_local.end_of("month") if ts_end_local is not None else None
        )

    prev_slot_has_label = False
    for i, slot in enumerate(time_slots):
        slot_end = _get_slot_end(slot, granularity)
        width = slot_widths[i]
        current_slot_has_label = i in slots_to_show

        # Determine background style for alternating day columns (only for day granularity)
        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # Check if timespan overlaps with this slot
        if ts_end_normalized is not None:
            # Timespan has an end date
            overlaps = ts_start_normalized <= slot_end and ts_end_normalized >= slot
        else:
            # Timespan has no end date (ongoing)
            overlaps = ts_start_normalized <= slot_end

        # Determine if this is the start or end slot (needed for separator logic)
        is_start = ts_start_normalized >= slot and ts_start_normalized <= slot_end
        is_end = (
            ts_end_normalized is not None
            and ts_end_normalized >= slot
            and ts_end_normalized <= slot_end
        )

        # Handle leading separator space if both current and previous slots have labels
        if current_slot_has_label and prev_slot_has_label:
            # If timespan overlaps and is not starting in this slot, use continuation character
            if overlaps and not is_start:
                row.append("━", style=color)
            else:
                row.append(" ")
            width = width - 1  # Adjust width for the remaining content

        if overlaps:
            if is_start and is_end:
                # Both start and end in this slot - fill entire width with single character
                char = "●"
                row.append(char * width, style=color + bg_style)
            elif is_start:
                # Starts in this slot - use start marker then continuation
                row.append("◄", style=color + bg_style)
                if width > 1:
                    row.append("━" * (width - 1), style=color + bg_style)
            elif is_end:
                # Ends in this slot - use continuation then end marker
                if width > 1:
                    row.append("━" * (width - 1), style=color + bg_style)
                row.append("►", style=color + bg_style)
            else:
                # Continues through this slot - fill entire width with continuation
                char = "━"
                row.append(char * width, style=color + bg_style)
        else:
            # No overlap, use empty spaces for the full width with background
            if bg_style:
                row.append(" " * width, style=bg_style)
            else:
                row.append(" " * width)

        prev_slot_has_label = current_slot_has_label

    return row


def _build_event_row(
    event: Event,
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int = 40,
) -> Text:
    """
    Build a row for a single event with its title and timeline.

    Events are displayed as a square (■) on their start date with the title after.

    Args:
        event: The event to visualize
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        left_column_width: Width of the left column (default 40)

    Returns:
        Rich Text object with the event row
    """
    row = Text()

    # Add ID and title (left column)
    ev_id_raw = event["id"]
    if ev_id_raw is not None:
        ev_id = str(ID_MAP_REPO.associate_id("events", ev_id_raw))
    else:
        ev_id = ""
    title = event["title"] or event["description"] or "[no title]"
    color = event["color"] or "white"

    # Format the left column: "ID Title"
    left_col = f"{ev_id:>3} {title}"
    if len(left_col) > left_column_width:
        left_col = left_col[: left_column_width - 3] + "..."
    else:
        left_col = left_col.ljust(left_column_width)

    row.append(left_col, style=color)

    # Build the timeline visualization
    ev_start = event["start"]
    # Event start is guaranteed to be not None when called from gantt_report
    # due to valid_events filtering
    assert ev_start is not None

    ev_start_local = ev_start.in_tz("local")

    # Normalize event start date based on granularity
    if granularity == "day":
        ev_start_normalized = ev_start_local.start_of("day")
    elif granularity == "week":
        ev_start_normalized = ev_start_local.start_of("week")
    else:  # month
        ev_start_normalized = ev_start_local.start_of("month")

    # Track if previous slot had a label (needed for proper spacing alignment)
    prev_slot_had_label = False

    for i, slot in enumerate(time_slots):
        slot_end = _get_slot_end(slot, granularity)
        width = slot_widths[i]

        # Determine if current slot has a label in the header
        current_slot_has_label = i in slots_to_show

        # Determine background style for alternating day columns (only for day granularity)
        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # Check if event starts in this slot
        is_start_slot = ev_start_normalized >= slot and ev_start_normalized <= slot_end

        # Handle leading separator space if both current and previous slots have labels
        if current_slot_has_label and prev_slot_had_label:
            row.append(" ")
            width = width - 1  # Adjust width for the remaining content

        if is_start_slot:
            # Place marker at start
            row.append("■", style=color + bg_style)
            # Fill remaining width with spaces
            if width > 1:
                row.append(" " * (width - 1), style=bg_style if bg_style else None)
        else:
            # No marker, use empty spaces for the full width with background
            if bg_style:
                row.append(" " * width, style=bg_style)
            else:
                row.append(" " * width)

        prev_slot_had_label = current_slot_has_label

    return row


def _get_slot_end(
    slot: pendulum.DateTime, granularity: GranularityType
) -> pendulum.DateTime:
    """
    Get the end datetime for a given time slot.

    Args:
        slot: The start of the time slot
        granularity: "day", "week", or "month"

    Returns:
        The end datetime of the slot
    """
    if granularity == "day":
        return slot.end_of("day")
    elif granularity == "week":
        return slot.end_of("week")
    else:  # granularity == "month"
        return slot.end_of("month")


def _get_date_format(granularity: GranularityType) -> str:
    """
    Get the appropriate date format string for the granularity.

    Args:
        granularity: "day", "week", or "month"

    Returns:
        Format string for pendulum's format() method
    """
    if granularity == "day":
        return "MM/DD"
    elif granularity == "week":
        return "MM/DD"
    else:  # granularity == "month"
        return "MMM YY"


def _format_task_left_column(
    task: Task,
    all_tasks: list[Task],
    left_column_width: int,
    indent: int = 0,
) -> tuple[str, str]:
    """
    Format the left column text for a task row.

    Args:
        task: The task to format
        all_tasks: List of all tasks (for state calculation)
        left_column_width: Width of the left column
        indent: Number of spaces to indent (default 0 for standalone, 4 for timespan tasks)

    Returns:
        Tuple of (formatted_text, style) where formatted_text is padded/truncated to fit
        and style is the color to apply
    """
    task_id_raw = task.get("id")
    if task_id_raw is not None:
        task_id = str(ID_MAP_REPO.associate_id("tasks", task_id_raw))
    else:
        task_id = ""
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

    # Format the left column
    indent_str = " " * indent
    if indent > 0:
        # Timespan-associated task: "    [state] ID description"
        left_col = f"{indent_str}[{state}] {task_id:>3} {description}"
    else:
        # Standalone task: "[state] ID description"
        left_col = f"[{state}] {task_id:>3} {description}"

    # Truncate with ellipsis if too long, otherwise pad to width
    if len(left_col) > left_column_width:
        left_col = left_col[: left_column_width - 3] + "..."
    else:
        left_col = left_col.ljust(left_column_width)

    return left_col, task_style


def _build_task_rows(
    timespan_id: Optional[EntityId],
    tasks: list[Task],
    left_column_width: int,
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
) -> list[Text]:
    """
    Build rows for tasks associated with a timespan.

    Tasks with due dates show a filled circle (●) on their due date.
    Tasks with scheduled dates show a hollow circle (○) on their scheduled date.

    Only tasks with due or scheduled dates within the visible timeline range are shown.

    Args:
        timespan_id: The ID of the timespan
        tasks: List of all tasks
        left_column_width: Width of the left column for padding
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers

    Returns:
        List of Rich Text objects with task rows
    """
    if timespan_id is None:
        return []

    # Get the timeline range from time_slots
    if not time_slots:
        return []

    start_local = time_slots[0]
    end_local = _get_slot_end(time_slots[-1], granularity)

    # Filter tasks that belong to this timespan, are not deleted,
    # and have due or scheduled dates within the visible timeline range
    timespan_tasks = []
    for task in tasks:
        if task["timespan_id"] == timespan_id and task["deleted"] is None:
            # Check if the task has a due or scheduled date within the timeline range
            task_in_range = False
            if task["due"] is not None:
                task_date = task["due"].in_tz("local")
                if task_date >= start_local and task_date <= end_local:
                    task_in_range = True
            if not task_in_range and task["scheduled"] is not None:
                task_date = task["scheduled"].in_tz("local")
                if task_date >= start_local and task_date <= end_local:
                    task_in_range = True

            # Include the task if it has a date in range, or if it has no dates at all
            # (tasks without dates are shown to provide context for the timespan)
            if task_in_range or (task["due"] is None and task["scheduled"] is None):
                timespan_tasks.append(task)

    # Sort timespan tasks by due date (or scheduled date if no due) ascending
    timespan_tasks.sort(
        key=lambda t: t["due"] or t["scheduled"] or pendulum.DateTime.min
    )

    if not timespan_tasks:
        return []

    task_rows = []
    for task in timespan_tasks:
        # Format the left column using the shared abstraction
        left_col, task_style = _format_task_left_column(
            task, tasks, left_column_width, indent=4
        )

        line = Text()
        line.append(left_col, style=task_style)

        # Build the timeline visualization
        due_date = task.get("due")
        scheduled_date = task.get("scheduled")

        # Normalize dates based on granularity
        due_normalized = None
        scheduled_normalized = None

        if due_date is not None:
            due_local = due_date.in_tz("local")
            if granularity == "day":
                due_normalized = due_local.start_of("day")
            elif granularity == "week":
                due_normalized = due_local.start_of("week")
            else:  # month
                due_normalized = due_local.start_of("month")

        if scheduled_date is not None:
            scheduled_local = scheduled_date.in_tz("local")
            if granularity == "day":
                scheduled_normalized = scheduled_local.start_of("day")
            elif granularity == "week":
                scheduled_normalized = scheduled_local.start_of("week")
            else:  # month
                scheduled_normalized = scheduled_local.start_of("month")

        # Track if previous slot had a label (needed for proper spacing alignment)
        prev_slot_had_label = False

        for i, slot in enumerate(time_slots):
            slot_end = _get_slot_end(slot, granularity)
            width = slot_widths[i]

            # Determine if current slot has a label in the header
            current_slot_has_label = i in slots_to_show

            # Determine background style for alternating day columns (only for day granularity)
            bg_style = ""
            if granularity == "day" and i % 2 == 1:
                bg_style = " on grey23"

            # Check if due or scheduled date is in this slot
            is_due_slot = (
                due_normalized is not None
                and due_normalized >= slot
                and due_normalized <= slot_end
            )
            is_scheduled_slot = (
                scheduled_normalized is not None
                and scheduled_normalized >= slot
                and scheduled_normalized <= slot_end
            )

            # Handle leading separator space if both current and previous slots have labels
            if current_slot_has_label and prev_slot_had_label:
                line.append(" ")
                width = width - 1  # Adjust width for the remaining content

            if is_due_slot or is_scheduled_slot:
                # Place marker at start
                # Due date takes priority if both are on the same slot
                if is_due_slot:
                    line.append("●", style=task_style + bg_style)
                else:
                    line.append("○", style=task_style + bg_style)
                # Fill remaining width with spaces
                if width > 1:
                    line.append(" " * (width - 1), style=bg_style if bg_style else None)
            else:
                # No marker, use empty spaces for the full width with background
                if bg_style:
                    line.append(" " * width, style=bg_style)
                else:
                    line.append(" " * width)

            prev_slot_had_label = current_slot_has_label

        task_rows.append(line)

    return task_rows


def _build_standalone_task_row(
    task: Task,
    all_tasks: list[Task],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int = 40,
) -> Text:
    """
    Build a row for a standalone task (not associated with a timespan) with its timeline markers.

    Tasks with due dates show a filled circle (●) on their due date.
    Tasks with scheduled dates show a hollow circle (○) on their scheduled date.

    Args:
        task: The task to visualize
        all_tasks: List of all tasks (for state calculation)
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers
        left_column_width: Width of the left column (default 40)

    Returns:
        Rich Text object with the task row
    """
    row = Text()

    # Format the left column using the shared abstraction
    left_col, task_style = _format_task_left_column(
        task, all_tasks, left_column_width, indent=0
    )

    row.append(left_col, style=task_style)

    # Build the timeline visualization
    due_date = task.get("due")
    scheduled_date = task.get("scheduled")

    # Normalize dates based on granularity
    due_normalized = None
    scheduled_normalized = None

    if due_date is not None:
        due_local = due_date.in_tz("local")
        if granularity == "day":
            due_normalized = due_local.start_of("day")
        elif granularity == "week":
            due_normalized = due_local.start_of("week")
        else:  # month
            due_normalized = due_local.start_of("month")

    if scheduled_date is not None:
        scheduled_local = scheduled_date.in_tz("local")
        if granularity == "day":
            scheduled_normalized = scheduled_local.start_of("day")
        elif granularity == "week":
            scheduled_normalized = scheduled_local.start_of("week")
        else:  # month
            scheduled_normalized = scheduled_local.start_of("month")

    # Track if previous slot had a label (needed for proper spacing alignment)
    prev_slot_had_label = False

    for i, slot in enumerate(time_slots):
        slot_end = _get_slot_end(slot, granularity)
        width = slot_widths[i]

        # Determine if current slot has a label in the header
        current_slot_has_label = i in slots_to_show

        # Determine background style for alternating day columns (only for day granularity)
        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # Check if due or scheduled date is in this slot
        is_due_slot = (
            due_normalized is not None
            and due_normalized >= slot
            and due_normalized <= slot_end
        )
        is_scheduled_slot = (
            scheduled_normalized is not None
            and scheduled_normalized >= slot
            and scheduled_normalized <= slot_end
        )

        # Handle leading separator space if both current and previous slots have labels
        if current_slot_has_label and prev_slot_had_label:
            row.append(" ")
            width = width - 1  # Adjust width for the remaining content

        if is_due_slot or is_scheduled_slot:
            # Place marker at start
            # Due date takes priority if both are on the same slot
            if is_due_slot:
                row.append("●", style=task_style + bg_style)
            else:
                row.append("○", style=task_style + bg_style)
            # Fill remaining width with spaces
            if width > 1:
                row.append(" " * (width - 1), style=bg_style if bg_style else None)
        else:
            # No marker, use empty spaces for the full width with background
            if bg_style:
                row.append(" " * width, style=bg_style)
            else:
                row.append(" " * width)

        prev_slot_had_label = current_slot_has_label

    return row


def _build_tracker_row(
    tracker: Tracker,
    entries: list[Entry],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int = 40,
) -> Text:
    """
    Build a row for a single tracker with its heatmap visualization.

    Symbols:
    - "X" for checkin trackers with entries
    - "." "o" "O" "#" for intensity levels 1-4 (quantitative/multi_select)
    - " " for no entry
    - "-" for future dates

    Args:
        tracker: The tracker to visualize
        entries: All entries (will be filtered to this tracker)
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers
        left_column_width: Width of the left column (default 40)

    Returns:
        Rich Text object with the tracker row
    """
    # Add ID and name (left column)
    tracker_id_raw = tracker["id"]
    if tracker_id_raw is not None:
        tracker_id = str(ID_MAP_REPO.associate_id("trackers", tracker_id_raw))
    else:
        tracker_id = ""
    name = tracker["name"] or "[no name]"
    color = tracker["color"] or "white"
    value_type = tracker["value_type"]

    left_column_text = f"{tracker_id:>3} {name}"

    # Get timeline data for this tracker
    timeline_data = get_tracker_timeline_data(tracker, entries, time_slots, granularity)

    def symbol_callback(slot_data: dict, is_future: bool) -> tuple[str, str]:
        return get_tracker_symbol(slot_data, is_future, value_type, color)

    return build_heatmap_row(
        left_column_text=left_column_text,
        left_column_style=color,
        timeline_data=timeline_data,
        time_slots=time_slots,
        granularity=granularity,
        slot_widths=slot_widths,
        slots_to_show=slots_to_show,
        left_column_width=left_column_width,
        get_symbol=symbol_callback,
    )


def _build_tasks_heatmap_row(
    label: str,
    color: str,
    tasks: list[Task],
    time_audits: list[TimeAudit],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int = 40,
) -> Text:
    """
    Build a row for the tasks heatmap visualization.

    Shows activity markers for dates where tasks were completed or time audits exist.

    Symbols:
    - "." "o" "O" "#" for intensity levels 1-4 based on activity count
    - " " for no activity
    - "-" for future dates

    Args:
        label: Text to display in the left column
        color: Color for the left column and markers
        tasks: List of tasks (pre-filtered)
        time_audits: List of time audits (pre-filtered)
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers
        left_column_width: Width of the left column (default 40)

    Returns:
        Rich Text object with the heatmap row
    """
    # Get timeline data for tasks and time audits
    timeline_data = get_tasks_timeline_data(tasks, time_audits, time_slots, granularity)

    def symbol_callback(slot_data: dict, is_future: bool) -> tuple[str, str]:
        return get_tasks_symbol(slot_data, is_future, color)

    return build_heatmap_row(
        left_column_text=label,
        left_column_style=color,
        timeline_data=timeline_data,
        time_slots=time_slots,
        granularity=granularity,
        slot_widths=slot_widths,
        slots_to_show=slots_to_show,
        left_column_width=left_column_width,
        get_symbol=symbol_callback,
    )
