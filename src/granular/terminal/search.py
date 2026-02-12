# SPDX-License-Identifier: MIT

from typing import Annotated, cast

import typer

from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.repository.context import CONTEXT_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.service.search import search_entities
from granular.view.view.views.search import search_results_view


def search(
    query: Annotated[str, typer.Argument(help="Search query string")],
    search_in_description: Annotated[
        bool,
        typer.Option(
            "--search-in-description",
            "-d",
            help="Search in description/title/text fields",
        ),
    ] = True,
    search_in_tags: Annotated[
        bool,
        typer.Option("--search-in-tags", "-t", help="Search in tags"),
    ] = False,
    search_in_project: Annotated[
        bool,
        typer.Option("--search-in-project", "-p", help="Search in project field"),
    ] = False,
    tasks: Annotated[
        bool,
        typer.Option("--tasks/--no-tasks", help="Include tasks in search"),
    ] = True,
    time_audits: Annotated[
        bool,
        typer.Option(
            "--time-audits/--no-time-audits", help="Include time audits in search"
        ),
    ] = True,
    events: Annotated[
        bool,
        typer.Option("--events/--no-events", help="Include events in search"),
    ] = True,
    timespans: Annotated[
        bool,
        typer.Option("--timespans/--no-timespans", help="Include timespans in search"),
    ] = True,
    notes: Annotated[
        bool,
        typer.Option("--notes/--no-notes", help="Include notes in search"),
    ] = True,
    logs: Annotated[
        bool,
        typer.Option("--logs/--no-logs", help="Include logs in search"),
    ] = True,
    include_deleted: Annotated[
        bool,
        typer.Option("--include-deleted", "-i", help="Include deleted entities"),
    ] = False,
    no_wrap: Annotated[
        bool,
        typer.Option("--no-wrap", help="Disable text wrapping in table columns"),
    ] = False,
) -> None:
    # Get active context
    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Retrieve entities based on flags
    tasks_list: list[Task] = []
    time_audits_list: list[TimeAudit] = []
    events_list: list[Event] = []
    timespans_list: list[Timespan] = []
    notes_list: list[Note] = []
    logs_list: list[Log] = []

    if tasks:
        tasks_list = TASK_REPO.get_all_tasks()
        # Filter out deleted tasks by default
        if not include_deleted:
            tasks_list = [task for task in tasks_list if task["deleted"] is None]

    if time_audits:
        time_audits_list = TIME_AUDIT_REPO.get_all_time_audits()
        # Filter out deleted time audits by default
        if not include_deleted:
            time_audits_list = [
                time_audit
                for time_audit in time_audits_list
                if time_audit["deleted"] is None
            ]

    if events:
        events_list = EVENT_REPO.get_all_events()
        # Filter out deleted events by default
        if not include_deleted:
            events_list = [event for event in events_list if event["deleted"] is None]

    if timespans:
        timespans_list = TIMESPAN_REPO.get_all_timespans()
        # Filter out deleted timespans by default
        if not include_deleted:
            timespans_list = [
                timespan for timespan in timespans_list if timespan["deleted"] is None
            ]

    if notes:
        notes_list = NOTE_REPO.get_all_notes()
        # Filter out deleted notes by default
        if not include_deleted:
            notes_list = [note for note in notes_list if note["deleted"] is None]

    if logs:
        logs_list = LOG_REPO.get_all_logs()
        # Filter out deleted logs by default
        if not include_deleted:
            logs_list = [log for log in logs_list if log["deleted"] is None]

    # Perform search
    results = search_entities(
        query=query,
        tasks=tasks_list,
        time_audits=time_audits_list,
        events=events_list,
        timespans=timespans_list,
        notes=notes_list,
        logs=logs_list,
        search_in_description=search_in_description,
        search_in_tags=search_in_tags,
        search_in_project=search_in_project,
    )

    # Display results
    search_results_view(active_context_name, "search", results, no_wrap=no_wrap)
