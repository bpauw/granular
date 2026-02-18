# SPDX-License-Identifier: MIT

"""
Story view that displays all entities related to specific anchor entities.

Unlike agenda which focuses on a chronological date range, story focuses on
relationships - pulling in all nested data to tell the complete "story" of
an entity (project, tag, task, time audit, or event).
"""

from typing import Optional

import pendulum
from rich.console import Console

from granular.model.entity_id import EntityId
from granular.color import (
    LOG_META_COLOR,
    NOTE_META_COLOR,
    TIME_AUDIT_META_COLOR,
)
from granular.model.entry import Entry
from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan
from granular.model.tracker import Tracker
from granular.query.filter import tag_matches_regex
from granular.repository.id_map import ID_MAP_REPO
from granular.view.view.views.agenda_core import render_agenda_day
from granular.view.view.views.header import header


def story_view(
    active_context: str,
    report_name: str,
    tasks: list[Task],
    time_audits: list[TimeAudit],
    events: list[Event],
    timespans: list[Timespan],
    logs: list[Log],
    notes: list[Note],
    entries: Optional[list[Entry]] = None,
    trackers: Optional[list[Tracker]] = None,
    task_ids: Optional[list[EntityId]] = None,
    time_audit_ids: Optional[list[EntityId]] = None,
    event_ids: Optional[list[EntityId]] = None,
    projects: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    start_date: Optional[pendulum.DateTime] = None,
    end_date: Optional[pendulum.DateTime] = None,
    only_active_days: bool = True,
    show_tasks: bool = True,
    show_time_audits: bool = True,
    show_events: bool = True,
    show_timespans: bool = True,
    show_logs: bool = True,
    show_notes: bool = True,
    show_entries: bool = True,
    limit_note_lines: Optional[int] = None,
    include_deleted: bool = False,
    time_audit_meta_color: str = TIME_AUDIT_META_COLOR,
    log_meta_color: str = LOG_META_COLOR,
    note_meta_color: str = NOTE_META_COLOR,
) -> None:
    """
    Display a story view showing all entities related to anchor entities.

    Args:
        active_context: The name of the active context
        report_name: The name of the report
        tasks: All tasks in the system
        time_audits: All time audits in the system
        events: All events in the system
        timespans: All timespans in the system
        logs: All logs in the system
        notes: All notes in the system
        entries: All tracker entries in the system
        trackers: All trackers in the system
        task_ids: Task IDs to anchor the story on
        time_audit_ids: Time audit IDs to anchor the story on
        event_ids: Event IDs to anchor the story on
        projects: Project names to anchor the story on
        tags: Tag names to anchor the story on
        start_date: Override start date for the story
        end_date: Override end date for the story
        only_active_days: Whether to show only days with activity
        show_tasks: Whether to show tasks
        show_time_audits: Whether to show time audits
        show_events: Whether to show events
        show_timespans: Whether to show timespans
        show_logs: Whether to show logs
        show_notes: Whether to show notes
        show_entries: Whether to show tracker entries
        limit_note_lines: Maximum number of lines per note
        include_deleted: Whether to include deleted entities
        time_audit_meta_color: Color for time audit metadata
        log_meta_color: Color for log metadata
        note_meta_color: Color for note metadata
    """
    console = Console()

    # Collect related entities
    collector = StoryDataCollector(
        tasks=tasks,
        time_audits=time_audits,
        events=events,
        timespans=timespans,
        logs=logs,
        notes=notes,
        entries=entries,
        trackers=trackers,
        include_deleted=include_deleted,
    )

    collected = collector.collect(
        task_ids=task_ids,
        time_audit_ids=time_audit_ids,
        event_ids=event_ids,
        projects=projects,
        tags=tags,
    )

    story_tasks = collected["tasks"] if show_tasks else []
    story_time_audits = collected["time_audits"] if show_time_audits else []
    story_events = collected["events"] if show_events else []
    story_timespans = collected["timespans"] if show_timespans else []
    story_logs = collected["logs"] if show_logs else []
    story_notes = collected["notes"] if show_notes else []
    story_entries = collected["entries"] if show_entries else []

    # Generate header
    story_header = generate_story_header(
        task_ids=task_ids,
        time_audit_ids=time_audit_ids,
        event_ids=event_ids,
        projects=projects,
        tags=tags,
        tasks=tasks,
        time_audits=time_audits,
        events=events,
        num_tasks=len(story_tasks),
        num_time_audits=len(story_time_audits),
        num_logs=len(story_logs),
    )

    header(active_context, story_header)

    # Check if there's any content
    if not any(
        [
            story_tasks,
            story_time_audits,
            story_events,
            story_timespans,
            story_logs,
            story_notes,
            story_entries,
        ]
    ):
        console.print("\nNo related activity found.\n")
        return

    # Calculate date range
    calc_start, calc_end = calculate_date_range(
        story_tasks,
        story_time_audits,
        story_events,
        story_timespans,
        story_logs,
        story_notes,
        story_entries,
    )

    # Use provided dates or calculated dates
    if start_date is not None:
        range_start = start_date.in_tz("local").start_of("day")
    elif calc_start is not None:
        range_start = calc_start.in_tz("local").start_of("day")
    else:
        range_start = pendulum.now("local").start_of("day")

    if end_date is not None:
        range_end = end_date.in_tz("local").start_of("day")
    elif calc_end is not None:
        range_end = calc_end.in_tz("local").start_of("day")
    else:
        range_end = pendulum.now("local").start_of("day")

    # Iterate through each day in the range
    current_date = range_start
    rendered_any_day = False

    while current_date <= range_end:
        rendered = render_agenda_day(
            console,
            current_date,
            story_time_audits,
            story_events,
            story_tasks,
            story_timespans,
            story_logs,
            story_notes,
            entries=story_entries,
            trackers=trackers,
            show_scheduled_tasks=True,
            show_due_tasks=True,
            show_events=show_events,
            show_timespans=show_timespans,
            show_logs=show_logs,
            show_notes=show_notes,
            show_time_audits=show_time_audits,
            show_entries=show_entries,
            limit_note_lines=limit_note_lines,
            time_audit_meta_color=time_audit_meta_color,
            log_meta_color=log_meta_color,
            note_meta_color=note_meta_color,
        )

        if rendered:
            rendered_any_day = True
        elif not only_active_days:
            # If showing all days, render the header even for empty days
            from granular.view.view.views.agenda_core import render_day_header

            render_day_header(console, current_date)

        current_date = current_date.add(days=1)

    if not rendered_any_day and only_active_days:
        console.print("\nNo activity found in date range.\n")
    else:
        console.print()


class StoryDataCollector:
    """
    Collects entities related to anchor entities based on relationship rules.

    Entity Relationship Rules:
    - Task Story: task + its time audits + logs/notes for task and its time audits
    - Time Audit Story: time audit + logs/notes for it
    - Event Story: event + logs/notes for it
    - Project Story: all entities where project = X (exact match)
    - Tag Story: all entities that have the specified tag
    """

    def __init__(
        self,
        tasks: list[Task],
        time_audits: list[TimeAudit],
        events: list[Event],
        timespans: list[Timespan],
        logs: list[Log],
        notes: list[Note],
        entries: Optional[list[Entry]] = None,
        trackers: Optional[list[Tracker]] = None,
        include_deleted: bool = False,
    ):
        self.all_tasks = tasks
        self.all_time_audits = time_audits
        self.all_events = events
        self.all_timespans = timespans
        self.all_logs = logs
        self.all_notes = notes
        self.all_entries = entries or []
        self.all_trackers = trackers or []
        self.include_deleted = include_deleted

        # Filter out deleted items unless include_deleted is True
        if not include_deleted:
            self.all_tasks = [t for t in self.all_tasks if t["deleted"] is None]
            self.all_time_audits = [
                ta for ta in self.all_time_audits if ta["deleted"] is None
            ]
            self.all_events = [e for e in self.all_events if e["deleted"] is None]
            self.all_timespans = [
                ts for ts in self.all_timespans if ts["deleted"] is None
            ]
            self.all_logs = [log for log in self.all_logs if log["deleted"] is None]
            self.all_notes = [
                note for note in self.all_notes if note["deleted"] is None
            ]
            self.all_entries = [e for e in self.all_entries if e["deleted"] is None]

        # Build lookup dictionaries for efficient access
        self._build_lookups()

    def _build_lookups(self) -> None:
        """Build lookup dictionaries for efficient entity access."""
        self.tasks_by_id = {t["id"]: t for t in self.all_tasks if t["id"] is not None}
        self.time_audits_by_id = {
            ta["id"]: ta for ta in self.all_time_audits if ta["id"] is not None
        }
        self.events_by_id = {e["id"]: e for e in self.all_events if e["id"] is not None}
        self.timespans_by_id = {
            ts["id"]: ts for ts in self.all_timespans if ts["id"] is not None
        }
        self.trackers_by_id = {
            t["id"]: t for t in self.all_trackers if t["id"] is not None
        }

    def collect_for_tasks(self, task_ids: list[EntityId]) -> dict:
        """
        Collect all entities related to the specified tasks.

        Collects:
        - The tasks themselves
        - Time audits where task_id = task.id
        - Logs/Notes where reference_type = "task" AND reference_id = task.id
        - Logs/Notes where reference_type = "time_audit" AND reference_id is a time audit of this task
        """
        result_tasks: set[EntityId] = set()
        result_time_audits: set[EntityId] = set()
        result_logs: set[EntityId] = set()
        result_notes: set[EntityId] = set()

        for task_id in task_ids:
            if task_id not in self.tasks_by_id:
                continue

            result_tasks.add(task_id)

            # Get time audits for this task
            task_time_audits = [
                ta for ta in self.all_time_audits if ta["task_id"] == task_id
            ]
            for ta in task_time_audits:
                if ta["id"] is not None:
                    result_time_audits.add(ta["id"])

            # Get logs for task
            for log in self.all_logs:
                if (
                    log["reference_type"] == "task"
                    and log["reference_id"] == task_id
                    and log["id"] is not None
                ):
                    result_logs.add(log["id"])

            # Get notes for task
            for note in self.all_notes:
                if (
                    note["reference_type"] == "task"
                    and note["reference_id"] == task_id
                    and note["id"] is not None
                ):
                    result_notes.add(note["id"])

            # Get logs/notes for task's time audits
            for ta in task_time_audits:
                if ta["id"] is None:
                    continue
                for log in self.all_logs:
                    if (
                        log["reference_type"] == "time_audit"
                        and log["reference_id"] == ta["id"]
                        and log["id"] is not None
                    ):
                        result_logs.add(log["id"])
                for note in self.all_notes:
                    if (
                        note["reference_type"] == "time_audit"
                        and note["reference_id"] == ta["id"]
                        and note["id"] is not None
                    ):
                        result_notes.add(note["id"])

        return {
            "tasks": [self.tasks_by_id[tid] for tid in result_tasks],
            "time_audits": [
                self.time_audits_by_id[taid]
                for taid in result_time_audits
                if taid in self.time_audits_by_id
            ],
            "events": [],
            "timespans": [],
            "logs": [log for log in self.all_logs if log["id"] in result_logs],
            "notes": [note for note in self.all_notes if note["id"] in result_notes],
            "entries": [],
        }

    def collect_for_time_audits(self, time_audit_ids: list[EntityId]) -> dict:
        """
        Collect all entities related to the specified time audits.

        Collects:
        - The time audits themselves
        - Logs/Notes where reference_type = "time_audit" AND reference_id = time_audit.id
        """
        result_time_audits: set[EntityId] = set()
        result_logs: set[EntityId] = set()
        result_notes: set[EntityId] = set()

        for ta_id in time_audit_ids:
            if ta_id not in self.time_audits_by_id:
                continue

            result_time_audits.add(ta_id)

            # Get logs for time audit
            for log in self.all_logs:
                if (
                    log["reference_type"] == "time_audit"
                    and log["reference_id"] == ta_id
                    and log["id"] is not None
                ):
                    result_logs.add(log["id"])

            # Get notes for time audit
            for note in self.all_notes:
                if (
                    note["reference_type"] == "time_audit"
                    and note["reference_id"] == ta_id
                    and note["id"] is not None
                ):
                    result_notes.add(note["id"])

        return {
            "tasks": [],
            "time_audits": [
                self.time_audits_by_id[taid]
                for taid in result_time_audits
                if taid in self.time_audits_by_id
            ],
            "events": [],
            "timespans": [],
            "logs": [log for log in self.all_logs if log["id"] in result_logs],
            "notes": [note for note in self.all_notes if note["id"] in result_notes],
            "entries": [],
        }

    def collect_for_events(self, event_ids: list[EntityId]) -> dict:
        """
        Collect all entities related to the specified events.

        Collects:
        - The events themselves
        - Logs/Notes where reference_type = "event" AND reference_id = event.id
        """
        result_events: set[EntityId] = set()
        result_logs: set[EntityId] = set()
        result_notes: set[EntityId] = set()

        for event_id in event_ids:
            if event_id not in self.events_by_id:
                continue

            result_events.add(event_id)

            # Get logs for event
            for log in self.all_logs:
                if (
                    log["reference_type"] == "event"
                    and log["reference_id"] == event_id
                    and log["id"] is not None
                ):
                    result_logs.add(log["id"])

            # Get notes for event
            for note in self.all_notes:
                if (
                    note["reference_type"] == "event"
                    and note["reference_id"] == event_id
                    and note["id"] is not None
                ):
                    result_notes.add(note["id"])

        return {
            "tasks": [],
            "time_audits": [],
            "events": [
                self.events_by_id[eid]
                for eid in result_events
                if eid in self.events_by_id
            ],
            "timespans": [],
            "logs": [log for log in self.all_logs if log["id"] in result_logs],
            "notes": [note for note in self.all_notes if note["id"] in result_notes],
            "entries": [],
        }

    def collect_for_projects(self, projects: list[str]) -> dict:
        """
        Collect all entities that belong to the specified projects.

        Collects all entities where any of the entity's projects match:
        - Tasks
        - Time audits (directly tagged OR via task relationship)
        - Events
        - Timespans
        - Logs (directly tagged OR via reference to project entities)
        - Notes (directly tagged OR via reference to project entities)
        - Tracker entries (where entry OR tracker has matching project)
        """
        result_tasks: list[Task] = []
        result_time_audits: list[TimeAudit] = []
        result_events: list[Event] = []
        result_timespans: list[Timespan] = []
        result_logs: list[Log] = []
        result_notes: list[Note] = []
        result_entries: list[Entry] = []

        # Collect task IDs for nested log/note lookup
        project_task_ids: set[EntityId] = set()
        project_time_audit_ids: set[EntityId] = set()
        project_event_ids: set[EntityId] = set()

        for project in projects:
            # Tasks with this project
            for task in self.all_tasks:
                if task["projects"] is not None and project in task["projects"]:
                    result_tasks.append(task)
                    if task["id"] is not None:
                        project_task_ids.add(task["id"])

            # Time audits with this project (direct or via task)
            for ta in self.all_time_audits:
                if ta["projects"] is not None and project in ta["projects"]:
                    result_time_audits.append(ta)
                    if ta["id"] is not None:
                        project_time_audit_ids.add(ta["id"])
                elif ta["task_id"] in project_task_ids:
                    result_time_audits.append(ta)
                    if ta["id"] is not None:
                        project_time_audit_ids.add(ta["id"])

            # Events with this project
            for event in self.all_events:
                if event["projects"] is not None and project in event["projects"]:
                    result_events.append(event)
                    if event["id"] is not None:
                        project_event_ids.add(event["id"])

            # Timespans with this project
            for timespan in self.all_timespans:
                if timespan["projects"] is not None and project in timespan["projects"]:
                    result_timespans.append(timespan)

            # Logs with this project or referencing project entities
            for log in self.all_logs:
                if log["projects"] is not None and project in log["projects"]:
                    result_logs.append(log)
                elif (
                    log["reference_type"] == "task"
                    and log["reference_id"] in project_task_ids
                ):
                    result_logs.append(log)
                elif (
                    log["reference_type"] == "time_audit"
                    and log["reference_id"] in project_time_audit_ids
                ):
                    result_logs.append(log)
                elif (
                    log["reference_type"] == "event"
                    and log["reference_id"] in project_event_ids
                ):
                    result_logs.append(log)

            # Notes with this project or referencing project entities
            for note in self.all_notes:
                if note["projects"] is not None and project in note["projects"]:
                    result_notes.append(note)
                elif (
                    note["reference_type"] == "task"
                    and note["reference_id"] in project_task_ids
                ):
                    result_notes.append(note)
                elif (
                    note["reference_type"] == "time_audit"
                    and note["reference_id"] in project_time_audit_ids
                ):
                    result_notes.append(note)
                elif (
                    note["reference_type"] == "event"
                    and note["reference_id"] in project_event_ids
                ):
                    result_notes.append(note)

            # Tracker entries where entry or tracker has matching project
            project_tracker_ids = {
                t["id"]
                for t in self.all_trackers
                if t["projects"] is not None
                and project in t["projects"]
                and t["id"] is not None
            }
            for entry in self.all_entries:
                if entry["projects"] is not None and project in entry["projects"]:
                    result_entries.append(entry)
                elif entry["tracker_id"] in project_tracker_ids:
                    result_entries.append(entry)

        # Deduplicate results
        return {
            "tasks": _dedupe_by_id(result_tasks),
            "time_audits": _dedupe_by_id(result_time_audits),
            "events": _dedupe_by_id(result_events),
            "timespans": _dedupe_by_id(result_timespans),
            "logs": _dedupe_by_id(result_logs),
            "notes": _dedupe_by_id(result_notes),
            "entries": _dedupe_by_id(result_entries),
        }

    def collect_for_tags(
        self, tags: list[str], tag_regex: Optional[list[str]] = None
    ) -> dict:
        """
        Collect all entities that have all the specified tags (AND logic).

        Same as project story, but filtering by tag membership.
        Args:
            tags: List of exact tag strings to match (must have ALL)
            tag_regex: List of regex patterns to match (must have ALL)
        """
        result_tasks: list[Task] = []
        result_time_audits: list[TimeAudit] = []
        result_events: list[Event] = []
        result_timespans: list[Timespan] = []
        result_logs: list[Log] = []
        result_notes: list[Note] = []
        result_entries: list[Entry] = []

        def has_all_tags(entity_tags: Optional[list[str]]) -> bool:
            """Check if entity has all required tags (exact match and regex)."""
            if entity_tags is None:
                return False
            # Check exact tag matches
            if not all(tag in entity_tags for tag in tags):
                return False
            # Check regex patterns if provided
            if tag_regex:
                if not all(
                    tag_matches_regex(pattern, entity_tags) for pattern in tag_regex
                ):
                    return False
            return True

        # Collect entity IDs for nested log/note lookup
        tag_task_ids: set[EntityId] = set()
        tag_time_audit_ids: set[EntityId] = set()
        tag_event_ids: set[EntityId] = set()

        # Tasks with all tags
        for task in self.all_tasks:
            if has_all_tags(task["tags"]):
                result_tasks.append(task)
                if task["id"] is not None:
                    tag_task_ids.add(task["id"])

        # Time audits with all tags (direct or via task)
        for ta in self.all_time_audits:
            if has_all_tags(ta["tags"]):
                result_time_audits.append(ta)
                if ta["id"] is not None:
                    tag_time_audit_ids.add(ta["id"])
            elif ta["task_id"] in tag_task_ids:
                result_time_audits.append(ta)
                if ta["id"] is not None:
                    tag_time_audit_ids.add(ta["id"])

        # Events with all tags
        for event in self.all_events:
            if has_all_tags(event["tags"]):
                result_events.append(event)
                if event["id"] is not None:
                    tag_event_ids.add(event["id"])

        # Timespans with all tags
        for timespan in self.all_timespans:
            if has_all_tags(timespan["tags"]):
                result_timespans.append(timespan)

        # Logs with all tags or referencing tag entities
        for log in self.all_logs:
            if has_all_tags(log["tags"]):
                result_logs.append(log)
            elif (
                log["reference_type"] == "task" and log["reference_id"] in tag_task_ids
            ):
                result_logs.append(log)
            elif (
                log["reference_type"] == "time_audit"
                and log["reference_id"] in tag_time_audit_ids
            ):
                result_logs.append(log)
            elif (
                log["reference_type"] == "event"
                and log["reference_id"] in tag_event_ids
            ):
                result_logs.append(log)

        # Notes with all tags or referencing tag entities
        for note in self.all_notes:
            if has_all_tags(note["tags"]):
                result_notes.append(note)
            elif (
                note["reference_type"] == "task"
                and note["reference_id"] in tag_task_ids
            ):
                result_notes.append(note)
            elif (
                note["reference_type"] == "time_audit"
                and note["reference_id"] in tag_time_audit_ids
            ):
                result_notes.append(note)
            elif (
                note["reference_type"] == "event"
                and note["reference_id"] in tag_event_ids
            ):
                result_notes.append(note)

        # Tracker entries where tracker has all tags
        tag_tracker_ids = {
            t["id"]
            for t in self.all_trackers
            if has_all_tags(t["tags"]) and t["id"] is not None
        }
        for entry in self.all_entries:
            if entry["tracker_id"] in tag_tracker_ids:
                result_entries.append(entry)

        # Deduplicate results
        return {
            "tasks": _dedupe_by_id(result_tasks),
            "time_audits": _dedupe_by_id(result_time_audits),
            "events": _dedupe_by_id(result_events),
            "timespans": _dedupe_by_id(result_timespans),
            "logs": _dedupe_by_id(result_logs),
            "notes": _dedupe_by_id(result_notes),
            "entries": _dedupe_by_id(result_entries),
        }

    def collect(
        self,
        task_ids: Optional[list[EntityId]] = None,
        time_audit_ids: Optional[list[EntityId]] = None,
        event_ids: Optional[list[EntityId]] = None,
        projects: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        tag_regex: Optional[list[str]] = None,
    ) -> dict:
        """
        Collect entities based on multiple anchor types.

        When multiple anchors are specified, this performs AND logic -
        collecting entities that match ALL criteria (intersection).
        """
        results: list[dict] = []

        if task_ids:
            results.append(self.collect_for_tasks(task_ids))

        if time_audit_ids:
            results.append(self.collect_for_time_audits(time_audit_ids))

        if event_ids:
            results.append(self.collect_for_events(event_ids))

        if projects:
            results.append(self.collect_for_projects(projects))

        if tags or tag_regex:
            results.append(self.collect_for_tags(tags or [], tag_regex))

        if not results:
            return {
                "tasks": [],
                "time_audits": [],
                "events": [],
                "timespans": [],
                "logs": [],
                "notes": [],
                "entries": [],
            }

        if len(results) == 1:
            return results[0]

        # Intersect results (AND logic)
        return _intersect_results(results)


def _dedupe_by_id(items: list) -> list:
    """Remove duplicates from a list of entities by their id field."""
    seen: set[int] = set()
    result = []
    for item in items:
        item_id = item.get("id")
        if item_id is not None and item_id not in seen:
            seen.add(item_id)
            result.append(item)
    return result


def _intersect_results(results: list[dict]) -> dict:
    """
    Intersect multiple result sets (AND logic).

    Returns only entities that appear in ALL result sets.
    """
    if not results:
        return {
            "tasks": [],
            "time_audits": [],
            "events": [],
            "timespans": [],
            "logs": [],
            "notes": [],
            "entries": [],
        }

    entity_types = [
        "tasks",
        "time_audits",
        "events",
        "timespans",
        "logs",
        "notes",
        "entries",
    ]
    intersected: dict = {}

    for entity_type in entity_types:
        # Get IDs from each result set
        id_sets = []
        for result in results:
            ids = {
                item.get("id")
                for item in result[entity_type]
                if item.get("id") is not None
            }
            id_sets.append(ids)

        if not id_sets:
            intersected[entity_type] = []
            continue

        # Find intersection of all ID sets
        common_ids = id_sets[0]
        for id_set in id_sets[1:]:
            common_ids = common_ids & id_set

        # Filter to only items with common IDs
        intersected[entity_type] = [
            item for item in results[0][entity_type] if item.get("id") in common_ids
        ]

    return intersected


def calculate_date_range(
    tasks: list[Task],
    time_audits: list[TimeAudit],
    events: list[Event],
    timespans: list[Timespan],
    logs: list[Log],
    notes: list[Note],
    entries: list[Entry],
) -> tuple[Optional[pendulum.DateTime], Optional[pendulum.DateTime]]:
    """
    Calculate the date range from all related entities.

    Date sources per entity type:
    - Task: scheduled, due, created
    - Time Audit: start, end
    - Event: start, end
    - Timespan: start, end
    - Log: timestamp
    - Note: timestamp
    - Entry: timestamp
    """
    all_dates: list[pendulum.DateTime] = []

    for task in tasks:
        if task["scheduled"] is not None:
            all_dates.append(task["scheduled"])
        if task["due"] is not None:
            all_dates.append(task["due"])
        if task["created"] is not None:
            all_dates.append(task["created"])

    for ta in time_audits:
        if ta["start"] is not None:
            all_dates.append(ta["start"])
        if ta["end"] is not None:
            all_dates.append(ta["end"])

    for event in events:
        if event["start"] is not None:
            all_dates.append(event["start"])
        if event["end"] is not None:
            all_dates.append(event["end"])

    for timespan in timespans:
        if timespan["start"] is not None:
            all_dates.append(timespan["start"])
        if timespan["end"] is not None:
            all_dates.append(timespan["end"])

    for log in logs:
        if log["timestamp"] is not None:
            all_dates.append(log["timestamp"])

    for note in notes:
        if note["timestamp"] is not None:
            all_dates.append(note["timestamp"])

    for entry in entries:
        if entry["timestamp"] is not None:
            all_dates.append(entry["timestamp"])

    if not all_dates:
        return None, None

    min_date = min(all_dates)
    max_date = max(all_dates)

    return min_date, max_date


def generate_story_header(
    task_ids: Optional[list[EntityId]] = None,
    time_audit_ids: Optional[list[EntityId]] = None,
    event_ids: Optional[list[EntityId]] = None,
    projects: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    tasks: Optional[list[Task]] = None,
    time_audits: Optional[list[TimeAudit]] = None,
    events: Optional[list[Event]] = None,
    num_tasks: int = 0,
    num_time_audits: int = 0,
    num_logs: int = 0,
) -> str:
    """
    Generate a header string describing the story.

    Examples:
    - Story: Task #5 - Fix the login bug
    - Story: Project work.api (15 tasks, 42 time audits, 23 logs)
    - Story: Tag #urgent (8 tasks, 12 time audits)
    - Story: Task #5, Task #8 (combined)
    """
    parts = []

    if task_ids and tasks:
        for tid in task_ids:
            for task in tasks:
                if task["id"] == tid:
                    mapped_id = ID_MAP_REPO.associate_id("tasks", tid)
                    desc = (
                        task.get("description", "[no description]")
                        or "[no description]"
                    )
                    parts.append(f"Task #{mapped_id} - {desc[:40]}")
                    break

    if time_audit_ids and time_audits:
        for ta_id in time_audit_ids:
            for ta in time_audits:
                if ta["id"] == ta_id:
                    mapped_id = ID_MAP_REPO.associate_id("time_audits", ta_id)
                    desc = (
                        ta.get("description", "[no description]") or "[no description]"
                    )
                    parts.append(f"Time Audit #{mapped_id} - {desc[:30]}")
                    break

    if event_ids and events:
        for eid in event_ids:
            for event in events:
                if event["id"] == eid:
                    mapped_id = ID_MAP_REPO.associate_id("events", eid)
                    title = event.get("title", "[no title]") or "[no title]"
                    parts.append(f"Event #{mapped_id} - {title[:30]}")
                    break

    if projects:
        for project in projects:
            stats = (
                f"({num_tasks} tasks, {num_time_audits} time audits, {num_logs} logs)"
            )
            parts.append(f"Project {project} {stats}")

    if tags:
        tag_str = ", ".join(f"#{tag}" for tag in tags)
        stats = f"({num_tasks} tasks, {num_time_audits} time audits)"
        parts.append(f"Tag {tag_str} {stats}")

    if len(parts) > 1:
        return "Story: " + ", ".join(parts[:2]) + " (combined)"
    elif parts:
        return "Story: " + parts[0]
    else:
        return "Story"
