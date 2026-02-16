# SPDX-License-Identifier: MIT

from typing import Annotated, Any, Optional, cast

import pendulum
import typer

from granular.color import (
    LOG_META_COLOR,
    NOTE_META_COLOR,
    TIME_AUDIT_META_COLOR,
)
from granular.id_map import clear_id_map_if_required
from granular.model.entry import Entry
from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.terminal_dispatch import (
    AgendaParams,
    CalDayParams,
    CalDaysParams,
    CalMonthParams,
    CalQuarterParams,
    CalWeekParams,
    ContextsParams,
    EntriesParams,
    EventsParams,
    GanttParams,
    LogsParams,
    NotesParams,
    ProjectsParams,
    StoryParams,
    TagsParams,
    TasksHeatmapParams,
    TasksParams,
    TerminalView,
    TimeAuditActiveParams,
    TimeAuditsParams,
    TimespansParams,
    TrackerHeatmapParams,
    TrackersParams,
    TrackerSummaryParams,
    TrackerTodayParams,
)
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.model.tracker import Tracker
from granular.query.filter import generate_filter, tag_matches_regex
from granular.repository.context import CONTEXT_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import AlphabeticalContextAwareGroup
from granular.terminal.parse import parse_datetime, parse_time
from granular.time import datetime_to_local_date_str_optional
from granular.view.terminal_dispatch import update_cached_dispatch
from granular.view.view.views.calendar import (
    calendar_agenda_days_view,
    calendar_day_view,
    calendar_days_view,
    calendar_month_view,
    calendar_quarter_view,
    calendar_week_view,
)
from granular.view.view.views.gantt import gantt_view
from granular.view.view.views.story import story_view

app = typer.Typer(cls=AlphabeticalContextAwareGroup, no_args_is_help=True)


@app.command("tasks, ts")
def tasks(
    scheduled: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--scheduled",
            "-s",
            parser=parse_datetime,
            help="Filter tasks scheduled on this date (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    due: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--due",
            "-d",
            parser=parse_datetime,
            help="Filter tasks due on this date (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", "-t", help="Filter tasks that have all of these tags"),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter tasks that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag", "-nt", help="Filter tasks that do not have any of these tags"
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter tasks that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter tasks by project"),
    ] = None,
    include_deleted: Annotated[
        bool, typer.Option("--include-deleted", "-i", help="Include deleted tasks")
    ] = False,
    columns: Annotated[
        Optional[list[str]],
        typer.Option(
            "--column", "-c", help="Show these columns. Accepts multiple inputs"
        ),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted tasks by default
    if not include_deleted:
        tasks = [task for task in tasks if task["deleted"] is None]

    # Filter by scheduled date if provided
    if scheduled is not None:
        end_scheduled = scheduled.add(hours=23, minutes=59, seconds=59)
        tasks = [
            task
            for task in tasks
            if task["scheduled"] is not None
            and scheduled <= task["scheduled"] < end_scheduled
        ]

    # Filter by due date if provided
    if due is not None:
        end_due = due.add(hours=23, minutes=59, seconds=59)
        tasks = [
            task
            for task in tasks
            if task["due"] is not None and due <= task["due"] < end_due
        ]

    # Filter by tags if provided (exact match)
    if tag is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is not None and all(t in task["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is not None
            and all(tag_matches_regex(pattern, task["tags"]) for pattern in tag_regex)
        ]

    # Filter out tasks with any of the no_tag tags (exact match)
    if no_tag is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is None or not any(t in task["tags"] for t in no_tag)
        ]

    # Filter out tasks with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is None
            or not any(
                tag_matches_regex(pattern, task["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        tasks = [task for task in tasks if task["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task], context_filter.filter(cast(list[dict[str, Any]], tasks))
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TasksParams = {
        "include_deleted": include_deleted,
        "scheduled": datetime_to_local_date_str_optional(scheduled),
        "due": datetime_to_local_date_str_optional(due),
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "columns": columns,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }

    update_cached_dispatch(TerminalView.TASKS, terminal_params)

    # Import view function here to avoid circular imports
    from granular.view.view.views.task import tasks_view

    tasks_view(
        active_context=active_context_name,
        report_name="tasks",
        tasks=tasks,
        time_audits=time_audits,
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap,
        **({"columns": columns} if columns is not None else {}),
    )


@app.command("task, t")
def task(
    task_id: Annotated[int, typer.Argument(help="Task ID to view")],
) -> None:
    """Display full details for a single task."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.task import single_task_view

    real_task_id: int = ID_MAP_REPO.get_real_id("tasks", task_id)

    task_obj = TASK_REPO.get_task(real_task_id)
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_task_view(
        active_context=active_context_name,
        task=task_obj,
        time_audits=time_audits,
    )


@app.command("time-audits, tas")
def time_audits(
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted time audits"),
    ] = False,
    task_id: Annotated[
        Optional[int],
        typer.Option("--task-id", "-tid", help="Filter by task ID"),
    ] = None,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag", "-t", help="Filter time audits that have all of these tags"
        ),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter time audits that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag",
            "-nt",
            help="Filter time audits that do not have any of these tags",
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter time audits that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter time audits by project"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    from granular.repository.id_map import ID_MAP_REPO

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted time audits by default
    if not include_deleted:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["deleted"] is None
        ]

    # Filter by task_id if provided
    if task_id is not None:
        real_task_id: int = ID_MAP_REPO.get_real_id("tasks", task_id)
        time_audits = [
            time_audit
            for time_audit in time_audits
            if time_audit["task_id"] == real_task_id
        ]

    # Filter by tags if provided (exact match)
    if tag is not None:
        time_audits = [
            time_audit
            for time_audit in time_audits
            if time_audit["tags"] is not None
            and all(t in time_audit["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        time_audits = [
            time_audit
            for time_audit in time_audits
            if time_audit["tags"] is not None
            and all(
                tag_matches_regex(pattern, time_audit["tags"]) for pattern in tag_regex
            )
        ]

    # Filter out time audits with any of the no_tag tags (exact match)
    if no_tag is not None:
        time_audits = [
            time_audit
            for time_audit in time_audits
            if time_audit["tags"] is None
            or not any(t in time_audit["tags"] for t in no_tag)
        ]

    # Filter out time audits with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        time_audits = [
            time_audit
            for time_audit in time_audits
            if time_audit["tags"] is None
            or not any(
                tag_matches_regex(pattern, time_audit["tags"])
                for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["project"] == project
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TimeAuditsParams = {
        "include_deleted": include_deleted,
        "task_id": task_id,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }
    update_cached_dispatch(TerminalView.TIME_AUDITS, terminal_params)

    from granular.view.view.views.time_audit import time_audits_report

    time_audits_report(
        active_context=active_context_name,
        report_name="time_audits",
        time_audits=time_audits,
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap,
    )


@app.command("time-audit, ta")
def time_audit(
    time_audit_id: Annotated[int, typer.Argument(help="Time audit ID to view")],
) -> None:
    """Display full details for a single time audit."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.time_audit import single_time_audit_report

    real_time_audit_id: int = ID_MAP_REPO.get_real_id("time_audits", time_audit_id)

    time_audit_obj = TIME_AUDIT_REPO.get_time_audit(real_time_audit_id)
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_time_audit_report(
        active_context=active_context_name,
        time_audit=time_audit_obj,
    )


@app.command("time-audit-active, taa")
def time_audit_active() -> None:
    from granular.view.view.views.time_audit import active_time_audit_report

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    time_audits = [
        time_audit for time_audit in time_audits if time_audit["deleted"] is None
    ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )

    active_time_audits = [
        time_audit
        for time_audit in time_audits
        if time_audit["start"] is not None and time_audit["end"] is None
    ]

    if len(active_time_audits) > 1:
        raise ValueError("Should not have more than one active time audit")

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TimeAuditActiveParams = {}
    update_cached_dispatch(TerminalView.TIME_AUDIT_ACTIVE, terminal_params)

    time_audit_obj = active_time_audits[0] if len(active_time_audits) == 1 else None
    active_time_audit_report(
        active_context=active_context_name,
        time_audit=time_audit_obj,
    )


@app.command("events, es")
def events(
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted events"),
    ] = False,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", "-t", help="Filter events that have all of these tags"),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter events that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag", "-nt", help="Filter events that do not have any of these tags"
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter events that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter events by project"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    events = EVENT_REPO.get_all_events()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted events by default
    if not include_deleted:
        events = [event for event in events if event["deleted"] is None]

    # Filter by tags if provided (exact match)
    if tag is not None:
        events = [
            event
            for event in events
            if event["tags"] is not None and all(t in event["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        events = [
            event
            for event in events
            if event["tags"] is not None
            and all(tag_matches_regex(pattern, event["tags"]) for pattern in tag_regex)
        ]

    # Filter out events with any of the no_tag tags (exact match)
    if no_tag is not None:
        events = [
            event
            for event in events
            if event["tags"] is None or not any(t in event["tags"] for t in no_tag)
        ]

    # Filter out events with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        events = [
            event
            for event in events
            if event["tags"] is None
            or not any(
                tag_matches_regex(pattern, event["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        events = [event for event in events if event["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: EventsParams = {
        "include_deleted": include_deleted,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }
    update_cached_dispatch(TerminalView.EVENTS, terminal_params)

    from granular.view.view.views.event import events_view

    events_view(
        active_context=active_context_name,
        report_name="events",
        events=events,
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap,
    )


@app.command("event, e")
def event(
    event_id: Annotated[int, typer.Argument(help="Event ID to view")],
) -> None:
    """Display full details for a single event."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.event import single_event_view

    real_event_id: int = ID_MAP_REPO.get_real_id("events", event_id)

    event_obj = EVENT_REPO.get_event(real_event_id)
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_event_view(
        active_context=active_context_name,
        event=event_obj,
    )


@app.command("timespans, ts")
def timespans(
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted timespans"),
    ] = False,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag", "-t", help="Filter timespans that have all of these tags"
        ),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter timespans that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag",
            "-nt",
            help="Filter timespans that do not have any of these tags",
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter timespans that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter timespans by project"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    timespans = TIMESPAN_REPO.get_all_timespans()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted timespans by default
    if not include_deleted:
        timespans = [timespan for timespan in timespans if timespan["deleted"] is None]

    # Filter by tags if provided (exact match)
    if tag is not None:
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is not None and all(t in timespan["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is not None
            and all(
                tag_matches_regex(pattern, timespan["tags"]) for pattern in tag_regex
            )
        ]

    # Filter out timespans with any of the no_tag tags (exact match)
    if no_tag is not None:
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is None
            or not any(t in timespan["tags"] for t in no_tag)
        ]

    # Filter out timespans with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is None
            or not any(
                tag_matches_regex(pattern, timespan["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        timespans = [
            timespan for timespan in timespans if timespan["project"] == project
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        timespans = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TimespansParams = {
        "include_deleted": include_deleted,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }
    update_cached_dispatch(TerminalView.TIMESPANS, terminal_params)

    from granular.view.view.views.timespan import timespans_view

    timespans_view(
        active_context=active_context_name,
        report_name="timespans",
        timespans=timespans,
        use_color=not no_color,
        no_wrap=no_wrap,
    )


@app.command("timespan, tsp")
def timespan(
    timespan_id: Annotated[int, typer.Argument(help="Timespan ID to view")],
) -> None:
    """Display full details for a single timespan."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.timespan import single_timespan_view

    real_timespan_id: int = ID_MAP_REPO.get_real_id("timespans", timespan_id)

    timespan_obj = TIMESPAN_REPO.get_timespan(real_timespan_id)
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_timespan_view(
        active_context=active_context_name,
        timespan=timespan_obj,
    )


@app.command("log, l")
def log(
    log_id: Annotated[int, typer.Argument(help="Log ID to view")],
) -> None:
    """Display full details for a single log."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.log import single_log_report

    real_log_id: int = ID_MAP_REPO.get_real_id("logs", log_id)

    log_obj = LOG_REPO.get_log(real_log_id)
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_log_report(
        active_context=active_context_name,
        log=log_obj,
    )


@app.command("logs, ls")
def logs(
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted logs"),
    ] = False,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", "-t", help="Filter logs that have all of these tags"),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter logs that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag", "-nt", help="Filter logs that do not have any of these tags"
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter logs that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter logs by project"),
    ] = None,
    reference_type: Annotated[
        Optional[str],
        typer.Option("--reference-type", "-rt", help="Filter logs by reference type"),
    ] = None,
    reference_id: Annotated[
        Optional[int],
        typer.Option("--reference-id", "-rid", help="Filter logs by reference ID"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    """Display all logs in the system."""
    logs_list = LOG_REPO.get_all_logs()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted logs by default
    if not include_deleted:
        logs_list = [log for log in logs_list if log["deleted"] is None]

    # Filter by tags if provided (exact match)
    if tag is not None:
        logs_list = [
            log
            for log in logs_list
            if log["tags"] is not None and all(t in log["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        logs_list = [
            log
            for log in logs_list
            if log["tags"] is not None
            and all(tag_matches_regex(pattern, log["tags"]) for pattern in tag_regex)
        ]

    # Filter out logs with any of the no_tag tags (exact match)
    if no_tag is not None:
        logs_list = [
            log
            for log in logs_list
            if log["tags"] is None or not any(t in log["tags"] for t in no_tag)
        ]

    # Filter out logs with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        logs_list = [
            log
            for log in logs_list
            if log["tags"] is None
            or not any(
                tag_matches_regex(pattern, log["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        logs_list = [log for log in logs_list if log["project"] == project]

    # Filter by reference_type if provided
    if reference_type is not None:
        logs_list = [
            log for log in logs_list if log["reference_type"] == reference_type
        ]

    # Filter by reference_id if provided
    if reference_id is not None:
        logs_list = [log for log in logs_list if log["reference_id"] == reference_id]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        logs_list = cast(
            list[Log],
            context_filter.filter(cast(list[dict[str, Any]], logs_list)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: LogsParams = {
        "include_deleted": include_deleted,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }
    update_cached_dispatch(TerminalView.LOGS, terminal_params)

    from granular.view.view.views.log import logs_view

    logs_view(
        active_context=active_context_name,
        report_name="logs",
        logs=logs_list,
        use_color=not no_color,
        no_wrap=no_wrap,
    )


@app.command("notes, ns")
def notes(
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted notes"),
    ] = False,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", "-t", help="Filter notes that have all of these tags"),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter notes that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag", "-nt", help="Filter notes that do not have any of these tags"
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter notes that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter notes by project"),
    ] = None,
    reference_type: Annotated[
        Optional[str],
        typer.Option("--reference-type", "-rt", help="Filter notes by reference type"),
    ] = None,
    reference_id: Annotated[
        Optional[int],
        typer.Option("--reference-id", "-rid", help="Filter notes by reference ID"),
    ] = None,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    """Display all notes in the system."""
    notes_list = NOTE_REPO.get_all_notes()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted notes by default
    if not include_deleted:
        notes_list = [note for note in notes_list if note["deleted"] is None]

    # Filter by tags if provided (exact match)
    if tag is not None:
        notes_list = [
            note
            for note in notes_list
            if note["tags"] is not None and all(t in note["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        notes_list = [
            note
            for note in notes_list
            if note["tags"] is not None
            and all(tag_matches_regex(pattern, note["tags"]) for pattern in tag_regex)
        ]

    # Filter out notes with any of the no_tag tags (exact match)
    if no_tag is not None:
        notes_list = [
            note
            for note in notes_list
            if note["tags"] is None or not any(t in note["tags"] for t in no_tag)
        ]

    # Filter out notes with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        notes_list = [
            note
            for note in notes_list
            if note["tags"] is None
            or not any(
                tag_matches_regex(pattern, note["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        notes_list = [note for note in notes_list if note["project"] == project]

    # Filter by reference_type if provided
    if reference_type is not None:
        notes_list = [
            note for note in notes_list if note["reference_type"] == reference_type
        ]

    # Filter by reference_id if provided
    if reference_id is not None:
        notes_list = [
            note for note in notes_list if note["reference_id"] == reference_id
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        notes_list = cast(
            list[Note],
            context_filter.filter(cast(list[dict[str, Any]], notes_list)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: NotesParams = {
        "include_deleted": include_deleted,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "no_color": no_color,
        "no_wrap": no_wrap,
    }
    update_cached_dispatch(TerminalView.NOTES, terminal_params)

    from granular.view.view.views.note import notes_report

    notes_report(
        active_context=active_context_name,
        report_name="notes",
        notes=notes_list,
        use_color=not no_color,
        no_wrap=no_wrap,
    )


@app.command("note, n")
def note(
    note_id: Annotated[int, typer.Argument(help="Note ID to view")],
) -> None:
    """Display full details for a single note."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.view.view.views.note import single_note_report

    real_note_id: int = ID_MAP_REPO.get_real_id("notes", note_id)

    note_obj = NOTE_REPO.get_note(real_note_id)
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    clear_id_map_if_required()

    # Single entity views are not cached
    single_note_report(
        active_context=active_context_name,
        note=note_obj,
    )


@app.command("gantt, g")
def gantt(
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="Start date for timeline (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="End date for timeline (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    granularity: Annotated[
        str,
        typer.Option(
            "--granularity",
            "-g",
            help="Time granularity: day, week, or month",
        ),
    ] = "day",
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted items"),
    ] = False,
    tag: Annotated[
        Optional[list[str]],
        typer.Option("--tag", "-t", help="Filter entities that have all of these tags"),
    ] = None,
    tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag-regex",
            "-tr",
            help="Filter entities that have tags matching all of these regex patterns",
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag", "-nt", help="Filter entities that do not have any of these tags"
        ),
    ] = None,
    no_tag_regex: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag-regex",
            "-ntr",
            help="Filter entities that do not have tags matching any of these regex patterns",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
    show_tasks: Annotated[
        bool,
        typer.Option("--show-tasks/--no-show-tasks", help="Show tasks under timespans"),
    ] = False,
    show_timespans: Annotated[
        bool,
        typer.Option("--show-timespans/--no-show-timespans", help="Show timespans"),
    ] = True,
    show_events: Annotated[
        bool,
        typer.Option("--show-events/--no-show-events", help="Show events"),
    ] = True,
    show_trackers: Annotated[
        bool,
        typer.Option("--show-trackers/--no-show-trackers", help="Show trackers"),
    ] = False,
    left_width: Annotated[
        int,
        typer.Option("--left-width", "-lw", help="Width of left column for item names"),
    ] = 40,
) -> None:
    """Display timespans, events, and trackers on a gantt chart timeline."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.tracker import TRACKER_REPO

    timespans = TIMESPAN_REPO.get_all_timespans()
    events = EVENT_REPO.get_all_events()
    tasks = TASK_REPO.get_all_tasks()
    active_context = CONTEXT_REPO.get_active_context()

    # Fetch trackers and entries if show_trackers is enabled
    trackers: list[Tracker] = []
    entries: list[Entry] = []
    if show_trackers:
        trackers = TRACKER_REPO.get_all_trackers()
        entries = ENTRY_REPO.get_all_entries()

        # Filter out deleted/archived trackers and deleted entries
        trackers = [
            t for t in trackers if t["deleted"] is None and t["archived"] is None
        ]
        entries = [e for e in entries if e["deleted"] is None]

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted timespans and events by default
    if not include_deleted:
        timespans = [timespan for timespan in timespans if timespan["deleted"] is None]
        events = [event for event in events if event["deleted"] is None]

    # Filter by tags if provided (exact match)
    if tag is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is not None and all(t in task["tags"] for t in tag)
        ]
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is not None and all(t in timespan["tags"] for t in tag)
        ]
        events = [
            event
            for event in events
            if event["tags"] is not None and all(t in event["tags"] for t in tag)
        ]

    # Filter by tag regex patterns if provided
    if tag_regex is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is not None
            and all(tag_matches_regex(pattern, task["tags"]) for pattern in tag_regex)
        ]
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is not None
            and all(
                tag_matches_regex(pattern, timespan["tags"]) for pattern in tag_regex
            )
        ]
        events = [
            event
            for event in events
            if event["tags"] is not None
            and all(tag_matches_regex(pattern, event["tags"]) for pattern in tag_regex)
        ]

    # Filter out entities with any of the no_tag tags (exact match)
    if no_tag is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is None or not any(t in task["tags"] for t in no_tag)
        ]
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is None
            or not any(t in timespan["tags"] for t in no_tag)
        ]
        events = [
            event
            for event in events
            if event["tags"] is None or not any(t in event["tags"] for t in no_tag)
        ]

    # Filter out entities with tags matching any of the no_tag_regex patterns
    if no_tag_regex is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is None
            or not any(
                tag_matches_regex(pattern, task["tags"]) for pattern in no_tag_regex
            )
        ]
        timespans = [
            timespan
            for timespan in timespans
            if timespan["tags"] is None
            or not any(
                tag_matches_regex(pattern, timespan["tags"]) for pattern in no_tag_regex
            )
        ]
        events = [
            event
            for event in events
            if event["tags"] is None
            or not any(
                tag_matches_regex(pattern, event["tags"]) for pattern in no_tag_regex
            )
        ]

    # Filter by project if provided
    if project is not None:
        tasks = [task for task in tasks if task["project"] == project]
        timespans = [
            timespan for timespan in timespans if timespan["project"] == project
        ]
        events = [event for event in events if event["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        timespans = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        if show_trackers:
            trackers = cast(
                list[Tracker],
                context_filter.filter(cast(list[dict[str, Any]], trackers)),
            )
            entries = cast(
                list[Entry],
                context_filter.filter(cast(list[dict[str, Any]], entries)),
            )

    # Validate granularity
    if granularity not in ["day", "week", "month"]:
        raise typer.BadParameter(
            f"Granularity must be 'day', 'week', or 'month', got '{granularity}'"
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: GanttParams = {
        "start": datetime_to_local_date_str_optional(start),
        "end": datetime_to_local_date_str_optional(end),
        "granularity": granularity,
        "include_deleted": include_deleted,
        "tag": tag,
        "tag_regex": tag_regex,
        "no_tag": no_tag,
        "no_tag_regex": no_tag_regex,
        "project": project,
        "show_tasks": show_tasks,
        "show_timespans": show_timespans,
        "show_events": show_events,
        "show_trackers": show_trackers,
        "left_width": left_width,
    }
    update_cached_dispatch(TerminalView.GANTT, terminal_params)

    gantt_view(
        active_context_name,
        "gantt",
        timespans,
        events=events,
        tasks=tasks,
        trackers=trackers,
        entries=entries,
        start=start,
        end=end,
        granularity=granularity,  # type: ignore[arg-type]
        show_tasks=show_tasks,
        show_timespans=show_timespans,
        show_events=show_events,
        show_trackers=show_trackers,
        left_column_width=left_width,
    )


@app.command("contexts, cx")
def contexts() -> None:
    from granular.view.view.views.context import contexts_view

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    all_contexts = sorted(
        CONTEXT_REPO.get_all_contexts(), key=lambda x: cast(str, x["name"])
    )

    # Cache terminal-level parameters for replay
    terminal_params: ContextsParams = {}
    update_cached_dispatch(TerminalView.CONTEXTS, terminal_params)

    contexts_view(
        active_context=active_context_name,
        contexts=all_contexts,
    )


@app.command("context-current-name, ccn")
def context_current_name() -> None:
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    typer.echo(active_context_name)


@app.command("projects, p")
def projects() -> None:
    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items
    tasks = [task for task in tasks if task["deleted"] is None]
    time_audits = [
        time_audit for time_audit in time_audits if time_audit["deleted"] is None
    ]
    events = [event for event in events if event["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task], context_filter.filter(cast(list[dict[str, Any]], tasks))
        )
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )

    # Collect all unique projects from filtered entities
    all_projects: set[str] = set()
    for task in tasks:
        if task["project"] is not None:
            all_projects.add(task["project"])
    for time_audit in time_audits:
        if time_audit["project"] is not None:
            all_projects.add(time_audit["project"])
    for event in events:
        if event["project"] is not None:
            all_projects.add(event["project"])

    # Sort alphabetically
    sorted_projects = sorted(list(all_projects))

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: ProjectsParams = {}
    update_cached_dispatch(TerminalView.PROJECTS, terminal_params)

    from granular.view.view.views.project import projects_view

    projects_view(
        active_context=active_context_name,
        projects=sorted_projects,
    )


@app.command("tags, tg")
def tags() -> None:
    from granular.view.view.views.tag import tags_report

    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items
    tasks = [task for task in tasks if task["deleted"] is None]
    time_audits = [
        time_audit for time_audit in time_audits if time_audit["deleted"] is None
    ]
    events = [event for event in events if event["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task], context_filter.filter(cast(list[dict[str, Any]], tasks))
        )
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )

    # Collect all unique tags from filtered entities
    all_tags: set[str] = set()
    for task in tasks:
        if task["tags"] is not None:
            all_tags.update(task["tags"])
    for time_audit in time_audits:
        if time_audit["tags"] is not None:
            all_tags.update(time_audit["tags"])
    for event in events:
        if event["tags"] is not None:
            all_tags.update(event["tags"])

    # Sort alphabetically
    sorted_tags = sorted(list(all_tags))

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TagsParams = {}
    update_cached_dispatch(TerminalView.TAGS, terminal_params)

    tags_report(
        active_context=active_context_name,
        tags=sorted_tags,
    )


@app.command("cal-day, cd")
def cal_day(
    date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--date",
            "-d",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    granularity: Annotated[
        int,
        typer.Option(
            "--granularity",
            "-g",
            help="Time interval in minutes (15, 30, or 60)",
        ),
    ] = 60,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted time audits and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in calendar",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in calendar"
        ),
    ] = True,
    show_time_audits: Annotated[
        bool,
        typer.Option(
            "--show-time-audits/--no-show-time-audits",
            help="Show time audits in calendar",
        ),
    ] = True,
    show_trackers: Annotated[
        bool,
        typer.Option(
            "--show-trackers/--no-show-trackers",
            help="Show tracker entries as pips in calendar",
        ),
    ] = False,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start",
            "-s",
            help="Start time for calendar display (HH:mm format, e.g., 8:00)",
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option(
            "--end",
            "-e",
            help="End time for calendar display (HH:mm format, e.g., 17:00)",
        ),
    ] = None,
) -> None:
    """Display a calendar view showing time audits and events for the current day."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.tracker import TRACKER_REPO

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    tasks = TASK_REPO.get_all_tasks()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Fetch trackers and entries if show_trackers is enabled
    trackers: list[Tracker] = []
    entries: list[Entry] = []
    if show_trackers:
        trackers = TRACKER_REPO.get_all_trackers()
        entries = ENTRY_REPO.get_all_entries()

        # Filter out deleted/archived trackers and deleted entries
        trackers = [
            t for t in trackers if t["deleted"] is None and t["archived"] is None
        ]
        entries = [e for e in entries if e["deleted"] is None]

    # Filter out deleted items by default
    if not include_deleted:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["deleted"] is None
        ]
        events = [event for event in events if event["deleted"] is None]
        tasks = [task for task in tasks if task["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["project"] == project
        ]
        events = [event for event in events if event["project"] == project]
        tasks = [task for task in tasks if task["project"] == project]
        if show_trackers:
            trackers = [t for t in trackers if t["project"] == project]
            entries = [e for e in entries if e["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        if show_trackers:
            trackers = cast(
                list[Tracker],
                context_filter.filter(cast(list[dict[str, Any]], trackers)),
            )
            entries = cast(
                list[Entry],
                context_filter.filter(cast(list[dict[str, Any]], entries)),
            )

    # Parse time boundaries
    start_time = parse_time(start) if start else None
    end_time = parse_time(end) if end else None

    start_hour = start_time[0] if start_time else 0
    start_minute = start_time[1] if start_time else 0
    end_hour = end_time[0] if end_time else 23
    end_minute = end_time[1] if end_time else 59

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: CalDayParams = {
        "date": datetime_to_local_date_str_optional(date),
        "granularity": granularity,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "show_time_audits": show_time_audits,
        "show_trackers": show_trackers,
        "project": project,
        "start": start,
        "end": end,
    }
    update_cached_dispatch(TerminalView.CAL_DAY, terminal_params)

    calendar_day_view(
        active_context_name,
        "calendar",
        time_audits,
        events,
        tasks,
        date,
        granularity,
        show_scheduled_tasks,
        show_due_tasks,
        show_time_audits,
        start_hour,
        start_minute,
        end_hour,
        end_minute,
        trackers=trackers,
        entries=entries,
        show_trackers=show_trackers,
    )


@app.command("cal-week, cw")
def cal_week(
    start_date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start-date",
            "-sd",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    num_days: Annotated[
        int,
        typer.Option(
            "--num-days",
            "-n",
            help="Number of days to display",
        ),
    ] = 7,
    day_width: Annotated[
        int,
        typer.Option(
            "--day-width",
            "-w",
            help="Width of each day column in characters",
        ),
    ] = 30,
    granularity: Annotated[
        int,
        typer.Option(
            "--granularity",
            "-g",
            help="Time interval in minutes (15, 30, or 60)",
        ),
    ] = 60,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted time audits and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in calendar",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in calendar"
        ),
    ] = True,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start",
            "-s",
            help="Start time for calendar display (HH:mm format, e.g., 8:00)",
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option(
            "--end",
            "-e",
            help="End time for calendar display (HH:mm format, e.g., 17:00)",
        ),
    ] = None,
) -> None:
    """Display a multi-day calendar showing time audits and events horizontally across days."""
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    tasks = TASK_REPO.get_all_tasks()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items by default
    if not include_deleted:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["deleted"] is None
        ]
        events = [event for event in events if event["deleted"] is None]
        tasks = [task for task in tasks if task["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["project"] == project
        ]
        events = [event for event in events if event["project"] == project]
        tasks = [task for task in tasks if task["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )

    # Parse time boundaries
    start_time = parse_time(start) if start else None
    end_time = parse_time(end) if end else None

    start_hour = start_time[0] if start_time else 0
    start_minute = start_time[1] if start_time else 0
    end_hour = end_time[0] if end_time else 23
    end_minute = end_time[1] if end_time else 59

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: CalWeekParams = {
        "start_date": datetime_to_local_date_str_optional(start_date),
        "num_days": num_days,
        "day_width": day_width,
        "granularity": granularity,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "project": project,
        "start": start,
        "end": end,
    }
    update_cached_dispatch(TerminalView.CAL_WEEK, terminal_params)

    calendar_week_view(
        active_context_name,
        "calendar-week",
        time_audits,
        events,
        tasks,
        start_date,
        num_days,
        day_width,
        granularity,
        show_scheduled_tasks,
        show_due_tasks,
        start_hour,
        start_minute,
        end_hour,
        end_minute,
    )


@app.command("cal-days, cds")
def cal_days(
    start_date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start-date",
            "-sd",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    num_days: Annotated[
        int,
        typer.Option(
            "--num-days",
            "-n",
            help="Number of days to display",
        ),
    ] = 7,
    day_width: Annotated[
        int,
        typer.Option(
            "--day-width",
            "-w",
            help="Width of each day column in characters",
        ),
    ] = 30,
    granularity: Annotated[
        int,
        typer.Option(
            "--granularity",
            "-g",
            help="Time interval in minutes (15, 30, or 60)",
        ),
    ] = 60,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted time audits and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in calendar",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in calendar"
        ),
    ] = True,
    show_time_audits: Annotated[
        bool,
        typer.Option(
            "--show-time-audits/--no-show-time-audits",
            help="Show time audits in calendar",
        ),
    ] = True,
    show_trackers: Annotated[
        bool,
        typer.Option(
            "--show-trackers/--no-show-trackers",
            help="Show tracker entries as pips in calendar",
        ),
    ] = False,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start",
            "-s",
            help="Start time for calendar display (HH:mm format, e.g., 8:00)",
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option(
            "--end",
            "-e",
            help="End time for calendar display (HH:mm format, e.g., 17:00)",
        ),
    ] = None,
) -> None:
    """Display a multi-day calendar starting from today, showing time audits and events horizontally across days."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.tracker import TRACKER_REPO

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    tasks = TASK_REPO.get_all_tasks()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Fetch trackers and entries if show_trackers is enabled
    trackers: list[Tracker] = []
    entries: list[Entry] = []
    if show_trackers:
        trackers = TRACKER_REPO.get_all_trackers()
        entries = ENTRY_REPO.get_all_entries()

        # Filter out deleted/archived trackers and deleted entries
        trackers = [
            t for t in trackers if t["deleted"] is None and t["archived"] is None
        ]
        entries = [e for e in entries if e["deleted"] is None]

    # Filter out deleted items by default
    if not include_deleted:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["deleted"] is None
        ]
        events = [event for event in events if event["deleted"] is None]
        tasks = [task for task in tasks if task["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["project"] == project
        ]
        events = [event for event in events if event["project"] == project]
        tasks = [task for task in tasks if task["project"] == project]
        if show_trackers:
            trackers = [t for t in trackers if t["project"] == project]
            entries = [e for e in entries if e["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        if show_trackers:
            trackers = cast(
                list[Tracker],
                context_filter.filter(cast(list[dict[str, Any]], trackers)),
            )
            entries = cast(
                list[Entry],
                context_filter.filter(cast(list[dict[str, Any]], entries)),
            )

    effective_days = num_days

    # Parse time boundaries
    start_time = parse_time(start) if start else None
    end_time = parse_time(end) if end else None

    start_hour = start_time[0] if start_time else 0
    start_minute = start_time[1] if start_time else 0
    end_hour = end_time[0] if end_time else 23
    end_minute = end_time[1] if end_time else 59

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: CalDaysParams = {
        "start_date": datetime_to_local_date_str_optional(start_date),
        "num_days": num_days,
        "day_width": day_width,
        "granularity": granularity,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "show_time_audits": show_time_audits,
        "show_trackers": show_trackers,
        "project": project,
        "start": start,
        "end": end,
    }
    update_cached_dispatch(TerminalView.CAL_DAYS, terminal_params)

    calendar_days_view(
        active_context_name,
        "calendar-days",
        time_audits,
        events,
        tasks,
        start_date,
        effective_days,
        day_width,
        granularity,
        show_scheduled_tasks,
        show_due_tasks,
        show_time_audits,
        start_hour,
        start_minute,
        end_hour,
        end_minute,
        trackers=trackers,
        entries=entries,
        show_trackers=show_trackers,
    )


@app.command("cal-month, cm")
def cal_month(
    date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--date",
            "-d",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    cell_width: Annotated[
        int,
        typer.Option(
            "--cell-width",
            "-w",
            help="Width of each day cell in characters",
        ),
    ] = 20,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted tasks and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in calendar",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in calendar"
        ),
    ] = True,
    show_all_day_events: Annotated[
        bool,
        typer.Option(
            "--show-all-day-events/--no-show-all-day-events",
            help="Show all-day events in calendar",
        ),
    ] = True,
    show_non_all_day_events: Annotated[
        bool,
        typer.Option(
            "--show-time-events/--no-show-time-events",
            help="Show time events in calendar",
        ),
    ] = True,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
) -> None:
    """Display a monthly calendar grid showing tasks by their scheduled and due dates, and events."""
    tasks = TASK_REPO.get_all_tasks()
    events = EVENT_REPO.get_all_events()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items by default
    if not include_deleted:
        tasks = [task for task in tasks if task["deleted"] is None]
        events = [event for event in events if event["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        tasks = [task for task in tasks if task["project"] == project]
        events = [event for event in events if event["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task], context_filter.filter(cast(list[dict[str, Any]], tasks))
        )
        events = cast(
            list[Event], context_filter.filter(cast(list[dict[str, Any]], events))
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: CalMonthParams = {
        "date": datetime_to_local_date_str_optional(date),
        "cell_width": cell_width,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "show_all_day_events": show_all_day_events,
        "show_non_all_day_events": show_non_all_day_events,
        "project": project,
    }
    update_cached_dispatch(TerminalView.CAL_MONTH, terminal_params)

    calendar_month_view(
        active_context_name,
        "calendar-month",
        tasks,
        events,
        date,
        cell_width,
        show_scheduled_tasks,
        show_due_tasks,
        show_all_day_events,
        show_non_all_day_events,
    )


@app.command("cal-quarter, cq")
def cal_quarter(
    date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--date",
            "-d",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    cell_width: Annotated[
        int,
        typer.Option(
            "--cell-width",
            "-w",
            help="Width of each day cell in characters",
        ),
    ] = 20,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted tasks and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in calendar",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in calendar"
        ),
    ] = True,
    show_all_day_events: Annotated[
        bool,
        typer.Option(
            "--show-all-day-events/--no-show-all-day-events",
            help="Show all-day events in calendar",
        ),
    ] = True,
    show_non_all_day_events: Annotated[
        bool,
        typer.Option(
            "--show-time-events/--no-show-time-events",
            help="Show time events in calendar",
        ),
    ] = False,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
) -> None:
    """Display a quarterly calendar showing 3 months with tasks by their scheduled and due dates, and events."""
    tasks = TASK_REPO.get_all_tasks()
    events = EVENT_REPO.get_all_events()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items by default
    if not include_deleted:
        tasks = [task for task in tasks if task["deleted"] is None]
        events = [event for event in events if event["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        tasks = [task for task in tasks if task["project"] == project]
        events = [event for event in events if event["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task], context_filter.filter(cast(list[dict[str, Any]], tasks))
        )
        events = cast(
            list[Event], context_filter.filter(cast(list[dict[str, Any]], events))
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: CalQuarterParams = {
        "date": datetime_to_local_date_str_optional(date),
        "cell_width": cell_width,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "show_all_day_events": show_all_day_events,
        "show_non_all_day_events": show_non_all_day_events,
        "project": project,
    }
    update_cached_dispatch(TerminalView.CAL_QUARTER, terminal_params)

    calendar_quarter_view(
        active_context_name,
        "calendar-quarter",
        tasks,
        events,
        date,
        cell_width,
        show_scheduled_tasks,
        show_due_tasks,
        show_all_day_events,
        show_non_all_day_events,
    )


@app.command("agenda, a")
def cal_agenda_days(
    num_days: Annotated[
        int,
        typer.Option(
            "--num-days",
            "-n",
            help="Number of days to display",
        ),
    ] = 7,
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="Start date for agenda (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    only_active_days: Annotated[
        bool,
        typer.Option(
            "--only-active-days/--all-days",
            help="Show only days with activity vs all days in range",
        ),
    ] = False,
    include_deleted: Annotated[
        bool,
        typer.Option(
            "--include-deleted", "-i", help="Include deleted tasks and events"
        ),
    ] = False,
    show_scheduled_tasks: Annotated[
        bool,
        typer.Option(
            "--show-scheduled-tasks/--no-show-scheduled-tasks",
            help="Show scheduled tasks in agenda",
        ),
    ] = True,
    show_due_tasks: Annotated[
        bool,
        typer.Option(
            "--show-due-tasks/--no-show-due-tasks", help="Show due tasks in agenda"
        ),
    ] = True,
    show_time_audits: Annotated[
        bool,
        typer.Option(
            "--show-time-audits/--no-show-time-audits",
            help="Show time audit chronology in agenda",
        ),
    ] = False,
    show_events: Annotated[
        bool,
        typer.Option(
            "--show-events/--no-show-events", help="Show calendar events in agenda"
        ),
    ] = True,
    show_timespans: Annotated[
        bool,
        typer.Option(
            "--show-timespans/--no-show-timespans",
            help="Show active timespans in agenda",
        ),
    ] = True,
    show_logs: Annotated[
        bool,
        typer.Option(
            "--show-logs/--no-show-logs",
            help="Show log chronology in agenda",
        ),
    ] = False,
    show_notes: Annotated[
        bool,
        typer.Option(
            "--show-notes/--no-show-notes",
            help="Show note chronology in agenda",
        ),
    ] = False,
    limit_note_lines: Annotated[
        Optional[int],
        typer.Option(
            "--limit-note-lines",
            help="Limit the number of lines displayed per note",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Filter items by project"),
    ] = None,
    time_audit_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--time-audit-meta-color",
            help="Color for time audit metadata (default: dim)",
        ),
    ] = None,
    log_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--log-meta-color",
            help="Color for log metadata (default: dim)",
        ),
    ] = None,
    note_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--note-meta-color",
            help="Color for note metadata (default: dim)",
        ),
    ] = None,
) -> None:
    """Display an agenda view showing events, tasks, and active timespans as a list grouped by day."""
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    tasks = TASK_REPO.get_all_tasks()
    timespans = TIMESPAN_REPO.get_all_timespans()
    logs = LOG_REPO.get_all_logs()
    notes = NOTE_REPO.get_all_notes()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted items by default
    if not include_deleted:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["deleted"] is None
        ]
        events = [event for event in events if event["deleted"] is None]
        tasks = [task for task in tasks if task["deleted"] is None]
        timespans = [timespan for timespan in timespans if timespan["deleted"] is None]
        logs = [log for log in logs if log["deleted"] is None]
        notes = [note for note in notes if note["deleted"] is None]

    # Filter by project if provided
    if project is not None:
        time_audits = [
            time_audit for time_audit in time_audits if time_audit["project"] == project
        ]
        events = [event for event in events if event["project"] == project]
        tasks = [task for task in tasks if task["project"] == project]
        timespans = [
            timespan for timespan in timespans if timespan["project"] == project
        ]
        logs = [log for log in logs if log["project"] == project]
        notes = [note for note in notes if note["project"] == project]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        timespans = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans)),
        )
        logs = cast(
            list[Log],
            context_filter.filter(cast(list[dict[str, Any]], logs)),
        )
        notes = cast(
            list[Note],
            context_filter.filter(cast(list[dict[str, Any]], notes)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: AgendaParams = {
        "num_days": num_days,
        "start": datetime_to_local_date_str_optional(start),
        "only_active_days": only_active_days,
        "include_deleted": include_deleted,
        "show_scheduled_tasks": show_scheduled_tasks,
        "show_due_tasks": show_due_tasks,
        "show_time_audits": show_time_audits,
        "show_events": show_events,
        "show_timespans": show_timespans,
        "show_logs": show_logs,
        "show_notes": show_notes,
        "limit_note_lines": limit_note_lines,
        "project": project,
        "time_audit_meta_color": time_audit_meta_color,
        "log_meta_color": log_meta_color,
        "note_meta_color": note_meta_color,
    }
    update_cached_dispatch(TerminalView.AGENDA, terminal_params)

    calendar_agenda_days_view(
        active_context_name,
        "calendar-agenda-days",
        time_audits,
        events,
        tasks,
        timespans,
        logs,
        notes,
        num_days=num_days,
        start_date=start,
        only_active_days=only_active_days,
        show_scheduled_tasks=show_scheduled_tasks,
        show_due_tasks=show_due_tasks,
        show_events=show_events,
        show_timespans=show_timespans,
        show_logs=show_logs,
        show_notes=show_notes,
        show_time_audits=show_time_audits,
        limit_note_lines=limit_note_lines,
        time_audit_meta_color=time_audit_meta_color
        if time_audit_meta_color is not None
        else TIME_AUDIT_META_COLOR,
        log_meta_color=log_meta_color if log_meta_color is not None else LOG_META_COLOR,
        note_meta_color=note_meta_color
        if note_meta_color is not None
        else NOTE_META_COLOR,
    )


@app.command("story, s")
def story(
    task: Annotated[
        Optional[list[int]],
        typer.Option("--task", "-T", help="Task ID to anchor story on (can repeat)"),
    ] = None,
    time_audit: Annotated[
        Optional[list[int]],
        typer.Option(
            "--time-audit", "-A", help="Time audit ID to anchor story on (can repeat)"
        ),
    ] = None,
    event: Annotated[
        Optional[list[int]],
        typer.Option("--event", "-E", help="Event ID to anchor story on (can repeat)"),
    ] = None,
    project: Annotated[
        Optional[list[str]],
        typer.Option(
            "--project",
            "-p",
            help="Project name to anchor story on - exact match (can repeat)",
            autocompletion=complete_project,
        ),
    ] = None,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag",
            "-t",
            help="Tag name to anchor story on (can repeat)",
            autocompletion=complete_tag,
        ),
    ] = None,
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="Override start date (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="Override end date (YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1)",
        ),
    ] = None,
    only_active_days: Annotated[
        bool,
        typer.Option(
            "--only-active-days/--all-days",
            help="Show only days with activity vs all days in range",
        ),
    ] = True,
    show_tasks: Annotated[
        bool,
        typer.Option("--show-tasks/--no-tasks", help="Show tasks"),
    ] = True,
    show_time_audits: Annotated[
        bool,
        typer.Option("--show-time-audits/--no-time-audits", help="Show time audits"),
    ] = True,
    show_events: Annotated[
        bool,
        typer.Option("--show-events/--no-events", help="Show events"),
    ] = True,
    show_timespans: Annotated[
        bool,
        typer.Option("--show-timespans/--no-timespans", help="Show timespans"),
    ] = True,
    show_logs: Annotated[
        bool,
        typer.Option("--show-logs/--no-logs", help="Show logs"),
    ] = True,
    show_notes: Annotated[
        bool,
        typer.Option("--show-notes/--no-notes", help="Show notes"),
    ] = True,
    show_entries: Annotated[
        bool,
        typer.Option("--show-entries/--no-entries", help="Show tracker entries"),
    ] = True,
    limit_note_lines: Annotated[
        Optional[int],
        typer.Option(
            "--limit-note-lines",
            help="Limit the number of lines displayed per note",
        ),
    ] = None,
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted entities"),
    ] = False,
    time_audit_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--time-audit-meta-color",
            help="Color for time audit metadata (default: dim)",
        ),
    ] = None,
    log_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--log-meta-color",
            help="Color for log metadata (default: dim)",
        ),
    ] = None,
    note_meta_color: Annotated[
        Optional[str],
        typer.Option(
            "--note-meta-color",
            help="Color for note metadata (default: dim)",
        ),
    ] = None,
) -> None:
    """Display a story view showing all entities related to anchor entities.

    At least one anchor option (--task, --time-audit, --event, --project, or --tag) is required.
    When multiple anchors are specified, entities matching ALL criteria are shown (AND logic).
    """
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.id_map import ID_MAP_REPO
    from granular.repository.tracker import TRACKER_REPO

    # Validate that at least one anchor is specified
    if not any([task, time_audit, event, project, tag]):
        raise typer.BadParameter(
            "At least one anchor option (--task, --time-audit, --event, --project, or --tag) is required"
        )

    # Get all data
    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    timespans = TIMESPAN_REPO.get_all_timespans()
    logs = LOG_REPO.get_all_logs()
    notes = NOTE_REPO.get_all_notes()
    trackers = TRACKER_REPO.get_all_trackers()
    entries = ENTRY_REPO.get_all_entries()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )
        events = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events)),
        )
        timespans = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans)),
        )
        logs = cast(
            list[Log],
            context_filter.filter(cast(list[dict[str, Any]], logs)),
        )
        notes = cast(
            list[Note],
            context_filter.filter(cast(list[dict[str, Any]], notes)),
        )
        trackers = cast(
            list[Tracker],
            context_filter.filter(cast(list[dict[str, Any]], trackers)),
        )
        entries = cast(
            list[Entry],
            context_filter.filter(cast(list[dict[str, Any]], entries)),
        )

    # Convert mapped IDs to real IDs for task, time_audit, and event anchors
    real_task_ids: Optional[list[int]] = None
    if task is not None:
        real_task_ids = [ID_MAP_REPO.get_real_id("tasks", tid) for tid in task]

    real_time_audit_ids: Optional[list[int]] = None
    if time_audit is not None:
        real_time_audit_ids = [
            ID_MAP_REPO.get_real_id("time_audits", taid) for taid in time_audit
        ]

    real_event_ids: Optional[list[int]] = None
    if event is not None:
        real_event_ids = [ID_MAP_REPO.get_real_id("events", eid) for eid in event]

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: StoryParams = {
        "task": task,
        "time_audit": time_audit,
        "event": event,
        "project": project,
        "tag": tag,
        "start": datetime_to_local_date_str_optional(start),
        "end": datetime_to_local_date_str_optional(end),
        "only_active_days": only_active_days,
        "show_tasks": show_tasks,
        "show_time_audits": show_time_audits,
        "show_events": show_events,
        "show_timespans": show_timespans,
        "show_logs": show_logs,
        "show_notes": show_notes,
        "show_entries": show_entries,
        "limit_note_lines": limit_note_lines,
        "include_deleted": include_deleted,
        "time_audit_meta_color": time_audit_meta_color,
        "log_meta_color": log_meta_color,
        "note_meta_color": note_meta_color,
    }
    update_cached_dispatch(TerminalView.STORY, terminal_params)

    story_view(
        active_context_name,
        "story",
        tasks,
        time_audits,
        events,
        timespans,
        logs,
        notes,
        entries=entries,
        trackers=trackers,
        task_ids=real_task_ids,
        time_audit_ids=real_time_audit_ids,
        event_ids=real_event_ids,
        projects=project,
        tags=tag,
        start_date=start,
        end_date=end,
        only_active_days=only_active_days,
        show_tasks=show_tasks,
        show_time_audits=show_time_audits,
        show_events=show_events,
        show_timespans=show_timespans,
        show_logs=show_logs,
        show_notes=show_notes,
        show_entries=show_entries,
        limit_note_lines=limit_note_lines,
        include_deleted=include_deleted,
        time_audit_meta_color=time_audit_meta_color
        if time_audit_meta_color is not None
        else TIME_AUDIT_META_COLOR,
        log_meta_color=log_meta_color if log_meta_color is not None else LOG_META_COLOR,
        note_meta_color=note_meta_color
        if note_meta_color is not None
        else NOTE_META_COLOR,
    )


@app.command("tracker-today, tt")
def tracker_today(
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
) -> None:
    """Show today's status for all active trackers."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.tracker import TRACKER_REPO
    from granular.view.view.views.tracker import tracker_today_view

    trackers = TRACKER_REPO.get_all_trackers()
    entries = ENTRY_REPO.get_all_entries()
    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Filter out deleted and archived trackers
    trackers = [t for t in trackers if t["deleted"] is None and t["archived"] is None]

    # Filter out deleted entries
    entries = [e for e in entries if e["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        trackers = cast(
            list[Tracker],
            context_filter.filter(cast(list[dict[str, Any]], trackers)),
        )
        entries = cast(
            list[Entry],
            context_filter.filter(cast(list[dict[str, Any]], entries)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TrackerTodayParams = {
        "no_color": no_color,
    }
    update_cached_dispatch(TerminalView.TRACKER_TODAY, terminal_params)

    tracker_today_view(
        active_context=active_context_name,
        trackers=trackers,
        entries=entries,
    )


@app.command("tracker-heatmap, th")
def tracker_heatmap(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to show"),
    ] = 14,
    left_width: Annotated[
        int,
        typer.Option(
            "--left-width", "-lw", help="Width of left column for tracker names"
        ),
    ] = 30,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag",
            "-t",
            help="Filter trackers that have any of these tags",
            autocompletion=complete_tag,
        ),
    ] = None,
) -> None:
    """Show gantt-style heatmap for all active trackers."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.tracker import TRACKER_REPO

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Get all non-archived, non-deleted trackers
    trackers = TRACKER_REPO.get_all_trackers()
    trackers = [t for t in trackers if t["deleted"] is None and t["archived"] is None]

    # Get all entries
    entries = ENTRY_REPO.get_all_entries()

    # Filter out deleted entries
    entries = [e for e in entries if e["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        trackers = cast(
            list[Tracker],
            context_filter.filter(cast(list[dict[str, Any]], trackers)),
        )
        entries = cast(
            list[Entry],
            context_filter.filter(cast(list[dict[str, Any]], entries)),
        )

    # Filter by tags if provided (any tag must match - OR logic)
    if tag is not None:
        trackers = [
            t
            for t in trackers
            if t["tags"] is not None and any(tg in t["tags"] for tg in tag)
        ]
        # Also filter entries to only include entries from matching trackers
        tracker_ids = {t["id"] for t in trackers}
        entries = [e for e in entries if e["tracker_id"] in tracker_ids]

    # Calculate date range: last N days ending today
    today = pendulum.today("local")
    start_date = today.subtract(days=days - 1)
    end_date = today

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TrackerHeatmapParams = {
        "days": days,
        "left_width": left_width,
        "tag": tag,
    }
    update_cached_dispatch(TerminalView.TRACKER_HEATMAP, terminal_params)

    gantt_view(
        active_context_name,
        "tracker-heatmap",
        timespans=[],
        events=[],
        tasks=[],
        trackers=trackers,
        entries=entries,
        start=start_date,
        end=end_date,
        granularity="day",
        show_tasks=False,
        show_timespans=False,
        show_events=False,
        show_trackers=True,
        left_column_width=left_width,
    )


@app.command("tasks-heatmap, tsh")
def tasks_heatmap(
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to show"),
    ] = 14,
    left_width: Annotated[
        int,
        typer.Option("--left-width", "-lw", help="Width of left column for label"),
    ] = 30,
    tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag",
            "-t",
            help="Show separate heatmap rows for these tags",
            autocompletion=complete_tag,
        ),
    ] = None,
    no_tag: Annotated[
        Optional[list[str]],
        typer.Option(
            "--no-tag",
            "-nt",
            help="Filter out tasks/time audits that have any of these tags",
            autocompletion=complete_tag,
        ),
    ] = None,
    project: Annotated[
        Optional[list[str]],
        typer.Option(
            "--project",
            "-p",
            help="Show separate heatmap rows for these projects",
            autocompletion=complete_project,
        ),
    ] = None,
) -> None:
    """Show heatmap of task completions and time audit activity.

    When multiple --project or --tag options are provided, each one gets
    its own row in the heatmap display.
    """
    from granular.view.view.views.gantt import tasks_heatmap_view

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Get all non-deleted tasks and time audits
    tasks = TASK_REPO.get_all_tasks()
    tasks = [t for t in tasks if t["deleted"] is None]

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    time_audits = [ta for ta in time_audits if ta["deleted"] is None]

    # Filter out tasks/time audits with any of the no_tag tags
    if no_tag is not None:
        tasks = [
            task
            for task in tasks
            if task["tags"] is None or not any(t in task["tags"] for t in no_tag)
        ]
        time_audits = [
            ta
            for ta in time_audits
            if ta["tags"] is None or not any(t in ta["tags"] for t in no_tag)
        ]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        time_audits = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits)),
        )

    # Calculate date range: last N days ending today
    today = pendulum.today("local")
    start_date = today.subtract(days=days - 1)
    end_date = today

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TasksHeatmapParams = {
        "days": days,
        "left_width": left_width,
        "tag": tag,
        "no_tag": no_tag,
        "project": project,
    }
    update_cached_dispatch(TerminalView.TASKS_HEATMAP, terminal_params)

    tasks_heatmap_view(
        active_context_name,
        "tasks-heatmap",
        tasks,
        time_audits,
        start=start_date,
        end=end_date,
        granularity="day",
        left_column_width=left_width,
        projects=project,
        tags=tag,
    )


@app.command("tracker-summary, ts")
def tracker_summary(
    tracker_id: Annotated[int, typer.Argument(help="Tracker ID to view")],
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to show"),
    ] = 14,
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="Start date for summary",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="End date for summary",
        ),
    ] = None,
) -> None:
    """Show summary for a tracker over a date range."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.id_map import ID_MAP_REPO
    from granular.repository.tracker import TRACKER_REPO

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    real_tracker_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)
    tracker = TRACKER_REPO.get_tracker(real_tracker_id)
    entries = ENTRY_REPO.get_entries_for_tracker(real_tracker_id)

    # Filter out deleted entries
    entries = [e for e in entries if e["deleted"] is None]

    # Convert DateTime to Date if provided
    start_date = start.date() if start is not None else None
    end_date = end.date() if end is not None else None

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TrackerSummaryParams = {
        "tracker_id": tracker_id,
        "days": days,
        "start": datetime_to_local_date_str_optional(start),
        "end": datetime_to_local_date_str_optional(end),
    }
    update_cached_dispatch(TerminalView.TRACKER_SUMMARY, terminal_params)

    from granular.view.view.views.tracker import tracker_summary_view

    tracker_summary_view(
        active_context=active_context_name,
        tracker=tracker,
        entries=entries,
        start_date=start_date,
        end_date=end_date,
        days=days,
    )


@app.command("trackers, trs")
def trackers(
    show_archived: Annotated[
        bool, typer.Option("--archived", "-a", help="Show archived trackers")
    ] = False,
    include_deleted: Annotated[
        bool, typer.Option("--include-deleted", "-i", help="Include deleted trackers")
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
) -> None:
    """List all trackers."""
    from granular.repository.tracker import TRACKER_REPO
    from granular.view.view.views.tracker import trackers_view

    trackers_list = TRACKER_REPO.get_all_trackers()
    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Filter by archived status
    if not show_archived:
        trackers_list = [t for t in trackers_list if t["archived"] is None]

    # Filter out deleted by default
    if not include_deleted:
        trackers_list = [t for t in trackers_list if t["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        trackers_list = cast(
            list[Tracker],
            context_filter.filter(cast(list[dict[str, Any]], trackers_list)),
        )

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: TrackersParams = {
        "show_archived": show_archived,
        "include_deleted": include_deleted,
        "no_color": no_color,
    }
    update_cached_dispatch(TerminalView.TRACKERS, terminal_params)

    trackers_view(
        active_context=active_context_name,
        report_name="trackers",
        trackers=trackers_list,
        use_color=not no_color,
    )


@app.command("tracker, tr")
def tracker(
    tracker_id: Annotated[int, typer.Argument(help="Tracker ID to view")],
) -> None:
    """Display full details for a single tracker."""
    from granular.repository.id_map import ID_MAP_REPO
    from granular.repository.tracker import TRACKER_REPO
    from granular.view.view.views.tracker import single_tracker_view

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    real_tracker_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)
    tracker_obj = TRACKER_REPO.get_tracker(real_tracker_id)

    clear_id_map_if_required()

    # Single entity views are not cached
    single_tracker_view(
        active_context=active_context_name,
        tracker=tracker_obj,
    )


@app.command("entries, ens")
def entries(
    tracker_id: Annotated[int, typer.Argument(help="Tracker ID to view entries for")],
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days to show"),
    ] = 14,
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted entries"),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable entity color in table rows"),
    ] = False,
) -> None:
    """List entries for a tracker."""
    from granular.repository.entry import ENTRY_REPO
    from granular.repository.id_map import ID_MAP_REPO
    from granular.repository.tracker import TRACKER_REPO
    from granular.time import now_utc
    from granular.view.view.views.entry import entries_view

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    real_tracker_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)
    tracker_obj = TRACKER_REPO.get_tracker(real_tracker_id)
    entries_list = ENTRY_REPO.get_entries_for_tracker(real_tracker_id)

    # Filter by date range
    cutoff_date = now_utc().subtract(days=days)
    entries_list = [e for e in entries_list if e["timestamp"] >= cutoff_date]

    # Filter out deleted by default
    if not include_deleted:
        entries_list = [e for e in entries_list if e["deleted"] is None]

    # Apply context filter
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        entries_list = cast(
            list[Entry],
            context_filter.filter(cast(list[dict[str, Any]], entries_list)),
        )

    # Sort by timestamp descending
    entries_list.sort(key=lambda e: e["timestamp"], reverse=True)

    clear_id_map_if_required()

    # Cache terminal-level parameters for replay
    terminal_params: EntriesParams = {
        "tracker_id": tracker_id,
        "days": days,
        "include_deleted": include_deleted,
        "no_color": no_color,
    }
    update_cached_dispatch(TerminalView.ENTRIES, terminal_params)

    entries_view(
        active_context=active_context_name,
        tracker=tracker_obj,
        entries=entries_list,
        use_color=not no_color,
    )
