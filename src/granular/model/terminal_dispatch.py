# SPDX-License-Identifier: MIT

from enum import Enum
from typing import NotRequired, Optional, TypedDict


class TerminalDispatchPersistence(TypedDict):
    view_type: "TerminalView"
    view_params: "TerminalViewParams"


class TerminalView(Enum):
    # List views
    TASKS = "tasks"
    TIME_AUDITS = "time_audits"
    EVENTS = "events"
    TIMESPANS = "timespans"
    LOGS = "logs"
    NOTES = "notes"
    CONTEXTS = "contexts"
    PROJECTS = "projects"
    TAGS = "tags"
    TRACKERS = "trackers"
    ENTRIES = "entries"

    # Single entity views
    TASK = "task"
    TIME_AUDIT = "time_audit"
    TIME_AUDIT_ACTIVE = "time_audit_active"
    EVENT = "event"
    TIMESPAN = "timespan"
    LOG = "log"
    NOTE = "note"
    TRACKER = "tracker"

    # Calendar views
    CAL_DAY = "cal_day"
    CAL_WEEK = "cal_week"
    CAL_DAYS = "cal_days"
    CAL_MONTH = "cal_month"
    CAL_QUARTER = "cal_quarter"
    AGENDA = "agenda"

    # Special views
    GANTT = "gantt"
    STORY = "story"
    TRACKER_TODAY = "tracker_today"
    TRACKER_HEATMAP = "tracker_heatmap"
    TASKS_HEATMAP = "tasks_heatmap"
    TRACKER_SUMMARY = "tracker_summary"

    # Custom loader views
    CUSTOM_LOADER = "custom_loader"


class TerminalViewParams(TypedDict):
    pass


# List view parameters


class TasksParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    scheduled: NotRequired[Optional[str]]
    due: NotRequired[Optional[str]]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    columns: NotRequired[Optional[list[str]]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class TimeAuditsParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    task_ids: NotRequired[Optional[list[int]]]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class EventsParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class TimespansParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class LogsParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    reference_type: NotRequired[Optional[str]]
    reference_id: NotRequired[Optional[int]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class NotesParams(TerminalViewParams):
    include_deleted: NotRequired[bool]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    reference_type: NotRequired[Optional[str]]
    reference_id: NotRequired[Optional[int]]
    no_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


class ContextsParams(TerminalViewParams):
    pass


class ProjectsParams(TerminalViewParams):
    pass


class TagsParams(TerminalViewParams):
    pass


class TrackersParams(TerminalViewParams):
    show_archived: NotRequired[bool]
    include_deleted: NotRequired[bool]
    no_color: NotRequired[bool]


class EntriesParams(TerminalViewParams):
    tracker_id: int
    days: NotRequired[int]
    include_deleted: NotRequired[bool]
    no_color: NotRequired[bool]


# Single entity view parameters


class TaskParams(TerminalViewParams):
    task_id: int


class TimeAuditParams(TerminalViewParams):
    time_audit_id: int


class TimeAuditActiveParams(TerminalViewParams):
    pass


class EventParams(TerminalViewParams):
    event_id: int


class TimespanParams(TerminalViewParams):
    timespan_id: int


class LogParams(TerminalViewParams):
    log_id: int


class NoteParams(TerminalViewParams):
    note_id: int


class TrackerParams(TerminalViewParams):
    tracker_id: int


# Calendar view parameters


class CalDayParams(TerminalViewParams):
    date: NotRequired[Optional[str]]
    granularity: NotRequired[int]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    show_trackers: NotRequired[bool]
    project: NotRequired[Optional[str]]
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]


class CalWeekParams(TerminalViewParams):
    start_date: NotRequired[Optional[str]]
    num_days: NotRequired[int]
    day_width: NotRequired[int]
    granularity: NotRequired[int]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    project: NotRequired[Optional[str]]
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]


class CalDaysParams(TerminalViewParams):
    start_date: NotRequired[Optional[str]]
    num_days: NotRequired[int]
    day_width: NotRequired[int]
    granularity: NotRequired[int]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    show_trackers: NotRequired[bool]
    project: NotRequired[Optional[str]]
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]


class CalMonthParams(TerminalViewParams):
    date: NotRequired[Optional[str]]
    cell_width: NotRequired[int]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_all_day_events: NotRequired[bool]
    show_non_all_day_events: NotRequired[bool]
    project: NotRequired[Optional[str]]


class CalQuarterParams(TerminalViewParams):
    date: NotRequired[Optional[str]]
    cell_width: NotRequired[int]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_all_day_events: NotRequired[bool]
    show_non_all_day_events: NotRequired[bool]
    project: NotRequired[Optional[str]]


class AgendaParams(TerminalViewParams):
    num_days: NotRequired[int]
    start: NotRequired[Optional[str]]
    only_active_days: NotRequired[bool]
    include_deleted: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    show_events: NotRequired[bool]
    show_timespans: NotRequired[bool]
    show_logs: NotRequired[bool]
    show_notes: NotRequired[bool]
    limit_note_lines: NotRequired[Optional[int]]
    project: NotRequired[Optional[str]]
    time_audit_meta_color: NotRequired[Optional[str]]
    log_meta_color: NotRequired[Optional[str]]
    note_meta_color: NotRequired[Optional[str]]


# Special view parameters


class GanttParams(TerminalViewParams):
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]
    granularity: NotRequired[str]
    include_deleted: NotRequired[bool]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[str]]
    show_tasks: NotRequired[bool]
    show_timespans: NotRequired[bool]
    show_events: NotRequired[bool]
    show_trackers: NotRequired[bool]
    left_width: NotRequired[int]


class StoryParams(TerminalViewParams):
    task: NotRequired[Optional[list[int]]]
    time_audit: NotRequired[Optional[list[int]]]
    event: NotRequired[Optional[list[int]]]
    project: NotRequired[Optional[list[str]]]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]
    only_active_days: NotRequired[bool]
    show_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    show_events: NotRequired[bool]
    show_timespans: NotRequired[bool]
    show_logs: NotRequired[bool]
    show_notes: NotRequired[bool]
    show_entries: NotRequired[bool]
    limit_note_lines: NotRequired[Optional[int]]
    include_deleted: NotRequired[bool]
    time_audit_meta_color: NotRequired[Optional[str]]
    log_meta_color: NotRequired[Optional[str]]
    note_meta_color: NotRequired[Optional[str]]


class TrackerTodayParams(TerminalViewParams):
    no_color: NotRequired[bool]


class TrackerHeatmapParams(TerminalViewParams):
    days: NotRequired[int]
    left_width: NotRequired[int]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]


class TasksHeatmapParams(TerminalViewParams):
    days: NotRequired[int]
    left_width: NotRequired[int]
    tag: NotRequired[Optional[list[str]]]
    tag_regex: NotRequired[Optional[list[str]]]
    no_tag: NotRequired[Optional[list[str]]]
    no_tag_regex: NotRequired[Optional[list[str]]]
    project: NotRequired[Optional[list[str]]]


class TrackerSummaryParams(TerminalViewParams):
    tracker_id: int
    days: NotRequired[int]
    start: NotRequired[Optional[str]]
    end: NotRequired[Optional[str]]


# Custom loader view parameters


class CustomLoaderParams(TerminalViewParams):
    compound_view: "CompoundView"


# Import at end to avoid circular import
from granular.model.custom_view import CompoundView  # noqa: E402
