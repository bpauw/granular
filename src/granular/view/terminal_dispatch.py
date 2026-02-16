# SPDX-License-Identifier: MIT

from typing import cast

from granular.model.terminal_dispatch import (
    AgendaParams,
    CalDayParams,
    CalDaysParams,
    CalMonthParams,
    CalQuarterParams,
    CalWeekParams,
    CustomLoaderParams,
    EntriesParams,
    EventParams,
    EventsParams,
    GanttParams,
    LogParams,
    LogsParams,
    NoteParams,
    NotesParams,
    StoryParams,
    TaskParams,
    TasksHeatmapParams,
    TasksParams,
    TerminalView,
    TerminalViewParams,
    TimeAuditParams,
    TimeAuditsParams,
    TimespanParams,
    TimespansParams,
    TrackerHeatmapParams,
    TrackerParams,
    TrackersParams,
    TrackerSummaryParams,
    TrackerTodayParams,
)
from granular.repository.dispatch import DISPATCH_REPO
from granular.time import datetime_from_local_date_str_optional
from granular.view.custom.compound import compound_view_command

# Single-entity views that should NOT be cached
SINGLE_ENTITY_VIEWS = {
    TerminalView.TASK,
    TerminalView.TIME_AUDIT,
    TerminalView.EVENT,
    TerminalView.TIMESPAN,
    TerminalView.LOG,
    TerminalView.NOTE,
    TerminalView.TRACKER,
}


def dispatch(view_type: TerminalView, view_params: TerminalViewParams) -> None:
    """Cache the dispatch call and execute the terminal view command."""
    # Import here to avoid circular imports
    from granular.terminal import view as terminal_view

    # Cache non-single-entity views
    if view_type not in SINGLE_ENTITY_VIEWS:
        update_cached_dispatch(view_type, view_params)

    # Dispatch to terminal view commands
    match view_type:
        # List views
        case TerminalView.TASKS:
            params = cast(TasksParams, view_params)
            terminal_view.tasks(
                include_deleted=params.get("include_deleted", False),
                scheduled=datetime_from_local_date_str_optional(
                    params.get("scheduled")
                ),
                due=datetime_from_local_date_str_optional(params.get("due")),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.TIME_AUDITS:
            params = cast(TimeAuditsParams, view_params)
            terminal_view.time_audits(
                include_deleted=params.get("include_deleted", False),
                task_id=params.get("task_id"),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.EVENTS:
            params = cast(EventsParams, view_params)
            terminal_view.events(
                include_deleted=params.get("include_deleted", False),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.TIMESPANS:
            params = cast(TimespansParams, view_params)
            terminal_view.timespans(
                include_deleted=params.get("include_deleted", False),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.LOGS:
            params = cast(LogsParams, view_params)
            terminal_view.logs(
                include_deleted=params.get("include_deleted", False),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                reference_type=params.get("reference_type"),
                reference_id=params.get("reference_id"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.NOTES:
            params = cast(NotesParams, view_params)
            terminal_view.notes(
                include_deleted=params.get("include_deleted", False),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
                reference_type=params.get("reference_type"),
                reference_id=params.get("reference_id"),
                no_color=params.get("no_color", False),
                no_wrap=params.get("no_wrap", False),
            )
        case TerminalView.CONTEXTS:
            terminal_view.contexts()
        case TerminalView.PROJECTS:
            terminal_view.projects()
        case TerminalView.TAGS:
            terminal_view.tags()
        case TerminalView.TRACKERS:
            params = cast(TrackersParams, view_params)
            terminal_view.trackers(
                show_archived=params.get("show_archived", False),
                include_deleted=params.get("include_deleted", False),
                no_color=params.get("no_color", False),
            )
        case TerminalView.ENTRIES:
            params = cast(EntriesParams, view_params)
            terminal_view.entries(
                tracker_id=params["tracker_id"],
                days=params.get("days", 14),
                include_deleted=params.get("include_deleted", False),
                no_color=params.get("no_color", False),
            )

        # Single entity views
        case TerminalView.TASK:
            params = cast(TaskParams, view_params)
            terminal_view.task(task_id=params["task_id"])
        case TerminalView.TIME_AUDIT:
            params = cast(TimeAuditParams, view_params)
            terminal_view.time_audit(time_audit_id=params["time_audit_id"])
        case TerminalView.TIME_AUDIT_ACTIVE:
            terminal_view.time_audit_active()
        case TerminalView.EVENT:
            params = cast(EventParams, view_params)
            terminal_view.event(event_id=params["event_id"])
        case TerminalView.TIMESPAN:
            params = cast(TimespanParams, view_params)
            terminal_view.timespan(timespan_id=params["timespan_id"])
        case TerminalView.LOG:
            params = cast(LogParams, view_params)
            terminal_view.log(log_id=params["log_id"])
        case TerminalView.NOTE:
            params = cast(NoteParams, view_params)
            terminal_view.note(note_id=params["note_id"])
        case TerminalView.TRACKER:
            params = cast(TrackerParams, view_params)
            terminal_view.tracker(tracker_id=params["tracker_id"])

        # Calendar views
        case TerminalView.CAL_DAY:
            params = cast(CalDayParams, view_params)
            terminal_view.cal_day(
                date=datetime_from_local_date_str_optional(params.get("date")),
                granularity=params.get("granularity", 60),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                show_time_audits=params.get("show_time_audits", True),
                show_trackers=params.get("show_trackers", False),
                project=params.get("project"),
                start=params.get("start"),
                end=params.get("end"),
            )
        case TerminalView.CAL_WEEK:
            params = cast(CalWeekParams, view_params)
            terminal_view.cal_week(
                start_date=datetime_from_local_date_str_optional(
                    params.get("start_date")
                ),
                num_days=params.get("num_days", 7),
                day_width=params.get("day_width", 30),
                granularity=params.get("granularity", 60),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                project=params.get("project"),
                start=params.get("start"),
                end=params.get("end"),
            )
        case TerminalView.CAL_DAYS:
            params = cast(CalDaysParams, view_params)
            terminal_view.cal_days(
                start_date=datetime_from_local_date_str_optional(
                    params.get("start_date")
                ),
                num_days=params.get("num_days", 7),
                day_width=params.get("day_width", 30),
                granularity=params.get("granularity", 60),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                show_time_audits=params.get("show_time_audits", True),
                show_trackers=params.get("show_trackers", False),
                project=params.get("project"),
                start=params.get("start"),
                end=params.get("end"),
            )
        case TerminalView.CAL_MONTH:
            params = cast(CalMonthParams, view_params)
            terminal_view.cal_month(
                date=datetime_from_local_date_str_optional(params.get("date")),
                cell_width=params.get("cell_width", 20),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                show_all_day_events=params.get("show_all_day_events", True),
                show_non_all_day_events=params.get("show_non_all_day_events", True),
                project=params.get("project"),
            )
        case TerminalView.CAL_QUARTER:
            params = cast(CalQuarterParams, view_params)
            terminal_view.cal_quarter(
                date=datetime_from_local_date_str_optional(params.get("date")),
                cell_width=params.get("cell_width", 20),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                show_all_day_events=params.get("show_all_day_events", True),
                show_non_all_day_events=params.get("show_non_all_day_events", False),
                project=params.get("project"),
            )
        case TerminalView.AGENDA:
            params = cast(AgendaParams, view_params)
            terminal_view.cal_agenda_days(
                num_days=params.get("num_days", 7),
                start=datetime_from_local_date_str_optional(params.get("start")),
                only_active_days=params.get("only_active_days", False),
                include_deleted=params.get("include_deleted", False),
                show_scheduled_tasks=params.get("show_scheduled_tasks", True),
                show_due_tasks=params.get("show_due_tasks", True),
                show_time_audits=params.get("show_time_audits", False),
                show_events=params.get("show_events", True),
                show_timespans=params.get("show_timespans", True),
                show_logs=params.get("show_logs", False),
                show_notes=params.get("show_notes", False),
                limit_note_lines=params.get("limit_note_lines"),
                project=params.get("project"),
                time_audit_meta_color=params.get("time_audit_meta_color"),
                log_meta_color=params.get("log_meta_color"),
                note_meta_color=params.get("note_meta_color"),
            )

        # Special views
        case TerminalView.GANTT:
            params = cast(GanttParams, view_params)
            terminal_view.gantt(
                start=datetime_from_local_date_str_optional(params.get("start")),
                end=datetime_from_local_date_str_optional(params.get("end")),
                granularity=params.get("granularity", "day"),
                include_deleted=params.get("include_deleted", False),
                tag=params.get("tag"),
                tag_regex=params.get("tag_regex"),
                no_tag=params.get("no_tag"),
                no_tag_regex=params.get("no_tag_regex"),
                project=params.get("project"),
                show_tasks=params.get("show_tasks", False),
                show_timespans=params.get("show_timespans", True),
                show_events=params.get("show_events", True),
                show_trackers=params.get("show_trackers", False),
                left_width=params.get("left_width", 40),
            )
        case TerminalView.STORY:
            params = cast(StoryParams, view_params)
            terminal_view.story(
                task=params.get("task"),
                time_audit=params.get("time_audit"),
                event=params.get("event"),
                project=params.get("project"),
                tag=params.get("tag"),
                start=datetime_from_local_date_str_optional(params.get("start")),
                end=datetime_from_local_date_str_optional(params.get("end")),
                only_active_days=params.get("only_active_days", True),
                show_tasks=params.get("show_tasks", True),
                show_time_audits=params.get("show_time_audits", True),
                show_events=params.get("show_events", True),
                show_timespans=params.get("show_timespans", True),
                show_logs=params.get("show_logs", True),
                show_notes=params.get("show_notes", True),
                show_entries=params.get("show_entries", True),
                limit_note_lines=params.get("limit_note_lines"),
                include_deleted=params.get("include_deleted", False),
                time_audit_meta_color=params.get("time_audit_meta_color"),
                log_meta_color=params.get("log_meta_color"),
                note_meta_color=params.get("note_meta_color"),
            )
        case TerminalView.TRACKER_TODAY:
            params = cast(TrackerTodayParams, view_params)
            terminal_view.tracker_today(
                no_color=params.get("no_color", False),
            )
        case TerminalView.TRACKER_HEATMAP:
            params = cast(TrackerHeatmapParams, view_params)
            terminal_view.tracker_heatmap(
                days=params.get("days", 14),
                left_width=params.get("left_width", 30),
                tag=params.get("tag"),
            )
        case TerminalView.TASKS_HEATMAP:
            params = cast(TasksHeatmapParams, view_params)
            terminal_view.tasks_heatmap(
                days=params.get("days", 14),
                left_width=params.get("left_width", 30),
                tag=params.get("tag"),
                no_tag=params.get("no_tag"),
                project=params.get("project"),
            )
        case TerminalView.TRACKER_SUMMARY:
            params = cast(TrackerSummaryParams, view_params)
            terminal_view.tracker_summary(
                tracker_id=params["tracker_id"],
                days=params.get("days", 14),
                start=datetime_from_local_date_str_optional(params.get("start")),
                end=datetime_from_local_date_str_optional(params.get("end")),
            )

        # Custom loader views
        case TerminalView.CUSTOM_LOADER:
            params = cast(CustomLoaderParams, view_params)
            compound_view_command(params["compound_view"])


def update_cached_dispatch(
    view_type: TerminalView, view_params: TerminalViewParams
) -> None:
    DISPATCH_REPO.save_dispatch(view_type, view_params)


def show_cached_dispatch() -> None:
    dispatch_data = DISPATCH_REPO.get_dispatch()
    if dispatch_data is not None:
        view_type, view_params = dispatch_data
        dispatch(view_type, view_params)
