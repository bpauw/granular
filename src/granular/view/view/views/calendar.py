# SPDX-License-Identifier: MIT

from typing import Optional

import pendulum
from rich import box
from rich.columns import Columns
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from granular.color import (
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
from granular.view.view.util import task_state
from granular.view.view.views.agenda_core import (
    render_agenda_day,
    render_day_header,
)
from granular.view.view.views.header import header


def calendar_day_view(
    active_context: str,
    report_name: str,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    date: Optional[pendulum.DateTime] = None,
    granularity: int = 60,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_time_audits: bool = True,
    start_hour: int = 0,
    start_minute: int = 0,
    end_hour: int = 23,
    end_minute: int = 59,
    trackers: Optional[list[Tracker]] = None,
    entries: Optional[list[Entry]] = None,
    show_trackers: bool = False,
) -> None:
    """
    Display a vertical timeline calendar showing time audits and events for a given day.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        time_audits: List of time audits to display
        events: List of events to display
        tasks: List of tasks to display
        date: The date to display (defaults to today in local timezone)
        granularity: Time interval in minutes (60, 30, or 15)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        show_time_audits: Whether to show time audits (defaults to True)
        start_hour: Starting hour for the timeline (default 0)
        start_minute: Starting minute for the timeline (default 0)
        end_hour: Ending hour for the timeline (default 23)
        end_minute: Ending minute for the timeline (default 59)
        trackers: List of trackers to display (defaults to None)
        entries: List of tracker entries to display (defaults to None)
        show_trackers: Whether to show tracker entries as pips (defaults to False)
    """
    header(active_context, report_name)

    console = Console()

    # Use today if no date specified
    if date is None:
        date = pendulum.now("local").start_of("day")
    else:
        date = date.in_tz("local").start_of("day")

    # Filter time audits, events, and tasks for this day
    filtered_audits = (
        _filter_audits_for_day(time_audits, date) if show_time_audits else []
    )
    filtered_events = _filter_events_for_day(events, date)
    filtered_tasks = _filter_tasks_for_scheduled_or_due(
        tasks, date, show_scheduled_tasks, show_due_tasks
    )

    # Filter tracker entries for this day
    filtered_entries: list[Entry] = []
    if show_trackers and entries is not None:
        filtered_entries = _filter_entries_for_day(entries, date)

    # Display the date header
    date_str = date.format("YYYY-MM-DD ddd")
    console.print(f"\n[bold]{date_str}[/bold]\n")

    # Separate all-day events from timed events
    all_day_events = [e for e in filtered_events if e["all_day"]]
    timed_events = [e for e in filtered_events if not e["all_day"]]

    # Display tasks section (scheduled or due)
    if filtered_tasks:
        for task in filtered_tasks:
            description = task.get("description", "[no description]")
            if description is None:
                description = "[no description]"
            color = task.get("color", "white")
            if color is None:
                color = "white"

            state = task_state(task, tasks)
            line = Text()
            line.append(f"{state} ", style=color)
            line.append(description, style=color)

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
        console.print()

    # Display all-day events section
    if all_day_events:
        for event in all_day_events:
            title = event.get("title", "[no title]")
            if title is None:
                title = "[no title]"
            color = event.get("color", "white")
            if color is None:
                color = "white"
            line = Text()
            line.append("■ ", style=color)
            line.append(title, style=color)
            console.print(line)
        console.print()

    # Create timeline with only timed events
    day_start = date
    day_end = date.end_of("day")
    _render_timeline(
        console,
        filtered_audits,
        timed_events,
        day_start,
        day_end,
        granularity,
        start_hour,
        start_minute,
        end_hour,
        end_minute,
        trackers=trackers if trackers is not None else [],
        entries=filtered_entries,
    )


def calendar_days_view(
    active_context: str,
    report_name: str,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    start_date: Optional[pendulum.DateTime] = None,
    num_days: int = 7,
    day_width: int = 30,
    granularity: int = 60,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_time_audits: bool = True,
    start_hour: int = 0,
    start_minute: int = 0,
    end_hour: int = 23,
    end_minute: int = 59,
    trackers: Optional[list[Tracker]] = None,
    entries: Optional[list[Entry]] = None,
    show_trackers: bool = False,
) -> None:
    """
    Display a multi-day calendar showing time audits and events horizontally across days.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        time_audits: List of time audits to display
        events: List of events to display
        tasks: List of tasks to display
        start_date: Optional start date (defaults to today in local timezone)
        num_days: Number of days to display (defaults to 7)
        day_width: Width of each day column in characters (defaults to 30)
        granularity: Time interval in minutes (60, 30, or 15)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        show_time_audits: Whether to show time audits (defaults to True)
        start_hour: Starting hour for the timeline (default 0)
        start_minute: Starting minute for the timeline (default 0)
        end_hour: Ending hour for the timeline (default 23)
        end_minute: Ending minute for the timeline (default 59)
        trackers: List of trackers to display (defaults to None)
        entries: List of tracker entries to display (defaults to None)
        show_trackers: Whether to show tracker entries as pips (defaults to False)
    """
    header(active_context, report_name)

    console = Console()

    # Use provided start_date or default to today
    if start_date is None:
        start_date = pendulum.now("local").start_of("day")
    else:
        start_date = start_date.in_tz("local").start_of("day")

    # Generate day columns
    day_columns: list[RenderableType] = []
    for day_offset in range(num_days):
        current_date = start_date.add(days=day_offset)
        filtered_audits = (
            _filter_audits_for_day(time_audits, current_date)
            if show_time_audits
            else []
        )
        filtered_events = _filter_events_for_day(events, current_date)
        filtered_tasks = _filter_tasks_for_scheduled_or_due(
            tasks, current_date, show_scheduled_tasks, show_due_tasks
        )

        # Filter tracker entries for this day
        filtered_entries: list[Entry] = []
        if show_trackers and entries is not None:
            filtered_entries = _filter_entries_for_day(entries, current_date)

        # Create day column
        day_column = _render_day_column(
            current_date,
            filtered_audits,
            filtered_events,
            filtered_tasks,
            tasks,
            day_width,
            granularity,
            show_scheduled_tasks,
            show_due_tasks,
            start_hour,
            start_minute,
            end_hour,
            end_minute,
            trackers=trackers if trackers is not None else [],
            entries=filtered_entries,
        )
        day_columns.append(day_column)

    # Render columns side by side
    console.print()
    console.print(Columns(day_columns, equal=False, expand=False, padding=(0, 0)))
    console.print()


def calendar_week_view(
    active_context: str,
    report_name: str,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    start_date: Optional[pendulum.DateTime] = None,
    num_days: int = 7,
    day_width: int = 30,
    granularity: int = 60,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    start_hour: int = 0,
    start_minute: int = 0,
    end_hour: int = 23,
    end_minute: int = 59,
) -> None:
    """
    Display a multi-day calendar showing time audits and events horizontally across days.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        time_audits: List of time audits to display
        events: List of events to display
        tasks: List of tasks to display
        start_date: The start date (defaults to beginning of current week)
        num_days: Number of days to display (defaults to 7)
        day_width: Width of each day column in characters (defaults to 30)
        granularity: Time interval in minutes (60, 30, or 15)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        start_hour: Starting hour for the timeline (default 0)
        start_minute: Starting minute for the timeline (default 0)
        end_hour: Ending hour for the timeline (default 23)
        end_minute: Ending minute for the timeline (default 59)
    """
    header(active_context, report_name)

    console = Console()

    # Use start of current week if no date specified
    if start_date is None:
        start_date = pendulum.now("local").start_of("week")
    else:
        start_date = start_date.in_tz("local").start_of("day")

    # Generate day columns
    day_columns: list[RenderableType] = []
    for day_offset in range(num_days):
        current_date = start_date.add(days=day_offset)
        filtered_audits = _filter_audits_for_day(time_audits, current_date)
        filtered_events = _filter_events_for_day(events, current_date)
        filtered_tasks = _filter_tasks_for_scheduled_or_due(
            tasks, current_date, show_scheduled_tasks, show_due_tasks
        )

        # Create day column
        day_column = _render_day_column(
            current_date,
            filtered_audits,
            filtered_events,
            filtered_tasks,
            tasks,
            day_width,
            granularity,
            show_scheduled_tasks,
            show_due_tasks,
            start_hour,
            start_minute,
            end_hour,
            end_minute,
        )
        day_columns.append(day_column)

    # Render columns side by side
    console.print()
    console.print(Columns(day_columns, equal=False, expand=False, padding=(0, 0)))
    console.print()


def calendar_month_view(
    active_context: str,
    report_name: str,
    tasks: list[Task],
    events: list[Event],
    date: Optional[pendulum.DateTime] = None,
    cell_width: int = 20,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_all_day_events: bool = True,
    show_non_all_day_events: bool = False,
) -> None:
    """
    Display a monthly calendar grid showing tasks by their scheduled and due dates, and events.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        tasks: List of tasks to display
        events: List of events to display
        date: The month to display (defaults to current month in local timezone)
        cell_width: Width of each day cell in characters (defaults to 20)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        show_all_day_events: Whether to show all-day events (defaults to True)
        show_non_all_day_events: Whether to show non-all-day events (defaults to False)
    """
    header(active_context, report_name)

    console = Console()

    # Use current month if no date specified
    if date is None:
        date = pendulum.now("local").start_of("month")
    else:
        date = date.in_tz("local").start_of("month")

    month_end = date.end_of("month")

    # Group tasks by scheduled and due dates
    scheduled_tasks_by_date = _get_tasks_by_scheduled_date(tasks, date, month_end)
    due_tasks_by_date = _get_tasks_by_due_date(tasks, date, month_end)

    # Group all-day events by date
    all_day_events_by_date = _get_all_day_events_by_date(events, date, month_end)

    # Group non-all-day events by date
    non_all_day_events_by_date = _get_non_all_day_events_by_date(
        events, date, month_end
    )

    # Display month and year header
    month_year_str = date.format("MMMM YYYY")
    console.print(f"\n[bold]{month_year_str}[/bold]\n")

    # Render the month grid
    month_grid = _render_month_grid(
        date,
        scheduled_tasks_by_date,
        due_tasks_by_date,
        all_day_events_by_date,
        non_all_day_events_by_date,
        tasks,
        cell_width,
        show_scheduled_tasks,
        show_due_tasks,
        show_all_day_events,
        show_non_all_day_events,
    )
    console.print(month_grid)
    console.print()


def calendar_quarter_view(
    active_context: str,
    report_name: str,
    tasks: list[Task],
    events: list[Event],
    date: Optional[pendulum.DateTime] = None,
    cell_width: int = 15,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_all_day_events: bool = True,
    show_non_all_day_events: bool = False,
) -> None:
    """
    Display a quarterly calendar showing 3 months with tasks by their scheduled and due dates, and events.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        tasks: List of tasks to display
        events: List of events to display
        date: The first month of the quarter to display (defaults to current quarter)
        cell_width: Width of each day cell in characters (defaults to 15)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        show_all_day_events: Whether to show all-day events (defaults to True)
        show_non_all_day_events: Whether to show non-all-day events (defaults to False)
    """
    header(active_context, report_name)

    console = Console()

    # Use current quarter if no date specified
    if date is None:
        date = pendulum.now("local")
    else:
        date = date.in_tz("local")

    # Calculate start of quarter (Q1: Jan, Q2: Apr, Q3: Jul, Q4: Oct)
    quarter = ((date.month - 1) // 3) * 3 + 1
    quarter_start = date.start_of("year").add(months=quarter - 1).start_of("month")

    # Display quarter and year header
    quarter_num = ((quarter - 1) // 3) + 1
    quarter_str = f"Q{quarter_num} {quarter_start.year}"
    console.print(f"\n[bold]{quarter_str}[/bold]\n")

    # Generate 3 months for the quarter
    month_panels: list[RenderableType] = []

    for month_offset in range(3):
        current_month = quarter_start.add(months=month_offset)
        month_end = current_month.end_of("month")

        # Group tasks by scheduled and due dates for this month
        scheduled_tasks_by_date = _get_tasks_by_scheduled_date(
            tasks, current_month, month_end
        )
        due_tasks_by_date = _get_tasks_by_due_date(tasks, current_month, month_end)

        # Group all-day events by date for this month
        all_day_events_by_date = _get_all_day_events_by_date(
            events, current_month, month_end
        )

        # Group non-all-day events by date for this month
        non_all_day_events_by_date = _get_non_all_day_events_by_date(
            events, current_month, month_end
        )

        # Create month grid
        month_grid = _render_month_grid(
            current_month,
            scheduled_tasks_by_date,
            due_tasks_by_date,
            all_day_events_by_date,
            non_all_day_events_by_date,
            tasks,
            cell_width,
            show_scheduled_tasks,
            show_due_tasks,
            show_all_day_events,
            show_non_all_day_events,
        )

        # Wrap in panel with month name
        month_name = current_month.format("MMMM")
        month_panel = Panel(
            month_grid,
            title=month_name,
            border_style="bright_black",
            padding=(0, 1),
        )
        month_panels.append(month_panel)

    # Display months side by side
    console.print(Columns(month_panels, equal=False, expand=False, padding=(0, 2)))
    console.print()


def calendar_agenda_days_view(
    active_context: str,
    report_name: str,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    timespans: list[Timespan],
    logs: list[Log],
    notes: list[Note],
    num_days: int = 7,
    start_date: Optional[pendulum.DateTime] = None,
    only_active_days: bool = False,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_events: bool = True,
    show_timespans: bool = True,
    show_logs: bool = False,
    show_notes: bool = False,
    show_time_audits: bool = False,
    limit_note_lines: Optional[int] = None,
    time_audit_meta_color: str = TIME_AUDIT_META_COLOR,
    log_meta_color: str = LOG_META_COLOR,
    note_meta_color: str = NOTE_META_COLOR,
) -> None:
    """
    Display an agenda view showing events, tasks, and active timespans as a list grouped by day.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        time_audits: List of time audits to display
        events: List of events to display
        tasks: List of tasks to display
        timespans: List of timespans to display
        logs: List of logs to display
        notes: List of notes to display
        num_days: Number of days to display (defaults to 7)
        start_date: Start date for the agenda (defaults to today)
        only_active_days: Whether to show only days with activity (defaults to False)
        show_scheduled_tasks: Whether to show scheduled tasks (defaults to True)
        show_due_tasks: Whether to show due tasks (defaults to True)
        show_events: Whether to show calendar events (defaults to True)
        show_timespans: Whether to show active timespans (defaults to True)
        show_logs: Whether to show log chronology (defaults to False)
        show_notes: Whether to show note chronology (defaults to False)
        show_time_audits: Whether to show time audit chronology (defaults to False)
        limit_note_lines: Maximum number of lines to display per note (defaults to None, showing all lines)
        time_audit_meta_color: Color for time audit metadata (defaults to "dim")
        log_meta_color: Color for log metadata (defaults to "dim")
        note_meta_color: Color for note metadata (defaults to "dim")
    """
    header(active_context, report_name)

    console = Console()

    # Use provided start_date or default to today (current date at beginning of day)
    if start_date is None:
        start_date = pendulum.now("local").start_of("day")
    else:
        start_date = start_date.in_tz("local").start_of("day")

    # Filter out deleted tasks, events, timespans, notes, and logs
    tasks = [task for task in tasks if task["deleted"] is None]
    events = [event for event in events if event["deleted"] is None]
    timespans = [timespan for timespan in timespans if timespan["deleted"] is None]
    notes = [note for note in notes if note["deleted"] is None]
    logs = [log for log in logs if log["deleted"] is None]

    # Iterate through each day using the shared renderer
    for day_offset in range(num_days):
        current_date = start_date.add(days=day_offset)
        rendered = render_agenda_day(
            console,
            current_date,
            time_audits,
            events,
            tasks,
            timespans,
            logs,
            notes,
            show_scheduled_tasks=show_scheduled_tasks,
            show_due_tasks=show_due_tasks,
            show_events=show_events,
            show_timespans=show_timespans,
            show_logs=show_logs,
            show_notes=show_notes,
            show_time_audits=show_time_audits,
            limit_note_lines=limit_note_lines,
            time_audit_meta_color=time_audit_meta_color,
            log_meta_color=log_meta_color,
            note_meta_color=note_meta_color,
        )

        # If showing all days and this day had no content, render just the header
        if not rendered and not only_active_days:
            render_day_header(console, current_date)

    console.print()


def _filter_audits_for_day(
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


def _filter_events_for_day(events: list[Event], date: pendulum.DateTime) -> list[Event]:
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


def _filter_entries_for_day(
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


def _render_day_column(
    date: pendulum.DateTime,
    time_audits: list[TimeAudit],
    events: list[Event],
    tasks: list[Task],
    all_tasks: list[Task],
    day_width: int = 30,
    granularity: int = 60,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    start_hour: int = 0,
    start_minute: int = 0,
    end_hour: int = 23,
    end_minute: int = 59,
    trackers: Optional[list[Tracker]] = None,
    entries: Optional[list[Entry]] = None,
) -> Panel:
    """
    Render a single day as a panel with timeline.

    Args:
        date: The date to render (start of day in local timezone)
        time_audits: Time audits for this day
        events: Events for this day
        tasks: Tasks for this day (filtered)
        all_tasks: All tasks (for checking clones)
        day_width: Width of the day column in characters
        granularity: Time interval in minutes (60, 30, or 15)
        show_scheduled_tasks: Whether to show scheduled tasks
        show_due_tasks: Whether to show due tasks
        start_hour: Starting hour for the timeline (default 0)
        start_minute: Starting minute for the timeline (default 0)
        end_hour: Ending hour for the timeline (default 23)
        end_minute: Ending minute for the timeline (default 59)
        trackers: List of trackers (defaults to None)
        entries: List of tracker entries for this day (defaults to None)

    Returns:
        A Panel containing the day's timeline
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    # Build tracker lookup for getting tracker info from entry
    tracker_by_id: dict[EntityId, Tracker] = {}
    if trackers is not None:
        for tracker in trackers:
            if tracker["id"] is not None:
                tracker_by_id[tracker["id"]] = tracker

    # Build the timeline content
    content_lines: list[Text] = []

    # Separate all-day events from timed events
    all_day_events = [e for e in events if e["all_day"]]
    timed_events = [e for e in events if not e["all_day"]]

    # Add tasks section if any exist (scheduled or due)
    if tasks:
        for task in tasks:
            description = task.get("description", "[no description]")
            if description is None:
                description = "[no description]"
            color = task.get("color", "white")
            if color is None:
                color = "white"

            state = task_state(task, all_tasks)

            # Determine label based on scheduled/due status
            label = ""
            if show_scheduled_tasks and task["scheduled"] is not None:
                task_scheduled_local = task["scheduled"].in_tz("local").start_of("day")
                if task_scheduled_local >= date and task_scheduled_local <= date.end_of(
                    "day"
                ):
                    label = "S "
            if show_due_tasks and task["due"] is not None:
                task_due_local = task["due"].in_tz("local").start_of("day")
                if task_due_local >= date and task_due_local <= date.end_of("day"):
                    if label:
                        label = "S/D "
                    else:
                        label = "D "

            # Calculate max length including label
            # day_width - borders (2) - padding (2) - emoji (~2) - state space (1) - label (varies)
            label_len = len(label)
            max_desc_len = day_width - 7 - label_len
            if len(description) > max_desc_len:
                description = description[: max_desc_len - 3] + "..."

            task_line = Text()
            task_line.append(f"{state} ", style=color)
            if label:
                task_line.append(label, style="dim")
            task_line.append(description, style=color)
            content_lines.append(task_line)

        # Add separator line after tasks
        separator = Text("─" * (day_width - 4), style="dim")
        content_lines.append(separator)

    # Add all-day events section if any exist
    if all_day_events:
        for event in all_day_events:
            title = event.get("title", "[no title]")
            if title is None:
                title = "[no title]"
            color = event.get("color", "white")
            if color is None:
                color = "white"

            # Calculate max length: day_width - borders (2) - padding (2) - square (1) - space (1)
            max_title_len = day_width - 6
            if len(title) > max_title_len:
                title = title[: max_title_len - 3] + "..."

            event_line = Text()
            event_line.append("■ ", style=color)
            event_line.append(title, style=color)
            content_lines.append(event_line)

        # Add separator line after all-day events
        separator = Text("─" * (day_width - 4), style="dim")
        content_lines.append(separator)

    # Calculate start and end minutes from midnight
    start_minutes_from_midnight = start_hour * 60 + start_minute
    end_minutes_from_midnight = end_hour * 60 + end_minute

    # Calculate number of time slots based on granularity and time range
    # Round start down to nearest granularity boundary
    start_slot_minutes = (start_minutes_from_midnight // granularity) * granularity
    # Round end up to nearest granularity boundary
    end_slot_minutes = (
        (end_minutes_from_midnight + granularity - 1) // granularity
    ) * granularity
    num_slots = (end_slot_minutes - start_slot_minutes) // granularity

    # Check if this is today and get current time slot
    today = pendulum.now("local").start_of("day")
    is_today = date == today
    current_time_slot = _get_current_time_slot(granularity) if is_today else None

    for slot_index in range(num_slots):
        slot_time = day_start.add(minutes=start_slot_minutes + slot_index * granularity)
        time_str = slot_time.format("HH:mm")
        slot_end = slot_time.add(minutes=granularity)

        active_audits = []
        for audit in time_audits:
            audit_start = audit["start"].in_tz("local") if audit["start"] else None
            audit_end: pendulum.DateTime = (
                audit["end"].in_tz("local") if audit["end"] else day_end
            )

            if audit_start is None:
                continue

            # Check if audit overlaps with this time slot
            if audit_start < slot_end and audit_end > slot_time:
                active_audits.append(audit)

        # Find active timed events for this time slot (all-day events are not included)
        active_events = []
        for event in timed_events:
            event_start = event["start"].in_tz("local")
            event_end = (
                event["end"].in_tz("local")
                if event["end"] is not None
                else event_start.add(hours=1)
            )

            # Check if event overlaps with this time slot
            if event_start < slot_end and event_end > slot_time:
                active_events.append(event)

        # Build the time slot line
        line = Text()
        # Highlight the time if it matches the current time slot
        if current_time_slot and time_str == current_time_slot:
            line.append(f"{time_str} ", style="bold black on bright_cyan")
        # Highlight lunch time (12:00-12:59, not including 13:00)
        elif slot_time.hour == 12:
            line.append(f"{time_str} ", style="bold black on yellow")
        else:
            line.append(f"{time_str} ", style="dim")
        line.append("│ ", style="bright_black")

        # Calculate available width for descriptions
        # day_width - panel padding (2) - borders (2) - time (6) - separator (2)
        available_width = day_width - 12

        # Display audit information and events on the same line
        if active_audits:
            for i, audit in enumerate(active_audits):
                if i > 0:
                    line.append(" ")

                audit_start = audit["start"].in_tz("local") if audit["start"] else None
                audit_end_optional = (
                    audit["end"].in_tz("local") if audit["end"] else None
                )

                color = audit.get("color", "white")
                if color is None:
                    color = "white"

                # Check if this time slot contains the start or end of the audit
                show_desc = False
                if audit_start and audit_start >= slot_time and audit_start < slot_end:
                    show_desc = True
                elif (
                    audit_end_optional
                    and audit_end_optional >= slot_time
                    and audit_end_optional < slot_end
                ):
                    show_desc = True

                if show_desc:
                    desc = audit.get("description", "")
                    if desc is None:
                        desc = "[no desc]"

                    # Calculate remaining space based on current content length
                    # (excluding time marker and separator which are always 8 chars: "00:00 │ ")
                    current_line_len = len(line.plain)
                    content_len = current_line_len - 8  # Remove time and separator
                    remaining_space = available_width - content_len

                    # We need 2 chars for "█ " that we're about to add
                    space_for_block_and_space = 2

                    # Check if there are any future audits or events that need space
                    num_future_audits = len(active_audits) - i - 1
                    num_events = len(active_events)

                    # If this is the last audit and there are no events, use all remaining space
                    if num_future_audits == 0 and num_events == 0:
                        max_desc_len = remaining_space - space_for_block_and_space
                    else:
                        # Reserve minimal space for future content
                        min_space_for_future_audits = (
                            num_future_audits * 2 if num_future_audits > 0 else 0
                        )
                        min_space_for_events = 2 if num_events > 0 else 0

                        max_desc_len = max(
                            0,
                            remaining_space
                            - space_for_block_and_space
                            - min_space_for_future_audits
                            - min_space_for_events,
                        )

                    if len(desc) > max_desc_len:
                        if max_desc_len > 3:
                            desc = desc[: max_desc_len - 3] + "..."
                        else:
                            desc = desc[:max_desc_len] if max_desc_len > 0 else ""

                    line.append("█ ", style=color)
                    if desc:  # Only append if there's description left
                        line.append(desc, style=color)
                else:
                    line.append("█", style=color)

        # Add event indicators after audits
        if active_events:
            if active_audits:
                line.append("  ")  # Add spacing between audits and events

            for event_index, event in enumerate(active_events):
                if event_index > 0:
                    line.append(" ")

                event_start = event["start"].in_tz("local")
                event_end = (
                    event["end"].in_tz("local")
                    if event["end"] is not None
                    else event_start.add(hours=1)
                )

                color = event.get("color", "white")
                if color is None:
                    color = "white"

                # Check if this is the start of the event to show title
                show_title = event_start >= slot_time and event_start < slot_end

                if show_title:
                    title = event.get("title", "")
                    if title is None or title == "":
                        title = "[no title]"

                    # Calculate remaining space in the line
                    current_line_len = len(line.plain)
                    remaining_space = available_width - current_line_len

                    # Account for "■ " (2 chars) and remaining events
                    num_remaining_events = len(active_events) - event_index
                    # Each remaining event needs at least "■ " (2 chars) or "■" (1 char) + separator
                    min_space_for_remaining = (
                        num_remaining_events - 1
                    ) * 2  # "■ " for each future event

                    max_title_len = max(
                        0, remaining_space - 2 - min_space_for_remaining
                    )  # -2 for "■ "

                    if max_title_len > 3:
                        if len(title) > max_title_len:
                            title = title[: max_title_len - 3] + "..."
                        line.append("■ ", style=color)
                        line.append(title, style=color)
                    else:
                        # Not enough space for title, just show indicator
                        line.append("■", style=color)
                else:
                    # Just the square indicator without title
                    line.append("■", style=color)

        # Add tracker entries that fall in this time slot
        if entries is not None and len(entries) > 0:
            # Group entries by tracker_id that fall in this time slot
            # Entry timestamp is rounded down to the time slot
            slot_entries: dict[EntityId, list[Entry]] = {}
            for entry in entries:
                tracker_info = tracker_by_id.get(entry["tracker_id"])
                if tracker_info is None:
                    continue

                entry_time = entry["timestamp"].in_tz("local")
                # Round entry timestamp down to nearest granularity boundary
                entry_minutes = entry_time.hour * 60 + entry_time.minute
                entry_slot_minutes = (entry_minutes // granularity) * granularity
                entry_slot_hour = entry_slot_minutes // 60
                entry_slot_minute = entry_slot_minutes % 60

                # Check if this entry belongs to this time slot
                if (
                    entry_time.date() == slot_time.date()
                    and entry_slot_hour == slot_time.hour
                    and entry_slot_minute == slot_time.minute
                ):
                    tracker_id = entry["tracker_id"]
                    if tracker_id not in slot_entries:
                        slot_entries[tracker_id] = []
                    slot_entries[tracker_id].append(entry)

            if slot_entries:
                # Add spacing if there was previous content
                if active_audits or active_events:
                    line.append(" ")

                # Render each tracker's entries
                first_tracker = True
                for tracker_id, tracker_entries in slot_entries.items():
                    if not first_tracker:
                        line.append(" ")
                    first_tracker = False

                    # Get tracker info for color and name
                    tracker_info = tracker_by_id.get(tracker_id)
                    color = "white"
                    tracker_name = ""
                    value_type = "pips"
                    unit = ""
                    if tracker_info is not None:
                        color = tracker_info.get("color", "white") or "white"
                        tracker_name = tracker_info.get("name", "") or ""
                        value_type = tracker_info.get("value_type", "pips") or "pips"
                        unit = tracker_info.get("unit", "") or ""

                    # Show tracker name abbreviated (first 2 chars)
                    name_abbrev = tracker_name[:2] if tracker_name else ""
                    if name_abbrev:
                        line.append(f"{name_abbrev}:", style="dim")

                    # Render based on value_type
                    if value_type == "checkin":
                        # Show checkmark for each entry
                        check_count = len(tracker_entries)
                        if check_count == 1:
                            line.append("✓", style=color)
                        else:
                            line.append(f"✓×{check_count}", style=color)
                    elif value_type == "quantitative":
                        # Sum values and show total with unit
                        total = 0.0
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if isinstance(value, int | float):
                                total += value
                        # Format: show integer if whole number, else 1 decimal
                        if total == int(total):
                            display_val = str(int(total))
                        else:
                            display_val = f"{total:.1f}"
                        if unit:
                            line.append(f"{display_val}{unit}", style=color)
                        else:
                            line.append(display_val, style=color)
                    elif value_type == "multi_select":
                        # Show selected values
                        values = []
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if value is not None:
                                values.append(str(value))
                        if values:
                            line.append(",".join(values), style=color)
                        else:
                            line.append("·", style=color)
                    else:  # pips
                        # Generate pips based on entry values
                        pip_count = 0
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if isinstance(value, int):
                                pip_count += value
                            else:
                                pip_count += 1
                        pips = "●" * min(pip_count, 5)
                        if pip_count > 5:
                            pips += f"+{pip_count - 5}"
                        line.append(pips, style=color)

        content_lines.append(line)

    # Join all lines
    content = Text("\n").join(content_lines)

    # Create panel with date header and fixed width
    date_str = date.format("MM-DD ddd")

    # Determine border style and title based on whether it's today or a weekend
    today = pendulum.now("local").start_of("day")
    is_today = date == today
    is_weekend = date.day_of_week in [pendulum.SATURDAY, pendulum.SUNDAY]

    panel_title: RenderableType
    if is_today:
        border_style = "bold bright_cyan"
        panel_title = Text(date_str, style="bold black on bright_cyan")
    elif is_weekend:
        border_style = "bold orange4"
        panel_title = Text(date_str, style="bold white on orange4")
    else:
        border_style = "bright_black"
        panel_title = date_str

    return Panel(
        content,
        title=panel_title,
        title_align="left",
        border_style=border_style,
        padding=(0, 1),
        width=day_width,
    )


def _render_timeline(
    console: Console,
    time_audits: list[TimeAudit],
    events: list[Event],
    day_start: pendulum.DateTime,
    day_end: pendulum.DateTime,
    granularity: int = 60,
    start_hour: int = 0,
    start_minute: int = 0,
    end_hour: int = 23,
    end_minute: int = 59,
    trackers: Optional[list[Tracker]] = None,
    entries: Optional[list[Entry]] = None,
) -> None:
    """
    Render a vertical timeline with time audits and events.

    The timeline shows time intervals based on granularity from midnight to midnight
    with time audits plotted as blocks showing their duration and events as colored
    background squares that span their entire duration behind the audits.

    Args:
        console: Rich console for output
        time_audits: List of time audits to display
        events: List of events to display
        day_start: Start of the day
        day_end: End of the day
        granularity: Time interval in minutes (60, 30, or 15)
        start_hour: Starting hour for the timeline (default 0)
        start_minute: Starting minute for the timeline (default 0)
        end_hour: Ending hour for the timeline (default 23)
        end_minute: Ending minute for the timeline (default 59)
        trackers: List of trackers to display (defaults to None)
        entries: List of tracker entries to display (defaults to None)
    """
    # Build tracker lookup for getting tracker info from entry
    tracker_by_id: dict[EntityId, Tracker] = {}
    if trackers is not None:
        for tracker in trackers:
            if tracker["id"] is not None:
                tracker_by_id[tracker["id"]] = tracker
    # Calculate start and end minutes from midnight
    start_minutes_from_midnight = start_hour * 60 + start_minute
    end_minutes_from_midnight = end_hour * 60 + end_minute

    # Calculate number of time slots based on granularity and time range
    # Round start down to nearest granularity boundary
    start_slot_minutes = (start_minutes_from_midnight // granularity) * granularity
    # Round end up to nearest granularity boundary
    end_slot_minutes = (
        (end_minutes_from_midnight + granularity - 1) // granularity
    ) * granularity
    num_slots = (end_slot_minutes - start_slot_minutes) // granularity

    # Check if this is today and get current time slot
    today = pendulum.now("local").start_of("day")
    is_today = day_start == today
    current_time_slot = _get_current_time_slot(granularity) if is_today else None

    for slot_index in range(num_slots):
        slot_time = day_start.add(minutes=start_slot_minutes + slot_index * granularity)
        time_str = slot_time.format("HH:mm")
        slot_end = slot_time.add(minutes=granularity)

        active_audits = []
        for audit in time_audits:
            audit_start = audit["start"].in_tz("local") if audit["start"] else None
            audit_end: pendulum.DateTime = (
                audit["end"].in_tz("local") if audit["end"] else day_end
            )

            if audit_start is None:
                continue

            # Check if audit overlaps with this time slot
            if audit_start < slot_end and audit_end > slot_time:
                active_audits.append(audit)

        # Find active timed events for this time slot (all-day events are not included)
        active_events = []
        for event in events:
            if event["all_day"]:
                continue  # Skip all-day events, they're shown separately

            event_start = event["start"].in_tz("local")
            event_end = (
                event["end"].in_tz("local")
                if event["end"] is not None
                else event_start.add(hours=1)
            )

            # Check if event overlaps with this time slot
            if event_start < slot_end and event_end > slot_time:
                active_events.append(event)

        # Render the time slot line
        line = Text()
        # Highlight the time if it matches the current time slot
        if current_time_slot and time_str == current_time_slot:
            line.append(f"{time_str} ", style="bold black on bright_cyan")
        # Highlight lunch time (12:00-12:59, not including 13:00)
        elif slot_time.hour == 12:
            line.append(f"{time_str} ", style="bold black on yellow")
        else:
            line.append(f"{time_str} ", style="dim")
        line.append("│ ", style="bright_black")

        # Add audit information
        if active_audits:
            for i, audit in enumerate(active_audits):
                if i > 0:
                    line.append(" ")

                audit_start_optional = (
                    audit["start"].in_tz("local") if audit["start"] else None
                )
                audit_end_optional = (
                    audit["end"].in_tz("local") if audit["end"] else None
                )

                color = audit.get("color", "white")
                if color is None:
                    color = "white"

                # Check if this time slot contains the start or end of the audit
                show_desc = False
                if (
                    audit_start_optional
                    and audit_start_optional >= slot_time
                    and audit_start_optional < slot_end
                ):
                    show_desc = True
                elif (
                    audit_end_optional
                    and audit_end_optional >= slot_time
                    and audit_end_optional < slot_end
                ):
                    show_desc = True

                if show_desc:
                    desc = audit.get("description", "")
                    if desc is None:
                        desc = "[no description]"
                    line.append(f"█ {desc}", style=color)
                else:
                    line.append("█", style=color)

        # Add event indicators after audits
        if active_events:
            if active_audits:
                line.append("  ")  # Add spacing between audits and events

            for event_index, event in enumerate(active_events):
                if event_index > 0:
                    line.append(" ")

                event_start = event["start"].in_tz("local")
                event_end = (
                    event["end"].in_tz("local")
                    if event["end"] is not None
                    else event_start.add(hours=1)
                )

                color = event.get("color", "white")
                if color is None:
                    color = "white"

                # Check if this is the start of the event to show title
                show_title = event_start >= slot_time and event_start < slot_end

                if show_title:
                    title = event.get("title", "")
                    if title is None or title == "":
                        title = "[no title]"

                    # Truncate title to fit - leave room for other content
                    max_title_len = max(1, 40)
                    if len(title) > max_title_len:
                        title = title[: max_title_len - 3] + "..."

                    line.append("■ ", style=color)
                    line.append(title, style=color)
                else:
                    # Just the square indicator without title
                    line.append("■", style=color)

        # Add tracker entries that fall in this time slot
        if entries is not None and len(entries) > 0:
            # Group entries by tracker_id that fall in this time slot
            # Entry timestamp is rounded down to the time slot
            slot_entries: dict[EntityId, list[Entry]] = {}
            for entry in entries:
                tracker_info = tracker_by_id.get(entry["tracker_id"])
                if tracker_info is None:
                    continue

                entry_time = entry["timestamp"].in_tz("local")
                # Round entry timestamp down to nearest granularity boundary
                entry_minutes = entry_time.hour * 60 + entry_time.minute
                entry_slot_minutes = (entry_minutes // granularity) * granularity
                entry_slot_hour = entry_slot_minutes // 60
                entry_slot_minute = entry_slot_minutes % 60

                # Check if this entry belongs to this time slot
                if (
                    entry_time.date() == slot_time.date()
                    and entry_slot_hour == slot_time.hour
                    and entry_slot_minute == slot_time.minute
                ):
                    tracker_id = entry["tracker_id"]
                    if tracker_id not in slot_entries:
                        slot_entries[tracker_id] = []
                    slot_entries[tracker_id].append(entry)

            if slot_entries:
                # Add spacing if there was previous content
                if active_audits or active_events:
                    line.append("  ")

                # Render each tracker's entries
                first_tracker = True
                for tracker_id, tracker_entries in slot_entries.items():
                    if not first_tracker:
                        line.append(" ")
                    first_tracker = False

                    # Get tracker info for color and name
                    tracker_info = tracker_by_id.get(tracker_id)
                    color = "white"
                    tracker_name = ""
                    value_type = "pips"
                    unit = ""
                    if tracker_info is not None:
                        color = tracker_info.get("color", "white") or "white"
                        tracker_name = tracker_info.get("name", "") or ""
                        value_type = tracker_info.get("value_type", "pips") or "pips"
                        unit = tracker_info.get("unit", "") or ""

                    # Show tracker name abbreviated (first 3 chars)
                    name_abbrev = tracker_name[:3] if tracker_name else ""
                    if name_abbrev:
                        line.append(f"{name_abbrev}:", style="dim")

                    # Render based on value_type
                    if value_type == "checkin":
                        # Show checkmark for each entry
                        check_count = len(tracker_entries)
                        if check_count == 1:
                            line.append("✓", style=color)
                        else:
                            line.append(f"✓×{check_count}", style=color)
                    elif value_type == "quantitative":
                        # Sum values and show total with unit
                        total = 0.0
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if isinstance(value, int | float):
                                total += value
                        # Format: show integer if whole number, else 1 decimal
                        if total == int(total):
                            display_val = str(int(total))
                        else:
                            display_val = f"{total:.1f}"
                        if unit:
                            line.append(f"{display_val}{unit}", style=color)
                        else:
                            line.append(display_val, style=color)
                    elif value_type == "multi_select":
                        # Show selected values
                        values = []
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if value is not None:
                                values.append(str(value))
                        if values:
                            line.append(",".join(values), style=color)
                        else:
                            line.append("·", style=color)
                    else:  # pips
                        # Generate pips based on entry values
                        pip_count = 0
                        for entry in tracker_entries:
                            value = entry.get("value")
                            if isinstance(value, int):
                                pip_count += value
                            else:
                                pip_count += 1
                        pips = "●" * min(pip_count, 10)
                        if pip_count > 10:
                            pips += f"+{pip_count - 10}"
                        line.append(pips, style=color)

        # Print the line
        console.print(line)

    console.print()


def _filter_tasks_for_day(tasks: list[Task], date: pendulum.DateTime) -> list[Task]:
    """
    Filter tasks to only those that have a due date on the specified date.

    Args:
        tasks: List of all tasks
        date: The date to filter for (should be start of day in local timezone)

    Returns:
        List of tasks with due date on the specified day
    """
    day_start = date.start_of("day")
    day_end = date.end_of("day")

    filtered_tasks = []
    for task in tasks:
        if task["due"] is None or task["deleted"] is not None:
            continue

        # Convert due date to local timezone for comparison
        task_due_local = task["due"].in_tz("local").start_of("day")

        # Include task if due date matches the specified day
        if task_due_local >= day_start and task_due_local <= day_end:
            filtered_tasks.append(task)

    return filtered_tasks


def _filter_active_timespans_for_day(
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


def _filter_tasks_for_scheduled_or_due(
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


def _filter_logs_for_day(logs: list[Log], date: pendulum.DateTime) -> list[Log]:
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


def _filter_notes_for_day(notes: list[Note], date: pendulum.DateTime) -> list[Note]:
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


def _get_log_entity_name(
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


def _get_tasks_by_due_date(
    tasks: list[Task], month_start: pendulum.DateTime, month_end: pendulum.DateTime
) -> dict[str, list[Task]]:
    """
    Group tasks by their due date within the specified month range.

    Args:
        tasks: List of all tasks
        month_start: Start of the month range
        month_end: End of the month range

    Returns:
        Dictionary mapping date strings (YYYY-MM-DD) to lists of tasks
    """
    tasks_by_date: dict[str, list[Task]] = {}

    for task in tasks:
        if task["due"] is None or task["deleted"] is not None:
            continue

        # Convert due date to local timezone
        task_due_local = task["due"].in_tz("local").start_of("day")

        # Only include tasks within the month range
        if task_due_local >= month_start and task_due_local <= month_end:
            date_key = task_due_local.to_date_string()
            if date_key not in tasks_by_date:
                tasks_by_date[date_key] = []
            tasks_by_date[date_key].append(task)

    return tasks_by_date


def _get_tasks_by_scheduled_date(
    tasks: list[Task], month_start: pendulum.DateTime, month_end: pendulum.DateTime
) -> dict[str, list[Task]]:
    """
    Group tasks by their scheduled date within the specified month range.

    Args:
        tasks: List of all tasks
        month_start: Start of the month range
        month_end: End of the month range

    Returns:
        Dictionary mapping date strings (YYYY-MM-DD) to lists of tasks
    """
    tasks_by_date: dict[str, list[Task]] = {}

    for task in tasks:
        if task["scheduled"] is None or task["deleted"] is not None:
            continue

        # Convert scheduled date to local timezone
        task_scheduled_local = task["scheduled"].in_tz("local").start_of("day")

        # Only include tasks within the month range
        if task_scheduled_local >= month_start and task_scheduled_local <= month_end:
            date_key = task_scheduled_local.to_date_string()
            if date_key not in tasks_by_date:
                tasks_by_date[date_key] = []
            tasks_by_date[date_key].append(task)

    return tasks_by_date


def _get_all_day_events_by_date(
    events: list[Event], month_start: pendulum.DateTime, month_end: pendulum.DateTime
) -> dict[str, list[Event]]:
    """
    Group all-day events by their date within the specified month range.

    Args:
        events: List of all events
        month_start: Start of the month range
        month_end: End of the month range

    Returns:
        Dictionary mapping date strings (YYYY-MM-DD) to lists of all-day events
    """
    events_by_date: dict[str, list[Event]] = {}

    for event in events:
        if not event["all_day"] or event["deleted"] is not None:
            continue

        # All-day events are stored at midnight UTC for the intended date
        event_start_utc_day = event["start"].start_of("day")

        # Convert month range to UTC for comparison
        month_start_utc = month_start.in_tz("UTC").start_of("day")
        month_end_utc = month_end.in_tz("UTC").start_of("day")

        # Only include events within the month range
        if (
            event_start_utc_day >= month_start_utc
            and event_start_utc_day <= month_end_utc
        ):
            # Use the UTC date directly as the date key (since all-day events are stored at UTC midnight)
            date_key = event_start_utc_day.to_date_string()
            if date_key not in events_by_date:
                events_by_date[date_key] = []
            events_by_date[date_key].append(event)

    return events_by_date


def _get_non_all_day_events_by_date(
    events: list[Event], month_start: pendulum.DateTime, month_end: pendulum.DateTime
) -> dict[str, list[Event]]:
    """
    Group non-all-day (timed) events by their date within the specified month range.

    Args:
        events: List of all events
        month_start: Start of the month range
        month_end: End of the month range

    Returns:
        Dictionary mapping date strings (YYYY-MM-DD) to lists of non-all-day events
    """
    events_by_date: dict[str, list[Event]] = {}

    for event in events:
        if event["all_day"] or event["deleted"] is not None:
            continue

        # Timed events - convert to local for comparison
        event_start_local = event["start"].in_tz("local")
        event_end_local = (
            event["end"].in_tz("local")
            if event["end"] is not None
            else event_start_local.add(hours=1)
        )

        # Check if event overlaps with any day in the month range
        # We need to add events to all days they span
        current_day = event_start_local.start_of("day")
        last_day = event_end_local.start_of("day")

        # Iterate through each day the event spans
        while current_day <= last_day:
            # Only include if within month range
            if current_day >= month_start and current_day <= month_end:
                date_key = current_day.to_date_string()
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                # Avoid duplicates
                if event not in events_by_date[date_key]:
                    events_by_date[date_key].append(event)

            current_day = current_day.add(days=1)

    return events_by_date


def _get_current_time_slot(granularity: int) -> Optional[str]:
    """
    Get the current time rounded down to the nearest time slot based on granularity.

    Args:
        granularity: Time interval in minutes (60, 30, or 15)

    Returns:
        Time string in HH:mm format, or None if not today
    """
    now = pendulum.now("local")
    # Round down to the nearest time slot
    minutes_since_midnight = now.hour * 60 + now.minute
    slot_minutes = (minutes_since_midnight // granularity) * granularity
    hours = slot_minutes // 60
    minutes = slot_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _render_month_grid(
    month_start: pendulum.DateTime,
    scheduled_tasks_by_date: dict[str, list[Task]],
    due_tasks_by_date: dict[str, list[Task]],
    all_day_events_by_date: dict[str, list[Event]],
    non_all_day_events_by_date: dict[str, list[Event]],
    all_tasks: list[Task],
    cell_width: int = 20,
    show_scheduled_tasks: bool = True,
    show_due_tasks: bool = True,
    show_all_day_events: bool = True,
    show_non_all_day_events: bool = False,
) -> Table:
    """
    Render a single month as a calendar grid with tasks and events.

    Args:
        month_start: Start of the month to render
        scheduled_tasks_by_date: Dictionary mapping date strings to lists of scheduled tasks
        due_tasks_by_date: Dictionary mapping date strings to lists of due tasks
        all_day_events_by_date: Dictionary mapping date strings to lists of all-day events
        non_all_day_events_by_date: Dictionary mapping date strings to lists of non-all-day events
        all_tasks: All tasks (for checking clones)
        cell_width: Width of each day cell in characters
        show_scheduled_tasks: Whether to show scheduled tasks in the calendar
        show_due_tasks: Whether to show due tasks in the calendar
        show_all_day_events: Whether to show all-day events in the calendar
        show_non_all_day_events: Whether to show non-all-day events in the calendar

    Returns:
        A Table containing the month's calendar grid
    """
    # Create table with 7 columns for days of week
    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))

    # Add day-of-week headers
    for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        table.add_column(day_name, style="bold", width=cell_width)

    # Get the first day of the month and determine starting weekday
    month_start = month_start.start_of("month")
    month_end = month_start.end_of("month")

    # Pendulum's day_of_week: Monday = 0, Tuesday = 1, ..., Sunday = 6
    first_weekday = month_start.day_of_week

    # Get today's date for comparison
    today = pendulum.now("local").start_of("day")

    # Build calendar grid starting from the Monday of the week containing the first day
    # Since day_of_week is 0-indexed with Monday=0, we subtract day_of_week days
    current_date = month_start.subtract(days=first_weekday)
    week_cells: list[Text] = []

    for _ in range(42):  # 6 weeks max (6 * 7 = 42 days)
        cell_content = Text()

        # Check if this date is in the current month
        if current_date.month == month_start.month:
            date_str = current_date.to_date_string()
            day_num = current_date.day

            # Check if this is today
            is_today = current_date == today

            # Check if this is a weekend (use Pendulum's constants)
            is_weekend = current_date.day_of_week in [
                pendulum.SATURDAY,
                pendulum.SUNDAY,
            ]

            # Add day number with background color if today or weekend
            if is_today:
                cell_content.append(f"{day_num:2d}", style="bold black on bright_cyan")
                cell_content.append("   \n", style="bold black on bright_cyan")
            elif is_weekend:
                cell_content.append(f"{day_num:2d}", style="bold white on orange4")
                cell_content.append("   \n", style="bold white on orange4")
            else:
                cell_content.append(f"{day_num:2d}\n", style="bold")

            # Collect all tasks for this day
            day_tasks: list[tuple[Task, str]] = []  # (task, label) tuples

            if show_scheduled_tasks and date_str in scheduled_tasks_by_date:
                for task in scheduled_tasks_by_date[date_str]:
                    day_tasks.append((task, "S"))

            if show_due_tasks and date_str in due_tasks_by_date:
                for task in due_tasks_by_date[date_str]:
                    day_tasks.append((task, "D"))

            # Collect all-day events for this day
            day_all_day_events: list[Event] = []
            if show_all_day_events and date_str in all_day_events_by_date:
                day_all_day_events = all_day_events_by_date[date_str]

            # Collect non-all-day events for this day
            day_non_all_day_events: list[Event] = []
            if show_non_all_day_events and date_str in non_all_day_events_by_date:
                day_non_all_day_events = non_all_day_events_by_date[date_str]

            # Render tasks (max 3)
            for i, (task, label) in enumerate(day_tasks[:3]):
                state = task_state(task, all_tasks)
                desc = task.get("description", "")
                if desc is None:
                    desc = "[no desc]"

                color = task.get("color", "white")
                if color is None:
                    color = "white"

                # Truncate description to fit in cell
                # Account for state emoji, space, label, space
                max_desc_len = cell_width - 5
                if len(desc) > max_desc_len:
                    desc = desc[: max_desc_len - 3] + "..."

                cell_content.append(f"{state} ", style=color)
                cell_content.append(f"{label} ", style="dim")
                cell_content.append(f"{desc}\n", style=color)

            # Show count if more tasks exist
            if len(day_tasks) > 3:
                remaining = len(day_tasks) - 3
                cell_content.append(f"  +{remaining} more\n", style="dim")

            # Render all-day events (underneath tasks)
            for i, event in enumerate(day_all_day_events[:3]):
                title = event.get("title", "")
                if title is None or title == "":
                    title = "[no title]"

                color = event.get("color", "white")
                if color is None:
                    color = "white"

                # Truncate title to fit in cell
                # Account for square and space
                max_title_len = cell_width - 3
                if len(title) > max_title_len:
                    title = title[: max_title_len - 3] + "..."

                cell_content.append("■ ", style=color)
                cell_content.append(f"{title}\n", style=color)

            # Show count if more all-day events exist
            if len(day_all_day_events) > 3:
                remaining = len(day_all_day_events) - 3
                cell_content.append(f"  +{remaining} more\n", style="dim")

            # Render non-all-day events (underneath all-day events)
            for i, event in enumerate(day_non_all_day_events[:3]):
                title = event.get("title", "")
                if title is None or title == "":
                    title = "[no title]"

                color = event.get("color", "white")
                if color is None:
                    color = "white"

                # Get event time for display
                event_start = event["start"].in_tz("local")
                time_str = event_start.format("HH:mm")

                # Truncate title to fit in cell
                # Account for circle, space, time (5 chars), space (1), and space for truncation
                max_title_len = cell_width - 9
                if len(title) > max_title_len:
                    title = title[: max_title_len - 3] + "..."

                cell_content.append("● ", style=color)
                cell_content.append(f"{time_str} ", style="dim")
                cell_content.append(f"{title}\n", style=color)

            # Show count if more non-all-day events exist
            if len(day_non_all_day_events) > 3:
                remaining = len(day_non_all_day_events) - 3
                cell_content.append(f"  +{remaining} more\n", style="dim")
        else:
            # Empty cell for days outside the current month
            cell_content.append(" ", style="dim")

        week_cells.append(cell_content)

        # Add row when we have a complete week
        if len(week_cells) == 7:
            table.add_row(*week_cells)
            week_cells = []

        current_date = current_date.add(days=1)

        # Stop after we've passed the end of the month and filled the last week
        if current_date > month_end and len(week_cells) == 0:
            break

    return table
