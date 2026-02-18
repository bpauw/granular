# SPDX-License-Identifier: MIT

from granular.repository.entry import ENTRY_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.project import PROJECT_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.repository.tracker import TRACKER_REPO


def sync_projects() -> None:
    """
    Synchronize the projects.yaml file with all projects found across all entity types.

    This function:
    1. Loads all entities from their repositories
    2. Extracts all unique projects from these entities
    3. Rewrites the projects.yaml file to reflect only the projects currently in use
    """
    # Collect all projects from all entities
    all_projects: set[str] = set()

    # Extract projects from tasks
    for task in TASK_REPO.get_all_tasks():
        if task["projects"] is not None:
            all_projects.update(task["projects"])

    # Extract projects from events
    for event in EVENT_REPO.get_all_events():
        if event["projects"] is not None:
            all_projects.update(event["projects"])

    # Extract projects from time audits
    for time_audit in TIME_AUDIT_REPO.get_all_time_audits():
        if time_audit["projects"] is not None:
            all_projects.update(time_audit["projects"])

    # Extract projects from notes
    for note in NOTE_REPO.get_all_notes():
        if note["projects"] is not None:
            all_projects.update(note["projects"])

    # Extract projects from logs
    for log in LOG_REPO.get_all_logs():
        if log["projects"] is not None:
            all_projects.update(log["projects"])

    # Extract projects from timespans
    for timespan in TIMESPAN_REPO.get_all_timespans():
        if timespan["projects"] is not None:
            all_projects.update(timespan["projects"])

    # Extract projects from trackers
    for tracker in TRACKER_REPO.get_all_trackers():
        if tracker["projects"] is not None:
            all_projects.update(tracker["projects"])

    # Extract projects from entries
    for entry in ENTRY_REPO.get_all_entries():
        if entry["projects"] is not None:
            all_projects.update(entry["projects"])

    # Sort projects alphabetically for consistent output
    sorted_projects = sorted(all_projects)

    # Replace the entire project list in the repository
    PROJECT_REPO.set_all_projects(sorted_projects)
