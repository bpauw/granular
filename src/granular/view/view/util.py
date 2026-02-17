# SPDX-License-Identifier: MIT

from typing import Optional

import pendulum

from granular.model.entity_id import EntityId
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit

# def task_state(task: Task) -> str:
#     if task["completed"] is not None:
#         return "✅"
#     elif task["cancelled"] is not None:
#         return "❌"
#     elif task["not_completed"] is not None:
#         return "⭕"
#     return "◻️"


def task_state(task: Task, all_tasks: Optional[list[Task]] = None) -> str:
    """
    Get the state symbol for a task.

    Args:
        task: The task to get the state for
        all_tasks: Optional list of all tasks to check if this task has been cloned

    Returns:
        State symbol: ">" if cloned and closed, "X" if completed, "/" if cancelled,
        "~" if not completed, " " if open
    """
    # Check if task is closed (completed, not_completed, or cancelled)
    is_closed = (
        task["completed"] is not None
        or task["not_completed"] is not None
        or task["cancelled"] is not None
    )

    # If closed and we have all_tasks, check if this task was cloned
    if is_closed and all_tasks is not None:
        task_id = task["id"]
        # Check if any task has this task as its cloned_from_id
        for other_task in all_tasks:
            if other_task["cloned_from_id"] == task_id:
                return ">"

    # Normal state symbols
    if task["completed"] is not None:
        return "X"
    elif task["cancelled"] is not None:
        return "/"
    elif task["not_completed"] is not None:
        return "~"
    return " "


def is_task_completed(task: Task) -> bool:
    """Check if a task has been completed, cancelled, or marked as not_completed."""
    return (
        task["completed"] is not None
        or task["cancelled"] is not None
        or task["not_completed"] is not None
    )


def task_age(task: Task) -> str:
    now = pendulum.now()
    return now.diff_for_humans(task["created"], absolute=True)


def render_duration(duration: Optional[pendulum.Duration]) -> Optional[str]:
    if duration is None:
        return None
    return f"{duration.hours}:{duration.minutes:02d}"


def calculate_task_total_duration(
    task_id: Optional[EntityId], time_audits: list[TimeAudit]
) -> Optional[pendulum.Duration]:
    """Calculate the total duration of all time audits associated with a task."""
    if task_id is None:
        return None

    total_seconds: float = 0
    for time_audit in time_audits:
        # Only include time audits that are linked to this task and not deleted
        if time_audit["task_id"] == task_id and time_audit["deleted"] is None:
            if time_audit["start"] is not None and time_audit["end"] is not None:
                duration = time_audit["end"] - time_audit["start"]
                total_seconds += duration.total_seconds()

    if total_seconds == 0:
        return None

    return pendulum.duration(seconds=total_seconds)


def format_tags(tags: Optional[list[str]]) -> str:
    """Format a list of tags as a comma-separated string without brackets or quotes."""
    if tags is None or len(tags) == 0:
        return ""
    return ", ".join(tags)


def has_notes(
    entity_id: Optional[EntityId], entity_type: str, notes: list[Note]
) -> str:
    """Check if an entity has any notes and return a checkmark if so."""
    if entity_id is None:
        return ""
    for note in notes:
        if (
            note["reference_id"] == entity_id
            and note["reference_type"] == entity_type
            and note["deleted"] is None
        ):
            return "N"
    return ""


def has_logs(entity_id: Optional[EntityId], entity_type: str, logs: list[Log]) -> str:
    """Check if an entity has any logs and return a checkmark if so."""
    if entity_id is None:
        return ""
    for log in logs:
        if (
            log["reference_id"] == entity_id
            and log["reference_type"] == entity_type
            and log["deleted"] is None
        ):
            return "L"
    return ""
