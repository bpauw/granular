from enum import Enum
from typing import NotRequired, TypedDict

import pendulum

from granular.model.context import Context
from granular.model.entry import Entry
from granular.model.event import Event
from granular.model.granularity_type import GranularityType
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.model.tracker import Tracker
from granular.service.search import SearchResult


class ViewDispatchPersistence(TypedDict):
    view_type: View
    view_params: ViewParams


class View(Enum):
    CALENDAR_DAY = 0
    CALENDAR_DAYS = 1
    CALENDAR_WEEK = 2
    CALENDAR_MONTH = 3
    CALENDAR_QUARTER = 4
    CALENDAR_AGENDA_DAYS = 5

    CONTEXT = 6
    CONTEXTS = 7

    ENTRY = 8
    ENTRIES = 9

    EVENT = 10
    EVENTS = 11

    GANTT = 12
    TASKS_HEATMAP = 13

    LOG = 14
    LOGS = 15

    NOTE = 16
    NOTES = 17

    PROJECT = 18
    PROJECTS = 19

    SEARCH_RESULTS = 20

    TAG = 21
    TAGS = 22

    TASK = 23
    TASKS = 24

    TIME_AUDIT = 25
    TIME_AUDITS = 26
    ACTIVE_TIME_AUDIT = 27

    TIMESPAN = 28
    TIMESPANS = 29

    TRACKER = 30
    TRACKERS = 31
    TRACKER_TODAY = 32
    TRACKER_SUMMARY = 33

    CUSTOM_LOADER = 34


class ViewParams(TypedDict):
    pass


# calendar.calendar_day_view
class CalendarDayView(ViewParams):
    active_context: str
    report_name: str
    time_audits: list[TimeAudit]
    events: list[Event]
    tasks: list[Task]
    date: NotRequired[pendulum.DateTime]
    granularity: NotRequired[int]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    start_hour: NotRequired[int]
    start_minute: NotRequired[int]
    end_hour: NotRequired[int]
    end_minute: NotRequired[int]
    trackers: NotRequired[list[Tracker]]
    entries: NotRequired[list[Entry]]
    show_trackers: NotRequired[bool]


# calendar.calendar_days_view
class CalendarDaysView(ViewParams):
    active_context: str
    report_name: str
    time_audits: list[TimeAudit]
    events: list[Event]
    tasks: list[Task]
    num_days: NotRequired[int]
    day_width: NotRequired[int]
    granularity: NotRequired[int]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    start_hour: NotRequired[int]
    start_minute: NotRequired[int]
    end_hour: NotRequired[int]
    end_minute: NotRequired[int]
    trackers: NotRequired[list[Tracker]]
    entries: NotRequired[list[Entry]]
    show_trackers: NotRequired[bool]


# calendar.calendar_week_view
class CalendarWeekView(ViewParams):
    active_context: str
    report_name: str
    time_audits: list[TimeAudit]
    events: list[Event]
    tasks: list[Task]
    start_date: NotRequired[pendulum.DateTime]
    num_days: NotRequired[int]
    day_width: NotRequired[int]
    granularity: NotRequired[int]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    start_hour: NotRequired[int]
    start_minute: NotRequired[int]
    end_hour: NotRequired[int]
    end_minute: NotRequired[int]


# calendar.calendar_month_view
class CalendarMonthView(ViewParams):
    active_context: str
    report_name: str
    tasks: list[Task]
    events: list[Event]
    date: NotRequired[pendulum.DateTime]
    cell_width: NotRequired[int]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_all_day_events: NotRequired[bool]
    show_non_all_day_events: NotRequired[bool]


# calendar.calendar_quarter_view
class CalendarQuarterView(ViewParams):
    active_context: str
    report_name: str
    tasks: list[Task]
    events: list[Event]
    date: NotRequired[pendulum.DateTime]
    cell_width: NotRequired[int]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_all_day_events: NotRequired[bool]
    show_non_all_day_events: NotRequired[bool]


# calendar.calendar_agenda_days_view
class CalendarAgendaDaysView(ViewParams):
    active_context: str
    report_name: str
    time_audits: list[TimeAudit]
    events: list[Event]
    tasks: list[Task]
    timespans: list[Timespan]
    logs: list[Log]
    notes: list[Note]
    num_days: NotRequired[int]
    start_date: NotRequired[pendulum.DateTime]
    only_active_days: NotRequired[bool]
    show_scheduled_tasks: NotRequired[bool]
    show_due_tasks: NotRequired[bool]
    show_events: NotRequired[bool]
    show_timespans: NotRequired[bool]
    show_logs: NotRequired[bool]
    show_notes: NotRequired[bool]
    show_time_audits: NotRequired[bool]
    limit_note_lines: NotRequired[int]
    time_audit_meta_color: NotRequired[str]
    log_meta_color: NotRequired[str]
    note_meta_color: NotRequired[str]


# context.single_context_view
class ContextView(ViewParams):
    active_context: str
    context: Context


# context.contexts_view
class ContextsView(ViewParams):
    active_context: str
    contexts: list[Context]


# entry.single_entry_view
class EntryView(ViewParams):
    active_context: str
    entry: Entry
    tracker: Tracker


# entry.entries_view
class EntriesView(ViewParams):
    active_context: str
    tracker: Tracker
    entries: list[Entry]
    columns: NotRequired[list[str]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# event.single_event_view
class EventView(ViewParams):
    active_context: str
    event: Event


# event.events_view
class EventsView(ViewParams):
    active_context: str
    report_name: str
    events: list[Event]
    columns: NotRequired[list[str]]
    notes: NotRequired[list[Note]]
    logs: NotRequired[list[Log]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# gantt.gantt_view
class GanttView(ViewParams):
    active_context: str
    report_name: str
    timespans: list[Timespan]
    events: NotRequired[list[Event]]
    tasks: NotRequired[list[Task]]
    trackers: NotRequired[list[Tracker]]
    entries: NotRequired[list[Entry]]
    start: NotRequired[pendulum.DateTime]
    end: NotRequired[pendulum.DateTime]
    granularity: NotRequired[GranularityType]
    show_tasks: NotRequired[bool]
    show_timespans: NotRequired[bool]
    show_events: NotRequired[bool]
    show_trackers: NotRequired[bool]
    left_column_width: NotRequired[int]


# gantt.tasks_heatmap_view
class TasksHeatmapView(ViewParams):
    active_context: str
    report_name: str
    tasks: list[Task]
    time_audits: list[TimeAudit]
    start: NotRequired[pendulum.DateTime]
    end: NotRequired[pendulum.DateTime]
    granularity: NotRequired[GranularityType]
    left_column_width: NotRequired[int]
    projects: NotRequired[list[str]]
    tags: NotRequired[list[str]]


# log.logs_view
class LogsView(ViewParams):
    active_context: str
    report_name: str
    logs: list[Log]
    columns: NotRequired[list[str]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# log.single_log_report
class LogView(ViewParams):
    active_context: str
    log: Log


# note.notes_report
class NotesView(ViewParams):
    active_context: str
    report_name: str
    notes: list[Note]
    columns: NotRequired[list[str]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# note.single_note_report
class NoteView(ViewParams):
    active_context: str
    note: Note


# project.projects_view
class ProjectsView(ViewParams):
    active_context: str
    projects: list[str]


# search.search_results_view
class SearchResultsView(ViewParams):
    active_context: str
    report_name: str
    results: list[SearchResult]
    no_wrap: NotRequired[bool]


# tag.tags_report
class TagsView(ViewParams):
    active_context: str
    tags: list[str]


# task.tasks_view
class TasksView(ViewParams):
    active_context: str
    report_name: str
    tasks: list[Task]
    columns: NotRequired[list[str]]
    time_audits: NotRequired[list[TimeAudit]]
    notes: NotRequired[list[Note]]
    logs: NotRequired[list[Log]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# task.single_task_view
class TaskView(ViewParams):
    active_context: str
    task: Task
    time_audits: NotRequired[list[TimeAudit]]


# time_audit.time_audits_report
class TimeAuditsView(ViewParams):
    active_context: str
    report_name: str
    time_audits: list[TimeAudit]
    columns: NotRequired[list[str]]
    notes: NotRequired[list[Note]]
    logs: NotRequired[list[Log]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# time_audit.single_time_audit_report
class TimeAuditView(ViewParams):
    active_context: str
    time_audit: TimeAudit
    title: NotRequired[str]
    show_header: NotRequired[bool]


# time_audit.active_time_audit_report
class ActiveTimeAuditView(ViewParams):
    active_context: str
    time_audit: NotRequired[TimeAudit]
    show_header: NotRequired[bool]


# timespan.timespans_view
class TimespansView(ViewParams):
    active_context: str
    report_name: str
    timespans: list[Timespan]
    columns: NotRequired[list[str]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# timespan.single_timespan_view
class TimespanView(ViewParams):
    active_context: str
    timespan: Timespan


# tracker.trackers_view
class TrackersView(ViewParams):
    active_context: str
    report_name: str
    trackers: list[Tracker]
    columns: NotRequired[list[str]]
    use_color: NotRequired[bool]
    no_wrap: NotRequired[bool]


# tracker.single_tracker_view
class TrackerView(ViewParams):
    active_context: str
    tracker: Tracker


# tracker.tracker_today_view
class TrackerTodayView(ViewParams):
    active_context: str
    trackers: list[Tracker]
    entries: list[Entry]


# tracker.tracker_summary_view
class TrackerSummaryView(ViewParams):
    active_context: str
    tracker: Tracker
    entries: list[Entry]
    start_date: NotRequired[pendulum.Date]
    end_date: NotRequired[pendulum.Date]
    days: NotRequired[int]
