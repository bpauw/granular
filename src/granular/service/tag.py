# SPDX-License-Identifier: MIT

from granular.repository.entry import ENTRY_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.tag import TAG_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.repository.tracker import TRACKER_REPO


def sync_tags() -> None:
    """
    Synchronize the tags.yaml file with all tags found in all tagged entities.

    This function:
    1. Loads all tagged entities from their repositories
    2. Extracts all unique tags from these entities
    3. Rewrites the tags.yaml file to reflect only the tags currently in use
    """
    # Collect all tags from all entities
    all_tags: set[str] = set()

    # Extract tags from tasks
    for task in TASK_REPO.get_all_tasks():
        if task["tags"] is not None:
            all_tags.update(task["tags"])

    # Extract tags from events
    for event in EVENT_REPO.get_all_events():
        if event["tags"] is not None:
            all_tags.update(event["tags"])

    # Extract tags from time audits
    for time_audit in TIME_AUDIT_REPO.get_all_time_audits():
        if time_audit["tags"] is not None:
            all_tags.update(time_audit["tags"])

    # Extract tags from notes
    for note in NOTE_REPO.get_all_notes():
        if note["tags"] is not None:
            all_tags.update(note["tags"])

    # Extract tags from logs
    for log in LOG_REPO.get_all_logs():
        if log["tags"] is not None:
            all_tags.update(log["tags"])

    # Extract tags from timespans
    for timespan in TIMESPAN_REPO.get_all_timespans():
        if timespan["tags"] is not None:
            all_tags.update(timespan["tags"])

    # Extract tags from trackers
    for tracker in TRACKER_REPO.get_all_trackers():
        if tracker["tags"] is not None:
            all_tags.update(tracker["tags"])

    # Extract tags from entries
    for entry in ENTRY_REPO.get_all_entries():
        if entry["tags"] is not None:
            all_tags.update(entry["tags"])

    # Sort tags alphabetically for consistent output
    sorted_tags = sorted(all_tags)

    # Replace the entire tag list in the repository
    TAG_REPO.set_all_tags(sorted_tags)
