# SPDX-License-Identifier: MIT

from granular.repository.event import EVENT_REPO
from granular.repository.project import PROJECT_REPO
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO


def sync_projects() -> None:
    """
    Synchronize the projects.yaml file with all projects found in events, tasks, and time-audits.

    This function:
    1. Loads all events, tasks, and time-audits from their repositories
    2. Extracts all unique projects from these entities
    3. Rewrites the projects.yaml file to reflect only the projects currently in use
    """
    # Collect all projects from all entities
    all_projects: set[str] = set()

    # Extract projects from tasks
    for task in TASK_REPO.get_all_tasks():
        if task["project"] is not None:
            all_projects.add(task["project"])

    # Extract projects from events
    for event in EVENT_REPO.get_all_events():
        if event["project"] is not None:
            all_projects.add(event["project"])

    # Extract projects from time audits
    for time_audit in TIME_AUDIT_REPO.get_all_time_audits():
        if time_audit["project"] is not None:
            all_projects.add(time_audit["project"])

    # Sort projects alphabetically for consistent output
    sorted_projects = sorted(all_projects)

    # Replace the entire project list in the repository
    PROJECT_REPO.set_all_projects(sorted_projects)
