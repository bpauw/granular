# SPDX-License-Identifier: MIT

from typing import Literal, Optional, TypedDict, Union

from granular.model.filter import Filters
from granular.model.terminal_dispatch import TerminalViewParams

ViewType = Literal[
    "task",
    "time_audit",
    "event",
    "timespan",
    "log",
    "markdown",
    "header",
    "space",
    "agenda",
    "gantt",
    "tasks_heatmap",
    "story",
]


class Views(TypedDict):
    custom_views: list["CompoundView"]


class TaskSubView(TypedDict):
    view_type: Literal["task"]
    columns: list[str]
    sort: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]


class TimeAuditSubView(TypedDict):
    view_type: Literal["time_audit"]
    columns: list[str]
    sort: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]


class EventSubView(TypedDict):
    view_type: Literal["event"]
    columns: list[str]
    sort: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]


class TimespanSubView(TypedDict):
    view_type: Literal["timespan"]
    columns: list[str]
    sort: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]


class LogSubView(TypedDict):
    view_type: Literal["log"]
    columns: list[str]
    sort: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]


class MarkdownSubView(TypedDict):
    view_type: Literal["markdown"]
    markdown: str


class HeaderSubView(TypedDict):
    view_type: Literal["header"]


class SpaceSubView(TypedDict):
    view_type: Literal["space"]


class AgendaSubView(TypedDict):
    view_type: Literal["agenda"]
    num_days: Optional[int]
    start: Optional[str]
    only_active_days: Optional[bool]
    show_scheduled_tasks: Optional[bool]
    show_due_tasks: Optional[bool]
    show_events: Optional[bool]
    show_timespans: Optional[bool]
    show_logs: Optional[bool]
    show_notes: Optional[bool]
    show_time_audits: Optional[bool]
    limit_note_lines: Optional[int]
    filter: Optional["Filters"]
    no_header: Optional[bool]
    time_audit_meta_color: Optional[str]
    log_meta_color: Optional[str]
    note_meta_color: Optional[str]


class GanttSubView(TypedDict):
    view_type: Literal["gantt"]
    start: Optional[str]
    end: Optional[str]
    granularity: Optional[str]
    show_tasks: Optional[bool]
    show_timespans: Optional[bool]
    show_events: Optional[bool]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    left_column_width: Optional[int]
    no_header: Optional[bool]


class TasksHeatmapSubView(TypedDict):
    view_type: Literal["tasks_heatmap"]
    days: Optional[int]
    start: Optional[str]
    end: Optional[str]
    granularity: Optional[str]
    left_column_width: Optional[int]
    projects: Optional[list[str]]
    tags: Optional[list[str]]
    filter: Optional["Filters"]
    include_deleted: Optional[bool]
    no_header: Optional[bool]


class StorySubView(TypedDict):
    """
    Configuration for story view which displays all entities related to anchor entities.

    The story view focuses on relationships - pulling in all nested data to tell
    the complete "story" of an entity (task, project, tag, time audit, or event).
    """

    view_type: Literal["story"]
    # Anchor options - at least one required, multiple allowed with AND logic
    task: Optional[Union[int, list[int]]]
    time_audit: Optional[Union[int, list[int]]]
    event: Optional[Union[int, list[int]]]
    project: Optional[Union[str, list[str]]]
    tag: Optional[Union[str, list[str]]]
    # Date range options
    start: Optional[str]
    end: Optional[str]
    only_active_days: Optional[bool]
    # Display options (all default to True)
    show_tasks: Optional[bool]
    show_time_audits: Optional[bool]
    show_events: Optional[bool]
    show_timespans: Optional[bool]
    show_logs: Optional[bool]
    show_notes: Optional[bool]
    show_entries: Optional[bool]
    limit_note_lines: Optional[int]
    # Other options
    include_deleted: Optional[bool]
    no_header: Optional[bool]
    no_color: Optional[bool]
    no_wrap: Optional[bool]
    # Color options
    time_audit_meta_color: Optional[str]
    log_meta_color: Optional[str]
    note_meta_color: Optional[str]


SubView = (
    TaskSubView
    | TimeAuditSubView
    | EventSubView
    | TimespanSubView
    | LogSubView
    | MarkdownSubView
    | HeaderSubView
    | SpaceSubView
    | AgendaSubView
    | GanttSubView
    | TasksHeatmapSubView
    | StorySubView
)


class CompoundView(TerminalViewParams):
    name: str
    views: list[SubView]


class View(TypedDict):
    name: str
    columns: list[str]
    sort: Optional[list[str]]
    filter: "Filters"
    include_deleted: Optional[bool]
