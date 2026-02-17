# SPDX-License-Identifier: MIT

from typing import Any, cast

from rich.console import Console
from rich.markdown import Markdown

try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    pass  # type: ignore[assignment]


from granular.color import (
    LOG_META_COLOR,
    NOTE_META_COLOR,
    TIME_AUDIT_META_COLOR,
)
from granular.id_map import clear_id_map_if_required
from granular.model.custom_view import (
    AgendaSubView,
    CompoundView,
    EventSubView,
    GanttSubView,
    HeaderSubView,
    LogSubView,
    MarkdownSubView,
    SpaceSubView,
    StorySubView,
    TasksHeatmapSubView,
    TaskSubView,
    TimeAuditSubView,
    TimespanSubView,
)
from granular.model.entity_id import EntityId
from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.query.filter import generate_filter
from granular.query.sort import sort_items
from granular.repository.context import CONTEXT_REPO
from granular.repository.entry import ENTRY_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.repository.tracker import TRACKER_REPO
from granular.view.state import set_show_header
from granular.view.view.views.calendar import calendar_agenda_days_view
from granular.view.view.views.event import events_view
from granular.view.view.views.gantt import gantt_view, tasks_heatmap_view
from granular.view.view.views.header import header
from granular.view.view.views.log import logs_view
from granular.view.view.views.story import story_view
from granular.view.view.views.task import tasks_view
from granular.view.view.views.time_audit import time_audits_report
from granular.view.view.views.timespan import timespans_view


def compound_view_command(
    compound_view: CompoundView,
) -> None:
    """Execute a compound view consisting of multiple sub-views."""
    # Get active context
    active_context = CONTEXT_REPO.get_active_context()
    clear_id_map_if_required()

    # Execute each sub-view in sequence
    for sub_view in compound_view["views"]:
        view_type = sub_view["view_type"]

        if view_type == "task":
            __execute_task_sub_view(
                cast(TaskSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "time_audit":
            __execute_time_audit_sub_view(
                cast(TimeAuditSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "event":
            __execute_event_sub_view(
                cast(EventSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "timespan":
            __execute_timespan_sub_view(
                cast(TimespanSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "log":
            __execute_log_sub_view(
                cast(LogSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "markdown":
            __execute_markdown_sub_view(cast(MarkdownSubView, sub_view))
        elif view_type == "header":
            __execute_header_sub_view(
                cast(HeaderSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "space":
            __execute_space_sub_view(cast(SpaceSubView, sub_view))
        elif view_type == "agenda":
            __execute_agenda_sub_view(
                cast(AgendaSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "gantt":
            __execute_gantt_sub_view(
                cast(GanttSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "tasks_heatmap":
            __execute_tasks_heatmap_sub_view(
                cast(TasksHeatmapSubView, sub_view),
                compound_view["name"],
                active_context,
            )
        elif view_type == "story":
            __execute_story_sub_view(
                cast(StorySubView, sub_view),
                compound_view["name"],
                active_context,
            )


def __execute_task_sub_view(
    sub_view: TaskSubView,
    view_name: str,
    active_context: Any,
) -> None:
    tasks_original = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()

    # Filter out deleted tasks by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        tasks_original = [task for task in tasks_original if task["deleted"] is None]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks_original = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks_original)),
        )

    tasks = cast(list[dict[str, Any]], tasks_original)

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        tasks = filter.filter(tasks)

    if "sort" in sub_view and sub_view["sort"] is not None:
        tasks = sort_items(tasks, sub_view["sort"])

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Handle no_color option from sub-view (default to False)
    no_color = sub_view.get("no_color", False)

    # Handle no_wrap option from sub-view (default to False)
    no_wrap = sub_view.get("no_wrap", False)

    tasks_view(
        active_context["name"],
        view_name,
        cast(list[Task], tasks),
        columns=sub_view["columns"],
        time_audits=time_audits,
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap if no_wrap is not None else False,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_time_audit_sub_view(
    sub_view: TimeAuditSubView,
    view_name: str,
    active_context: Any,
) -> None:
    time_audits_original = TIME_AUDIT_REPO.get_all_time_audits()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()

    # Filter out deleted time audits by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        time_audits_original = [
            time_audit
            for time_audit in time_audits_original
            if time_audit["deleted"] is None
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        time_audits_original = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits_original)),
        )

    time_audits = cast(list[dict[str, Any]], time_audits_original)

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        time_audits = filter.filter(time_audits)

    if "sort" in sub_view and sub_view["sort"] is not None:
        time_audits = sort_items(time_audits, sub_view["sort"])

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Handle no_color option from sub-view (default to False)
    no_color = sub_view.get("no_color", False)

    # Handle no_wrap option from sub-view (default to False)
    no_wrap = sub_view.get("no_wrap", False)

    time_audits_report(
        active_context["name"],
        view_name,
        cast(list[TimeAudit], time_audits),
        columns=sub_view["columns"],
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap if no_wrap is not None else False,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_event_sub_view(
    sub_view: EventSubView,
    view_name: str,
    active_context: Any,
) -> None:
    events_original = EVENT_REPO.get_all_events()
    notes = NOTE_REPO.get_all_notes()
    logs = LOG_REPO.get_all_logs()

    # Filter out deleted events by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        events_original = [
            event for event in events_original if event["deleted"] is None
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        events_original = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events_original)),
        )

    events = cast(list[dict[str, Any]], events_original)

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        events = filter.filter(events)

    if "sort" in sub_view and sub_view["sort"] is not None:
        events = sort_items(events, sub_view["sort"])

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Handle no_color option from sub-view (default to False)
    no_color = sub_view.get("no_color", False)

    # Handle no_wrap option from sub-view (default to False)
    no_wrap = sub_view.get("no_wrap", False)

    events_view(
        active_context["name"],
        view_name,
        cast(list[Event], events),
        columns=sub_view["columns"],
        notes=notes,
        logs=logs,
        use_color=not no_color,
        no_wrap=no_wrap if no_wrap is not None else False,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_timespan_sub_view(
    sub_view: TimespanSubView,
    view_name: str,
    active_context: Any,
) -> None:
    timespans_original = TIMESPAN_REPO.get_all_timespans()

    # Filter out deleted timespans by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        timespans_original = [
            timespan for timespan in timespans_original if timespan["deleted"] is None
        ]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        timespans_original = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans_original)),
        )

    timespans = cast(list[dict[str, Any]], timespans_original)

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        timespans = filter.filter(timespans)

    if "sort" in sub_view and sub_view["sort"] is not None:
        timespans = sort_items(timespans, sub_view["sort"])

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Handle no_color option from sub-view (default to False)
    no_color = sub_view.get("no_color", False)

    # Handle no_wrap option from sub-view (default to False)
    no_wrap = sub_view.get("no_wrap", False)

    timespans_view(
        active_context["name"],
        view_name,
        cast(list[Timespan], timespans),
        columns=sub_view["columns"],
        use_color=not no_color,
        no_wrap=no_wrap if no_wrap is not None else False,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_log_sub_view(
    sub_view: LogSubView,
    view_name: str,
    active_context: Any,
) -> None:
    logs_original = LOG_REPO.get_all_logs()

    # Filter out deleted logs by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        logs_original = [log for log in logs_original if log["deleted"] is None]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        logs_original = cast(
            list[Log],
            context_filter.filter(cast(list[dict[str, Any]], logs_original)),
        )

    logs = cast(list[dict[str, Any]], logs_original)

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        logs = filter.filter(logs)

    if "sort" in sub_view and sub_view["sort"] is not None:
        logs = sort_items(logs, sub_view["sort"])

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Handle no_color option from sub-view (default to False)
    no_color = sub_view.get("no_color", False)

    # Handle no_wrap option from sub-view (default to False)
    no_wrap = sub_view.get("no_wrap", False)

    logs_view(
        active_context["name"],
        view_name,
        cast(list[Log], logs),
        columns=sub_view["columns"],
        use_color=not no_color,
        no_wrap=no_wrap if no_wrap is not None else False,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_markdown_sub_view(sub_view: MarkdownSubView) -> None:
    """Render markdown content to the console."""
    console = Console()
    markdown_content = sub_view["markdown"]
    markdown = Markdown(markdown_content)
    console.print(markdown)


def __execute_header_sub_view(
    sub_view: HeaderSubView, view_name: str, active_context: Any
) -> None:
    """Render the view header."""
    header(active_context["name"], view_name)


def __execute_space_sub_view(sub_view: SpaceSubView) -> None:
    """Print an empty line for spacing."""
    console = Console()
    console.print()


def __execute_agenda_sub_view(
    sub_view: AgendaSubView,
    view_name: str,
    active_context: Any,
) -> None:
    """Execute an agenda sub-view showing tasks, events, and timespans."""
    # Get all data
    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    timespans = TIMESPAN_REPO.get_all_timespans()
    logs = LOG_REPO.get_all_logs()
    notes = NOTE_REPO.get_all_notes()

    # Apply context filter if present
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

    # Apply sub-view filter if present
    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        tasks = cast(list[Task], filter.filter(cast(list[dict[str, Any]], tasks)))
        time_audits = cast(
            list[TimeAudit], filter.filter(cast(list[dict[str, Any]], time_audits))
        )
        events = cast(list[Event], filter.filter(cast(list[dict[str, Any]], events)))
        timespans = cast(
            list[Timespan], filter.filter(cast(list[dict[str, Any]], timespans))
        )

    # Get configuration options from sub-view (with defaults)
    num_days_value = sub_view.get("num_days")
    start_value = sub_view.get("start")
    only_active_days_value = sub_view.get("only_active_days")
    show_scheduled_tasks_value = sub_view.get("show_scheduled_tasks")
    show_due_tasks_value = sub_view.get("show_due_tasks")
    show_events_value = sub_view.get("show_events")
    show_timespans_value = sub_view.get("show_timespans")
    show_logs_value = sub_view.get("show_logs")
    show_notes_value = sub_view.get("show_notes")
    show_time_audits_value = sub_view.get("show_time_audits")
    limit_note_lines_value = sub_view.get("limit_note_lines")
    time_audit_meta_color_value = sub_view.get("time_audit_meta_color")
    log_meta_color_value = sub_view.get("log_meta_color")
    note_meta_color_value = sub_view.get("note_meta_color")

    # Parse start date if provided
    start_date = None
    if start_value is not None:
        from granular.terminal.parse import parse_datetime

        start_date = parse_datetime(start_value)

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Call the agenda calendar view
    calendar_agenda_days_view(
        active_context["name"],
        view_name,
        time_audits,
        events,
        tasks,
        timespans,
        logs,
        notes,
        num_days=num_days_value if num_days_value is not None else 7,
        start_date=start_date,
        only_active_days=only_active_days_value
        if only_active_days_value is not None
        else False,
        show_scheduled_tasks=show_scheduled_tasks_value
        if show_scheduled_tasks_value is not None
        else True,
        show_due_tasks=show_due_tasks_value
        if show_due_tasks_value is not None
        else True,
        show_events=show_events_value if show_events_value is not None else True,
        show_timespans=show_timespans_value
        if show_timespans_value is not None
        else True,
        show_logs=bool(show_logs_value) if show_logs_value is not None else False,
        show_notes=bool(show_notes_value) if show_notes_value is not None else False,
        show_time_audits=bool(show_time_audits_value)
        if show_time_audits_value is not None
        else False,
        limit_note_lines=limit_note_lines_value,
        time_audit_meta_color=time_audit_meta_color_value
        if time_audit_meta_color_value is not None
        else TIME_AUDIT_META_COLOR,
        log_meta_color=log_meta_color_value
        if log_meta_color_value is not None
        else LOG_META_COLOR,
        note_meta_color=note_meta_color_value
        if note_meta_color_value is not None
        else NOTE_META_COLOR,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_gantt_sub_view(
    sub_view: GanttSubView,
    view_name: str,
    active_context: Any,
) -> None:
    """Execute a gantt sub-view showing timespans and events on a timeline."""
    timespans_original = TIMESPAN_REPO.get_all_timespans()
    events_original = EVENT_REPO.get_all_events()
    tasks_original = TASK_REPO.get_all_tasks()

    # Filter out deleted timespans, events, and tasks by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        timespans_original = [
            timespan for timespan in timespans_original if timespan["deleted"] is None
        ]
        events_original = [
            event for event in events_original if event["deleted"] is None
        ]
        tasks_original = [task for task in tasks_original if task["deleted"] is None]

    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        timespans_original = cast(
            list[Timespan],
            context_filter.filter(cast(list[dict[str, Any]], timespans_original)),
        )
        events_original = cast(
            list[Event],
            context_filter.filter(cast(list[dict[str, Any]], events_original)),
        )
        tasks_original = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks_original)),
        )

    timespans = timespans_original
    events = events_original
    tasks = tasks_original

    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        timespans = cast(
            list[Timespan],
            filter.filter(cast(list[dict[str, Any]], timespans)),
        )
        events = cast(list[Event], filter.filter(cast(list[dict[str, Any]], events)))
        tasks = cast(list[Task], filter.filter(cast(list[dict[str, Any]], tasks)))

    # Get configuration options from sub-view
    start_value = sub_view.get("start")
    end_value = sub_view.get("end")
    granularity_value = sub_view.get("granularity")
    show_tasks_value = sub_view.get("show_tasks")
    show_timespans_value = sub_view.get("show_timespans")
    show_events_value = sub_view.get("show_events")
    left_column_width_value = sub_view.get("left_column_width")

    # Parse start and end dates if provided
    start_date = None
    end_date = None
    if start_value is not None:
        from granular.terminal.parse import parse_datetime

        start_date = parse_datetime(start_value)
    if end_value is not None:
        from granular.terminal.parse import parse_datetime

        end_date = parse_datetime(end_value)

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Call the gantt report
    gantt_view(
        active_context["name"],
        view_name,
        timespans,
        events=events,
        tasks=tasks,
        start=start_date,
        end=end_date,
        granularity=granularity_value if granularity_value is not None else "day",  # type: ignore[arg-type]
        show_tasks=show_tasks_value if show_tasks_value is not None else False,
        show_timespans=show_timespans_value
        if show_timespans_value is not None
        else True,
        show_events=show_events_value if show_events_value is not None else True,
        left_column_width=left_column_width_value
        if left_column_width_value is not None
        else 40,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_tasks_heatmap_sub_view(
    sub_view: TasksHeatmapSubView,
    view_name: str,
    active_context: Any,
) -> None:
    """Execute a tasks heatmap sub-view showing task completions and time audit activity."""
    import pendulum

    tasks_original = TASK_REPO.get_all_tasks()
    time_audits_original = TIME_AUDIT_REPO.get_all_time_audits()

    # Filter out deleted items by default unless include_deleted is True
    include_deleted = sub_view.get("include_deleted", False)
    if not include_deleted:
        tasks_original = [task for task in tasks_original if task["deleted"] is None]
        time_audits_original = [
            ta for ta in time_audits_original if ta["deleted"] is None
        ]

    # Apply context filter if present
    if "filter" in active_context and active_context["filter"] is not None:
        context_filter = generate_filter(active_context["filter"])
        tasks_original = cast(
            list[Task],
            context_filter.filter(cast(list[dict[str, Any]], tasks_original)),
        )
        time_audits_original = cast(
            list[TimeAudit],
            context_filter.filter(cast(list[dict[str, Any]], time_audits_original)),
        )

    tasks = tasks_original
    time_audits = time_audits_original

    # Apply sub-view filter if present
    if "filter" in sub_view and sub_view["filter"] is not None:
        filter = generate_filter(sub_view["filter"])
        tasks = cast(
            list[Task],
            filter.filter(cast(list[dict[str, Any]], tasks)),
        )
        time_audits = cast(
            list[TimeAudit],
            filter.filter(cast(list[dict[str, Any]], time_audits)),
        )

    # Get configuration options from sub-view
    days_value = sub_view.get("days")
    start_value = sub_view.get("start")
    end_value = sub_view.get("end")
    granularity_value = sub_view.get("granularity")
    left_column_width_value = sub_view.get("left_column_width")
    projects_value = sub_view.get("projects")
    tags_value = sub_view.get("tags")

    # Calculate date range
    today = pendulum.today("local")
    start_date = None
    end_date = None

    if start_value is not None:
        from granular.terminal.parse import parse_datetime

        start_date = parse_datetime(start_value)
    if end_value is not None:
        from granular.terminal.parse import parse_datetime

        end_date = parse_datetime(end_value)

    # If days is specified and no start/end, calculate based on days
    if days_value is not None and start_date is None and end_date is None:
        end_date = today
        start_date = today.subtract(days=days_value - 1)

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Call the tasks heatmap report
    tasks_heatmap_view(
        active_context["name"],
        view_name,
        tasks,
        time_audits,
        start=start_date,
        end=end_date,
        granularity=granularity_value if granularity_value is not None else "day",  # type: ignore[arg-type]
        left_column_width=left_column_width_value
        if left_column_width_value is not None
        else 30,
        projects=projects_value,
        tags=tags_value,
    )

    # Reset header state
    if no_header:
        set_show_header(True)


def __execute_story_sub_view(
    sub_view: StorySubView,
    view_name: str,
    active_context: Any,
) -> None:
    """Execute a story sub-view showing related entities for anchor entities."""
    from granular.repository.id_map import ID_MAP_REPO

    # Get all data
    tasks = TASK_REPO.get_all_tasks()
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    events = EVENT_REPO.get_all_events()
    timespans = TIMESPAN_REPO.get_all_timespans()
    logs = LOG_REPO.get_all_logs()
    notes = NOTE_REPO.get_all_notes()

    # Get tracker data
    trackers = TRACKER_REPO.get_all_trackers()
    entries = ENTRY_REPO.get_all_entries()

    # Apply context filter if present
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

    # Get configuration options from sub-view
    task_value = sub_view.get("task")
    time_audit_value = sub_view.get("time_audit")
    event_value = sub_view.get("event")
    project_value = sub_view.get("project")
    tag_value = sub_view.get("tag")
    start_value = sub_view.get("start")
    end_value = sub_view.get("end")
    only_active_days_value = sub_view.get("only_active_days")
    show_tasks_value = sub_view.get("show_tasks")
    show_time_audits_value = sub_view.get("show_time_audits")
    show_events_value = sub_view.get("show_events")
    show_timespans_value = sub_view.get("show_timespans")
    show_logs_value = sub_view.get("show_logs")
    show_notes_value = sub_view.get("show_notes")
    show_entries_value = sub_view.get("show_entries")
    limit_note_lines_value = sub_view.get("limit_note_lines")
    include_deleted_value = sub_view.get("include_deleted")
    time_audit_meta_color_value = sub_view.get("time_audit_meta_color")
    log_meta_color_value = sub_view.get("log_meta_color")
    note_meta_color_value = sub_view.get("note_meta_color")

    # Convert anchor values to lists
    task_ids: list[EntityId] | None = None
    if task_value is not None:
        if isinstance(task_value, int):
            task_ids = [ID_MAP_REPO.get_real_id("tasks", task_value)]
        else:
            task_ids = [ID_MAP_REPO.get_real_id("tasks", tid) for tid in task_value]

    time_audit_ids: list[EntityId] | None = None
    if time_audit_value is not None:
        if isinstance(time_audit_value, int):
            time_audit_ids = [ID_MAP_REPO.get_real_id("time_audits", time_audit_value)]
        else:
            time_audit_ids = [
                ID_MAP_REPO.get_real_id("time_audits", taid)
                for taid in time_audit_value
            ]

    event_ids: list[EntityId] | None = None
    if event_value is not None:
        if isinstance(event_value, int):
            event_ids = [ID_MAP_REPO.get_real_id("events", event_value)]
        else:
            event_ids = [ID_MAP_REPO.get_real_id("events", eid) for eid in event_value]

    projects: list[str] | None = None
    if project_value is not None:
        if isinstance(project_value, str):
            projects = [project_value]
        else:
            projects = project_value

    tags: list[str] | None = None
    if tag_value is not None:
        if isinstance(tag_value, str):
            tags = [tag_value]
        else:
            tags = tag_value

    # Parse start and end dates if provided
    start_date = None
    end_date = None
    if start_value is not None:
        from granular.terminal.parse import parse_datetime

        start_date = parse_datetime(start_value)
    if end_value is not None:
        from granular.terminal.parse import parse_datetime

        end_date = parse_datetime(end_value)

    # Handle no_header option
    no_header = sub_view.get("no_header", False)
    if no_header:
        set_show_header(False)

    # Call the story report
    story_view(
        active_context["name"],
        view_name,
        tasks,
        time_audits,
        events,
        timespans,
        logs,
        notes,
        entries=entries,
        trackers=trackers,
        task_ids=task_ids,
        time_audit_ids=time_audit_ids,
        event_ids=event_ids,
        projects=projects,
        tags=tags,
        start_date=start_date,
        end_date=end_date,
        only_active_days=only_active_days_value
        if only_active_days_value is not None
        else True,
        show_tasks=show_tasks_value if show_tasks_value is not None else True,
        show_time_audits=show_time_audits_value
        if show_time_audits_value is not None
        else True,
        show_events=show_events_value if show_events_value is not None else True,
        show_timespans=show_timespans_value
        if show_timespans_value is not None
        else True,
        show_logs=show_logs_value if show_logs_value is not None else True,
        show_notes=show_notes_value if show_notes_value is not None else True,
        show_entries=show_entries_value if show_entries_value is not None else True,
        limit_note_lines=limit_note_lines_value,
        include_deleted=include_deleted_value
        if include_deleted_value is not None
        else False,
        time_audit_meta_color=time_audit_meta_color_value
        if time_audit_meta_color_value is not None
        else TIME_AUDIT_META_COLOR,
        log_meta_color=log_meta_color_value
        if log_meta_color_value is not None
        else LOG_META_COLOR,
        note_meta_color=note_meta_color_value
        if note_meta_color_value is not None
        else NOTE_META_COLOR,
    )

    # Reset header state
    if no_header:
        set_show_header(True)
